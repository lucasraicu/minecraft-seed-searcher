#!/usr/bin/env python3
"""Run one explicitly bounded local catalog validation command; no HTTP exposure."""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from seed_search.catalog.ingestion import atomic_json,tree_bytes,verify_no_symlinks
from seed_search.realm.runner import process_tree_resources


def run(root,command,*,seconds=900,max_bytes=2<<30):
    if type(seconds) is not int or not 1<=seconds<=1800:raise ValueError('Wall allowance must be1..1800 seconds')
    if type(max_bytes) is not int or not 1<=max_bytes<=2<<30:raise ValueError('Output allowance must be<=2GiB')
    root=verify_no_symlinks(root);root.mkdir(parents=True,exist_ok=False)
    atomic_json(root/'job.json',dict(command=command,reserved_seconds=seconds,status='reserved'))
    before=time.monotonic();process=None;peak=0;reason=None;size=0
    read_fd,write_fd=os.pipe()
    try:
        with (root/'command.log').open('wb') as log:
            process=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'_child',str(seconds),str(read_fd),json.dumps(command)],
                stdout=log,stderr=log,pass_fds=(read_fd,),start_new_session=True,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(ROOT/'src')))
            os.close(read_fd);read_fd=None
            atomic_json(root/'job.json',dict(command=command,pid=process.pid,pgid=process.pid,reserved_seconds=seconds,status='active'))
            os.write(write_fd,b'G');os.close(write_fd);write_fd=None
            while process.poll() is None:
                elapsed=time.monotonic()-before
                if elapsed>=seconds:reason='wall_cap'
                sample=process_tree_resources(os.getpid())
                if not sample['available']:reason='aggregate_monitor_unavailable'
                peak=max(peak,sample.get('rss_bytes',0))
                if peak>4<<30:reason='aggregate_rss_cap'
                size=tree_bytes(root)
                if size>max_bytes:reason='output_cap'
                if reason:break
                time.sleep(.25)
    finally:
        for fd in (read_fd,write_fd):
            if fd is not None:os.close(fd)
        if process is not None and process.poll() is None:
            try:os.killpg(process.pid,signal.SIGTERM)
            except ProcessLookupError:pass
            try:process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                try:os.killpg(process.pid,signal.SIGKILL)
                except ProcessLookupError:pass
                process.wait(timeout=5)
        atomic_json(root/'job-result.json',dict(exit_status=process.returncode if process else None,stop_reason=reason,
            wall_seconds=time.monotonic()-before,polled_peak_rss_bytes=peak,output_bytes=tree_bytes(root),
            parent_crash_policy='Full reservation remains charged; child has inherited wall alarm. No automatic job retry.'))
    return process.returncode if reason is None else 2


def main():
    if len(sys.argv)>1 and sys.argv[1]=='_child':
        seconds=int(sys.argv[2]);fd=int(sys.argv[3]);command=json.loads(sys.argv[4])
        if os.read(fd,1)!=b'G':return 3
        os.close(fd);signal.alarm(seconds);os.execvpe(command[0],command,os.environ)
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--seconds',type=int,default=900);parser.add_argument('command',nargs=argparse.REMAINDER)
    args=parser.parse_args();command=args.command[1:] if args.command[:1]==['--'] else args.command
    if not command:parser.error('Expected an explicit local command after --')
    return run(args.output,command,seconds=args.seconds)


if __name__=='__main__':raise SystemExit(main())
