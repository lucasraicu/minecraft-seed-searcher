"""Finish bounded verification after the already-running mode experiment.

No production sweep is launched. Each phase has its own log and exit record.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from verify_approved_implementation import OUT, summary, write


def finish(experiment_pid):
    while True:
        try:
            os.kill(experiment_pid, 0)
        except ProcessLookupError:
            break
        time.sleep(5)
    path = OUT / 'mode-comparison.json'
    record = json.loads(path.read_text())
    assert record['complete'] is True
    # The earlier running interpreter predates added summary fields. Re-read
    # finished checkpoints without altering their invocations or predictions.
    record['arms'] = [summary(arm['path']) for arm in record['arms']]
    assert len(record['arms']) == 4
    assert {(a['run_key'], a['search_mode']) for a in record['arms']} == {
        (k, m) for k in record['run_keys']
        for m in ('full_64_bit_reference', 'lower32_staged')
    }
    write(path, record)
    phases = []
    for mode in ('parity', 'workers', 'recovery', 'pilot'):
        command = [sys.executable, 'scripts/verify_approved_implementation.py', mode]
        start = time.time()
        print(f'Starting {mode}', flush=True)
        log = OUT / f'{mode}.log'
        with log.open('a') as stream:
            result = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT)
        phases.append({'mode': mode, 'command': command, 'exit_code': result.returncode,
                       'wall_seconds': time.time() - start, 'log': str(log)})
        write(OUT / 'post-experiment-phases.json', phases)
        print(f'Finished {mode}: exit {result.returncode}', flush=True)
        if result.returncode:
            raise SystemExit(result.returncode)
    command = [sys.executable, 'scripts/verify_expanded_pilot.py',
               '--pilot', str(OUT / 'pilot-20'), '--repeat', str(OUT / 'repeat-20'),
               '--output', str(OUT)]
    with (OUT / 'pilot-proof.log').open('a') as stream:
        result = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT)
    if result.returncode:
        raise SystemExit(result.returncode)
    print('All bounded post-experiment workloads completed.', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--experiment-pid', type=int, required=True)
    finish(parser.parse_args().experiment_pid)
