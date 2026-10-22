# Frozen counterexample membership followup — review before execution
Use High reasoning, only this context, no commands/readers/edit/network/agents. <=650words final start MEMBERSHIP_REVIEW. User-approved PLAN permits bounded named point-membership followup within7200totalBDSseconds,600perseed,8GiB,8192pointmembers,24576biomes,196608blocks; oneBDSmax, noinitialpilotvolumes (pilotdone). This addendum uses ZEROvolumes/locates; only137biome/block/membershippoints acrossfivealready-stoppedworldcopies, targets3village,2bastion,1ancientcity positiveBDSexactover-rejection/omission refs. Allpointselection is post-discovery/biased, notblindtest. Original24worldcohort mustfinishbeforelaunch andsame campaign.lock. Original default-settings sources read-only, experiments gametest flag ONLY onownedcopies toenable2.11-beta. Prior samepinned BDSimage membership API worked; exactsameAPI/shapes. This proves only copied-world point membership ifpositive, never default-vs-Beta generation equivalence, all-worldabsence or instancecount. Nativefixapprovalpending; read-onlyfollowupindependent.

Frozen addendum SHA5dcce3c4433726ec00b761999bb8f8d0ad4a83f895a1cb9efff6f9f450122eff; indices2,16,3,4,17; points30,60,35,6,6. Sourceworldsizes590067..1223511bytes,4..5files, treehashesfrozen. Worlds2/3/4/17 priorBDS~175..244s;world16cum438.075s. Dynamicremaininggate reserves120s forpreparation/cleanup, thenbodywallmin180s,skipif<30. World16remaining161.9=>body41s; timedoutcase staysfailedimmutable, noautoretryornewdispatch. Allmeasuredprep/body/cleanupchargedincludingcopies; limitsnotincreased.

Existing scripts/predictor_targeted_bds.py::run_world contract: accepts casepoints≤64/columns=[]/structures=[],observer_path,copied_world,script_api2.11-beta,prepare_copy. Prepares defaultserverproperties/pack, copies sourceleveldb only intoownednewworld; checksfrozenbefore/aftercopy treehashes; prepare_copy modifiesONLYcopylevel.dat. DockerBDS2CPU2GiB,pidlimit256,read-onlyroot,tmpfs128MiB,nopublishedports,--rm,pinnedsha. Identitymustseed/API/players0. Sendsonefrozencoordinatepayload(max2000bytes); bindsreturnedrowXYZexactly; rejectsanyrowerror orreads>128biome/>8192blocks. Savehold/query ready/resume; cleanstop/ownedcleanup below. Scopevalidationinthisnewdriver replacesoldCLI'stwo-specificseedvalidator, notcallingthatCLI. Sourcefunctions unchanged. Drivervalidatesobserver/worldsource hashes beforecall; copied-world proof is scoped, noapprovalbypass.

## Proposed actual driver
```python
"""Small frozen copied-world followup; default dry-run, never a seed search."""
import argparse
import fcntl
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time
import uuid

ROOT = Path('/Users/lucasraicu/Downloads/minecraft-seed-searcher')
BASE = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT / 'scripts')]
from predictor_targeted_bds import run_world, IMAGE
from predictor_storage_probe import tree_hashes


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def atomic(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(path)


def execute(*, enabled=False):
    raw = (BASE / 'membership-addendum.json').read_bytes()
    if digest(raw) != (BASE / 'membership-addendum.sha256').read_text().strip():
        raise ValueError('Addendum changed')
    addendum = json.loads(raw)
    original_raw = (BASE / 'manifest.json').read_bytes()
    original = json.loads(original_raw)
    if digest(original_raw) != addendum['parent_manifest_sha256']:
        raise ValueError('Parent manifest changed')
    cases = addendum['cases']
    if [c['index'] for c in cases] != [2, 16, 3, 4, 17] or len(cases) != 5:
        raise ValueError('Followup scope changed')
    for case in cases:
        if original['worlds'][case['index']]['seed'] != case['seed']:
            raise ValueError('Seed differs from approved cohort')
        if case['dimension'] not in ('overworld', 'nether') or case['structures'] or case['columns']:
            raise ValueError('Unexpected method or dimension')
        if not 1 <= len(case['points']) <= 64 or len(case['points']) != len({tuple(p) for p in case['points']}):
            raise ValueError('Point inventory differs')
        for p in case['points']:
            if (len(p) != 3 or any(type(v) is not int for v in p) or
                max(abs(p[0]), abs(p[2])) > 5120 or
                not (0 if case['dimension'] == 'nether' else -64) <= p[1] <= (127 if case['dimension'] == 'nether' else 319)):
                raise ValueError('Invalid XYZ')
        observer = Path(case['observer'])
        if observer.parent != BASE or digest(observer.read_bytes()) != case['observer_sha256']:
            raise ValueError('Observer changed')
        source = Path(case['source_world'])
        if not source.is_relative_to(BASE / 'game') or source.is_symlink() or source.resolve() != source:
            raise ValueError('Source outside owned campaign')
        if tree_hashes(source) != case['source_world_hashes']:
            raise ValueError('Stopped source world changed')
    if sum(len(c['points']) for c in cases) != 137:
        raise ValueError('Read cap changed')
    if not enabled:
        return dict(dry_run=True, copies=5, biome_reads=137, membership_reads=137,
                    locates=0, volume_reads=0, addendum_sha256=digest(raw))

    out = BASE / 'membership-followup'
    with (BASE / 'game/campaign.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        cohort = json.loads((BASE / 'game/ledger.json').read_bytes())
        if len(cohort) != 24 or {r['index'] for r in cohort} != set(range(24)) or any(r['state'] != 'complete' for r in cohort):
            raise ValueError('Original cohort must be terminal and complete first')
        by_index = {r['index']: r for r in cohort}
        for case in cases:
            if by_index[case['index']]['report_sha256'] != case['original_report_sha256']:
                raise ValueError('Source observation changed')
        if out.exists():
            raise ValueError('Followup already attempted; no automatic retries')
        out.mkdir()
        (out / 'frozen.json').write_bytes(raw)
        ledger = []
        atomic(out / 'ledger.json', ledger)
        for case in cases:
            previous = by_index[case['index']]['wall_seconds']
            total = sum(r['wall_seconds'] for r in cohort) + sum(r['wall_seconds'] for r in ledger)
            remaining = min(600 - previous, 7200 - total)
            # Allow preparation and bounded stop/owned-cleanup overhead, charged below.
            wall = min(180, int(remaining) - 120)
            if wall < 30:
                ledger.append(dict(index=case['index'], state='unattempted_budget', wall_seconds=0.))
                atomic(out / 'ledger.json', ledger)
                continue
            if sum(p.stat().st_size for p in BASE.rglob('*') if p.is_file() and not p.is_symlink()) > 8 << 30:
                raise OSError('Owned output cap')
            started = time.monotonic()
            row = dict(index=case['index'], seed=case['seed'], state='starting', wall_seconds=0.)
            ledger.append(row)
            atomic(out / 'ledger.json', ledger)
            directory = out / ('world-' + str(case['index']))
            def enable_beta(target):
                script = BASE.parent / 'predictor-resolution-20261020/enable_beta_copy.py'
                # This preparation process is Python only, not a second BDS server.
                subprocess.run(['docker', 'run', '--rm', '--pull=never', '--read-only', '--network', 'none',
                    '--name', 'codex-generalization-beta-' + uuid.uuid4().hex[:10],
                    '--cpus', '1', '--memory', '256m', '--pids-limit', '32',
                    '--mount', f'type=bind,src={target},dst=/copy',
                    '--mount', f'type=bind,src={script},dst=/enable_beta_copy.py,readonly',
                    '--entrypoint', '/opt/reader/bin/python', IMAGE, '/enable_beta_copy.py'],
                    capture_output=True, text=True, check=True, timeout=30)
            try:
                report = run_world(case, directory, wall, 'docker', digest(raw), out,
                    observer_path=case['observer'], copied_world=case['source_world'],
                    script_api='2.11.0-beta', prepare_copy=enable_beta)
                row['report_sha256'] = digest((directory / 'report.json').read_bytes())
                row['source_unchanged'] = tree_hashes(Path(case['source_world'])) == case['source_world_hashes']
                identity = report.get('world_identity', {})
                console = (directory / 'console.log').read_text()
                ok = (report['status'] == 'observed' and
                    all(report.get(k) is True for k in ('clean_shutdown', 'owned_container_removed', 'save_confirmed')) and
                    row['source_unchanged'] and identity.get('dimension') == case['dimension'] and
                    identity.get('membershipAvailable') is True and
                    re.search(r'\bVersion: 1\.26\.52\.3(?:\s|$)', console) is not None)
                row.update(state='complete' if ok else 'failed', error=report.get('error'))
            except Exception as error:
                row.update(state='failed', error=type(error).__name__ + ': ' + str(error))
            finally:
                row['wall_seconds'] = time.monotonic() - started
                row['seed_cumulative_seconds'] = previous + row['wall_seconds']
                row['campaign_cumulative_seconds'] = total + row['wall_seconds']
                atomic(out / 'ledger.json', ledger)
            print(json.dumps(row), flush=True)
            if row['state'] != 'complete' or row['seed_cumulative_seconds'] > 600 or row['campaign_cumulative_seconds'] > 7200:
                raise RuntimeError('Followup failed or exhausted its budget; no new dispatch')
    return dict(copies=len(ledger), status='terminal', ledger=str(out / 'ledger.json'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    print(json.dumps(execute(enabled=args.execute)), flush=True)
```
## Observer template (twofrozen renderedfiles differonlyDIMENSION)
```javascript
// Targeted, read-only membership on a disposable already-saved world copy.
import {world, system} from '@minecraft/server';
const DIMENSION = 'overworld';
const tick = () => new Promise(resolve => system.run(resolve));
let busy = false;
world.afterEvents.worldLoad.subscribe(() => console.warn('TARGET_IDENTITY ' + JSON.stringify({
  seed: world.seed, api: '2.11.0-beta', players: world.getAllPlayers().length,
  dimension: DIMENSION,
  membershipAvailable: typeof world.getDimension(DIMENSION).getGeneratedStructures === 'function',
})));
system.afterEvents.scriptEventReceive.subscribe(async event => {
  if (event.id !== 'predictor_audit:observe') return;
  if (busy) { console.warn('TARGET_ERROR duplicate request'); return; }
  busy = true;
  let biomeReads = 0, blockReads = 0, membershipReads = 0;
  const dim = world.getDimension(DIMENSION), manager = world.tickingAreaManager;
  try {
    const q = JSON.parse(event.message);
    if (!Array.isArray(q.points) || !Array.isArray(q.columns) || q.columns.length ||
        q.points.length < 1 || q.points.length > 64) throw Error('Input cap');
    const chunks = new Map();
    for (const p of q.points) {
      if (!Array.isArray(p) || p.length !== 3 || !p.every(Number.isInteger) ||
          Math.max(Math.abs(p[0]), Math.abs(p[2])) > 5120 ||
          p[1] < (DIMENSION === 'nether' ? 0 : -64) ||
          p[1] > (DIMENSION === 'nether' ? 127 : 319)) throw Error('Invalid XYZ');
      chunks.set(Math.floor(p[0] / 16) + ',' + Math.floor(p[2] / 16), p);
    }
    if (chunks.size > 10) throw Error('Ticking-area cap');
    let index = 0;
    const loaded = [];
    for (const p of chunks.values()) {
      const [x,y,z] = p;
      let available = false;
      try { available = !!dim.getBlock({x,y,z}); blockReads++; } catch (_) { blockReads++; }
      if (!available) {
        const options = {dimension: dim, from: {x,y,z}, to: {x,y,z}};
        if (!manager.hasCapacity(options)) throw Error('Ticking-area capacity');
        let ready = false, failure;
        manager.createTickingArea('generalization_member_' + index++, options)
          .then(() => { ready = true; }).catch(error => { failure = error; });
        for (let n = 0; !ready && !failure && n < 100; n++) await tick();
        if (failure) throw failure;
        if (!ready) throw Error('Bounded chunk loading did not complete');
      }
      if (++blockReads > 8192 || !dim.getBlock({x,y,z})) throw Error('Chunk unavailable');
      loaded.push({x,y,z});
    }
    const rows = [];
    for (const [x,y,z] of q.points) {
      try {
        if (++biomeReads > 128 || ++blockReads > 8192 || ++membershipReads > 64) throw Error('Read cap');
        const id = dim.getBiome({x,y,z}).id;
        const block = dim.getBlock({x,y,z});
        if (!block) throw Error('Block unavailable');
        const structures = dim.getGeneratedStructures({x,y,z});
        if (!Array.isArray(structures) || structures.some(s => typeof s !== 'string')) throw Error('Unsupported membership result');
        rows.push({x,y,z,dimension:DIMENSION,id,block:block.typeId,structures});
      } catch (error) { rows.push({x,y,z,dimension:DIMENSION,error:String(error)}); }
      await tick();
    }
    // Hold owned areas through the caller's save and clean shutdown, on this copy only.
    console.warn('TARGET_RESULT ' + JSON.stringify({rows,columns:[],loaded,
      biomeReads,blockReads,membershipReads,tickingAreas:index,chunks:manager.chunkCount,
      interpretation:'Point membership in Beta-API copied world; not an instance census or default-settings certification'}));
  } catch (error) {
    console.warn('TARGET_ERROR ' + JSON.stringify({error:String(error),biomeReads,blockReads,membershipReads}));
  }
});
```
## Existing target helper cleanup
```python
    finally:
        if process is not None and process.poll() is None:
            try:
                process.stdin.write('stop\n')
                process.stdin.flush()
                process.wait(timeout=25)
            except (OSError, subprocess.TimeoutExpired):
                pass
        report['clean_shutdown'] = process is not None and process.poll() == 0
        report['owned_container_removed'] = False
        try:
            inspected = subprocess.run([docker, 'inspect', name], capture_output=True, text=True, timeout=10)
            if inspected.returncode == 0:
                info = json.loads(inspected.stdout)[0]
                if (info['Config'].get('Labels') or {}).get('seed-search.targeted') != token:
                    raise RuntimeError('Owned container identity mismatch')
                subprocess.run([docker, 'rm', '--force', name], capture_output=True, check=True, timeout=20)
            report['owned_container_removed'] = subprocess.run([docker, 'inspect', name], capture_output=True, timeout=10).returncode != 0
        except Exception as error:
            report['cleanup_error'] = type(error).__name__ + ': ' + str(error)
        if process is not None:
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.terminate()
                process.wait(timeout=5)
            reader.join(timeout=3)
        log.close()
        report['wall_seconds'] = time.monotonic() - started
        (directory / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    return report

```
