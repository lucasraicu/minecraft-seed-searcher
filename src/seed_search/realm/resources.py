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
    total=0;seen=set()
    for folder,_,files in os.walk(root,followlinks=False):
        for name in files:
            path=Path(folder)/name
            if path.is_symlink():continue
            try:stat=path.stat()
            except FileNotFoundError:continue  # e.g. SQLite's removed WAL
            key=(stat.st_dev,stat.st_ino)
            if key not in seen:
                seen.add(key);total+=stat.st_size
    return total


def disk_status(root,policy,*,additional_bytes=0,remaining_seeds=0,completed_seeds=0,bytes_per_seed=None):
    try:
        used=workspace_usage(root);free=shutil.disk_usage(root).free
    except OSError as exc:
        raise WorkspaceCapacityError('Workspace disk monitoring unavailable; checkpoint retained') from exc
    estimate=policy['projected_bytes_per_seed'] if bytes_per_seed is None else bytes_per_seed
    if bytes_per_seed is None and completed_seeds >= 128:
        minimum = 1 if policy.get('retention') == 'survivors' else 4096
        estimate = max(minimum, estimate, int(used / completed_seeds * 1.5))
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
