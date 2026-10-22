"""Opt-in immutable handoff, before personal qualification; never runs extraction."""
import hashlib
from pathlib import Path
import sqlite3


def prepare_campaign(search, output, start, count, personal_identity, root, *, sample_cap=100):
    from .harvest import make_descriptor, write_descriptor, HarvestQueue
    from .models import identity
    from .registry import digest
    from .ingestion import verify_no_symlinks
    from ..backend import model_metadata, native_runtime
    from ..realm.native_identity import native_source_fingerprint
    from ..realm.store import semantic_identity
    from .. import _native

    if type(sample_cap) is not int or not 1 <= sample_cap <= 100:
        raise ValueError('Catalog sample cap must be 1..100')
    run = verify_no_symlinks(Path(output).absolute())
    destination = verify_no_symlinks(Path(root).absolute())
    if run == destination or run in destination.parents or destination in run.parents:
        raise ValueError('Catalog and personal run roots must be separate and nonnested')
    native_runtime()  # Fail closed on source/binary drift, without rebuilding.
    template = identity('0', model_id=model_metadata()['model'],
                        source_sha256=native_source_fingerprint(),
                        native_sha256=hashlib.sha256(Path(_native.__file__).read_bytes()).hexdigest())
    sequence = {k: search[k] for k in ('sequence','run_key','low32','manifest_seeds') if k in search}
    from .automation import configuration,ensure_supervisor
    automation=configuration(destination)
    descriptor = make_descriptor(sequence, start, count, template, digest(semantic_identity(personal_identity)),
                                 destination, caps={'sample_cap': sample_cap},
                                 pipeline_revision=automation['policy_revision'] if automation else None)
    path = write_descriptor(run / 'catalog-handoff', descriptor)
    # Descriptor is durable even when queue registration is unavailable/contended.
    state, reason = 'registered', None
    try:
        with HarvestQueue(destination, busy_ms=250) as queue:
            queue.register(descriptor)
    except (OSError, sqlite3.Error, ValueError) as exc:
        state, reason = 'detached', f'{type(exc).__name__}: {str(exc)[:300]}'
    public_worker=None
    if automation is not None and state=='registered':
        try:public_worker=ensure_supervisor(destination)
        except (OSError,ValueError,sqlite3.Error) as exc:public_worker=dict(started=False,reason=str(exc)[:300])
    return dict(public_worker=public_worker,root=str(destination), sample_cap=sample_cap,
                campaign_id=descriptor['campaign_id'], descriptor_path=str(path),
                state=state, reason=reason,
                notice=('Configured independent public worker will drain this campaign within its durable budget; personal stop does not cancel it.' if automation else
                        'Catalog extraction requires an explicit drain command; personal stop does not cancel catalog work.'))
