"""Explicit bounded drain. No implicit daemon and no personal score admission."""
from pathlib import Path
import time
import uuid

from .harvest import DEFAULT_CAPS
from .harvest_native import require_complete


def drain(queue, extract, publish, *, max_worlds=100, clock=time.monotonic):
    if type(max_worlds) is not int or not 1 <= max_worlds <= DEFAULT_CAPS['sample_cap']:
        raise ValueError('Drain max_worlds must be 1..100')
    with queue.supervisor() as acquired:
        if not acquired:
            return dict(revision='catalog-harvest-drain-v1',completed=0,failed=0,deferred=0,
                        stop_reason='worker_already_running',elapsed_seconds=0,queue=queue.status())
        return _drain(queue,extract,publish,max_worlds=max_worlds,clock=clock)


def _drain(queue, extract, publish, *, max_worlds, clock):
    started=clock();worker_id=uuid.uuid4().hex
    completed=failed=deferred=0;reason='max_worlds'
    # Per invocation cap never grows when campaigns carry different smaller caps.
    deadline=started+DEFAULT_CAPS['total_seconds']
    for _ in range(max_worlds):
        if clock()>=deadline:reason='wall_budget';break
        job=queue.claim(worker_id)
        if job is None:reason='no_ready_work';break
        deadline=min(deadline,started+job['caps']['total_seconds'])
        remaining=deadline-clock()
        if remaining<=0:
            queue.defer(job,'total wall budget');deferred+=1;reason='wall_budget';break
        try:
            observation=require_complete(extract(job,min(remaining,job['caps']['world_seconds'])),job['identity'])
            if clock()>=deadline:raise TimeoutError('Total drain wall budget exhausted')
            with queue.publication(job):
                snapshot=publish(job,observation)
                queue.acknowledge(job,snapshot)
            completed+=1
        except (KeyboardInterrupt, SystemExit):
            try:queue.defer(job,'operator interruption')
            except ValueError:pass  # Fenced job belongs to another generation.
            reason='interrupted';deferred+=1;break
        except (OSError, MemoryError, TimeoutError) as exc:
            try:queue.defer(job,f'{type(exc).__name__}: {exc}')
            except ValueError:pass
            reason='resource_or_storage_limit';deferred+=1;break
        except Exception as exc:
            try:queue.fail(job,f'{type(exc).__name__}: {exc}',partial=Path(job['checkpoint']).is_file())
            except ValueError:pass
            failed+=1
    return dict(revision='catalog-harvest-drain-v1',completed=completed,failed=failed,
                deferred=deferred,stop_reason=reason,elapsed_seconds=clock()-started,queue=queue.status())
