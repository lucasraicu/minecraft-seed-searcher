"""Isolated real-BDS spawn observer; never modifies existing worlds or containers."""
import argparse
import hashlib
import json
import os
import queue
import shutil
import subprocess
import threading
import time
import uuid
from pathlib import Path

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
DOCKER = shutil.which('docker')
IMAGE = 'bedrock-verification-poc:1.26.52.3'
HEADER_UUID = '0d7797c3-65e9-4710-ac5e-e966fa32685e'


def docker(*args, timeout=20):
    return subprocess.run([DOCKER,*args],capture_output=True,text=True,check=True,timeout=timeout)


def prepare(seed, label):
    work = BASE / 'worlds' / label
    work.mkdir(parents=True,exist_ok=False)
    pack = work / 'behavior_packs/spawn_observer/scripts'
    pack.mkdir(parents=True)
    (pack/'main.js').write_bytes((BASE/'observer.js').read_bytes())
    manifest = {
        'format_version':2,
        'header':{'name':'Read-only spawn audit','description':'Observe default spawn and unmodified player join location',
                  'uuid':HEADER_UUID,'version':[1,0,0],'min_engine_version':[1,26,50]},
        'modules':[{'type':'script','language':'javascript','uuid':'184c523a-c28c-41a6-8cc1-30e5880d504e','version':[1,0,0],'entry':'scripts/main.js'}],
        'dependencies':[{'module_name':'@minecraft/server','version':'2.10.0'}],
    }
    (pack.parent/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    world = work/'worlds/spawn_audit'
    world.mkdir(parents=True)
    (world/'world_behavior_packs.json').write_text(json.dumps([{'pack_id':HEADER_UUID,'version':[1,0,0]}])+'\n')
    (work/'server.properties').write_text('\n'.join([
        'server-name=Isolated spawn audit','gamemode=survival','difficulty=peaceful',
        'allow-cheats=true','max-players=4','online-mode=false','allow-list=false',
        'server-port=19132','server-portv6=19133','transport=raknet','enable-lan-visibility=false',
        'view-distance=5','tick-distance=4','max-threads=2','level-name=spawn_audit',
        'level-seed='+str(seed),'default-player-permission-level=member',
        'content-log-file-enabled=true','content-log-console-output-enabled=true',
        'content-log-level=info','client-side-chunk-generation-enabled=false',
        'server-authoritative-movement-strict=false','player-idle-timeout=0',
    ])+'\n')
    return work


class RunningWorld:
    def __init__(self,seed,label):
        self.seed = str(seed)
        self.label = label
        self.name = 'codex-spawn-audit-'+label
        self.work = prepare(seed,label)
        self.events = queue.Queue()
        self.rows = []
        self.lines = []
        self.started = time.monotonic()
        # Reuse immutable resources via symlinks; never copy or alter source worlds.
        setup = '''set -eu
for p in /opt/bds/*; do
  b=$(basename "$p")
  case "$b" in worlds|server.properties|behavior_packs|config) continue;; esac
  if [ ! -e "/audit/$b" ]; then ln -s "$p" "/audit/$b"; fi
done
for p in /opt/bds/behavior_packs/*; do
  [ -e "$p" ] || continue
  b=$(basename "$p")
  [ -e "/audit/behavior_packs/$b" ] || ln -s "$p" "/audit/behavior_packs/$b"
done
if [ -d /opt/bds/config ] && [ ! -e /audit/config ]; then cp -a /opt/bds/config /audit/config; fi
cd /audit
export LD_LIBRARY_PATH=/opt/bds
exec /opt/bds/bedrock_server'''
        self.log = (self.work/'console.log').open('w')
        cmd = [DOCKER,'run','--rm','-i','--name',self.name,'--cpus','2','--memory','4g',
               '-p','127.0.0.1::19132/udp','--mount',f'type=bind,src={self.work},dst=/audit',
               '--workdir','/audit','--entrypoint','/bin/sh',IMAGE,'-c',setup]
        self.process = subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1)
        self.thread = threading.Thread(target=self.read,daemon=True)
        self.thread.start()

    def read(self):
        for line in self.process.stdout:
            self.lines.append(line)
            self.log.write(line)
            self.log.flush()
            self.events.put(line)
            if 'SPAWN_AUDIT ' in line:
                try:
                    row = json.loads(line.split('SPAWN_AUDIT ',1)[1])
                    row['wallSinceStart'] = time.monotonic()-self.started
                    self.rows.append(row)
                except ValueError:
                    pass

    def wait(self,phase,timeout=65):
        deadline = time.monotonic()+timeout
        while time.monotonic() < deadline:
            for row in self.rows:
                if row['phase'] == phase:
                    assert row['seed'] == self.seed, (row['seed'],self.seed)
                    return row
            if self.process.poll() is not None:
                raise RuntimeError('BDS exited: '+''.join(self.lines[-18:]))
            try:
                self.events.get(timeout=min(0.5,max(0.01,deadline-time.monotonic())))
            except queue.Empty:
                pass
        raise TimeoutError('BDS '+phase+'; last logs: '+''.join(self.lines[-18:]))

    def port(self):
        return int(docker('port',self.name,'19132/udp').stdout.strip().rsplit(':',1)[1])

    def stop(self):
        clean = False
        try:
            if self.process.poll() is None:
                self.process.stdin.write('stop\n')
                self.process.stdin.flush()
                self.process.wait(timeout=25)
            clean = self.process.returncode == 0
        except (subprocess.TimeoutExpired,BrokenPipeError):
            try:
                docker('stop','-t','5',self.name,timeout=12)
            except Exception:
                pass
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
        finally:
            self.thread.join(timeout=3)
            self.log.close()
        return clean


def run_headless(seed,label=None):
    label = label or uuid.uuid4().hex[:12]
    world = RunningWorld(seed,label)
    result = {'seed':str(seed),'label':label,'kind':'headless_world_spawn_only','rows':[]}
    try:
        world.wait('world_tick40')
        result['rows'] = world.rows.copy()
        result['elapsed_to_observation'] = time.monotonic()-world.started
        result['status'] = 'observed'
    except Exception as error:
        result['status'] = 'failed'
        result['error'] = str(error)
    finally:
        result['clean_shutdown'] = world.stop()
        result['elapsed_total'] = time.monotonic()-world.started
        result['console_sha256'] = hashlib.sha256((world.work/'console.log').read_bytes()).hexdigest()
        (world.work/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('seed',type=int)
    parser.add_argument('--label')
    args=parser.parse_args()
    print(json.dumps(run_headless(args.seed,args.label),indent=2))
