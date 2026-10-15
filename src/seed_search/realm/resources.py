"""Physical workspace accounting, including SQLite/WAL and retained evidence."""
from pathlib import Path
import os
import shutil
import time


class WorkspaceCapacityError(RuntimeError):
    pass


def disk_policy(search, retention='full'):
    if retention not in ('full', 'survivors'):
        raise ValueError('Unsupported retention mode')
    rate = search.get('compact_projected_bytes_per_seed', 32) if retention == 'survivors' else search.get('projected_bytes_per_seed', 65536)
    values = {
        'run_disk_limit_bytes': search.get('run_disk_limit_bytes', 128 << 30),
        'free_disk_reserve_bytes': search.get('free_disk_reserve_bytes', 16 << 30),
        'projected_bytes_per_seed': rate,
        'retention': retention,
    }
    for key, value in values.items():
        if key != 'retention' and (isinstance(value, bool) or not isinstance(value, int) or value < 1):
            raise ValueError(f'{key} must be a positive integer')
    return values


def workspace_usage(root):
    """No symlink traversal or deletion. Hard links are counted once per inode."""
    total = 0
    seen = set()
    stack = [os.fspath(root)]
    while stack:
        curr = stack.pop()
        try:
            with os.scandir(curr) as it:
                for entry in it:
                    try:
                        if entry.is_symlink():
                            continue
                        if entry.is_dir():
                            stack.append(entry.path)
                        elif entry.is_file():
                            st = entry.stat(follow_symlinks=False)
                            key = (st.st_dev, st.st_ino)
                            if key not in seen:
                                seen.add(key)
                                total += st.st_size
                    except FileNotFoundError:
                        continue
        except OSError:
            continue
    return total


def disk_status(root,policy,*,additional_bytes=0,remaining_seeds=0,completed_seeds=0,bytes_per_seed=None,initial_used_bytes=None,previous_sample=None):
    try:
        used=workspace_usage(root);free=shutil.disk_usage(root).free
    except OSError as exc:
        raise WorkspaceCapacityError('Workspace disk monitoring unavailable; checkpoint retained') from exc
    if initial_used_bytes is not None:
        policy.update(initial_used_bytes=initial_used_bytes,initial_completed_seeds=0)
    if 'initial_used_bytes' not in policy:
        # Persist bytes and coverage together: a legacy/resumed run without a
        # baseline starts a new observation interval, not a per-seed startup tax.
        previous=previous_sample if isinstance(previous_sample,dict) else {}
        initial=previous.get('initial_used_bytes')
        initial_completed=previous.get('initial_completed_seeds')
        valid=(type(initial) is int and initial>=0 and type(initial_completed) is int
               and 0<=initial_completed<=completed_seeds)
        policy.update(initial_used_bytes=initial if valid else used,
                      initial_completed_seeds=initial_completed if valid else completed_seeds)
    initial=policy['initial_used_bytes']
    initial_completed=policy.get('initial_completed_seeds',0)
    observed_seeds=completed_seeds-initial_completed
    estimate=policy['projected_bytes_per_seed'] if bytes_per_seed is None else bytes_per_seed
    if bytes_per_seed is None and observed_seeds >= 128:
        minimum = 1 if policy.get('retention') == 'survivors' else 4096
        # SQLite checkpointing can shrink the WAL below the initial footprint.
        marginal=max(0,used-initial)
        estimate=max(minimum,estimate,int(marginal/observed_seeds*1.5))
    projected = used + remaining_seeds * estimate
    required_free=policy['free_disk_reserve_bytes']+additional_bytes
    result={**policy,'run_bytes':used,'free_bytes':free,'additional_bytes':additional_bytes,
            'projected_run_bytes':projected,'bytes_per_seed_estimate':estimate,
            'scope':'run-owned files including database/WAL/exports/evidence; external Docker storage excluded',
            'sampled_at':time.time()}
    if used+additional_bytes>policy['run_disk_limit_bytes'] or free<required_free:
        raise WorkspaceCapacityError('Workspace disk cap or free-space reserve reached; checkpoint retained')
    if projected>policy['run_disk_limit_bytes'] or free<policy['free_disk_reserve_bytes']+max(0,projected-used):
        raise WorkspaceCapacityError('Projected finite shard exceeds disk budget; use a smaller shard')
    return result


def process_tree_resources(root_pid=None):
    # Preserve the complete-tree availability contract; partial SELF data is diagnostic only.
    from .runner import process_tree_resources as monitor
    return monitor(root_pid)
