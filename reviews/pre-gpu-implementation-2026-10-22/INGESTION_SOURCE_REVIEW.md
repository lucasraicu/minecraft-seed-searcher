High read-only tool-free numerical/durability critique. Do not invoke tools, edits, commands, tests or notification. User approved B. No validation/frequency/nativework changed. Source follows.

ATOMIC WRITER
def atomic_json(path: Path | str, value: Any) -> None:
    """Write strict finite JSON value atomically via temporary file and replace."""
    atomic_bytes(path, strict_json_dumps(value))


def atomic_bytes(path: Path | str, encoded: bytes) -> None:
    """Publish already-encoded immutable bytes with the same durable boundary."""
    if not isinstance(encoded, bytes):
        raise TypeError('Atomic payload must be immutable bytes')
    target = verify_no_symlinks(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    verify_no_symlinks(target.parent)

    tmp_path = target.with_name(f".{target.name}.tmp.{os.getpid()}.{time.time_ns()}")
    try:
        with open(tmp_path, 'wb') as f:
            f.write(encoded)
            f.flush()
            os.fsync(f.fileno())
        verify_no_symlinks(tmp_path)
        verify_no_symlinks(target)
        os.replace(tmp_path, target)
        directory = os.open(target.parent, os.O_RDONLY)
        try: os.fsync(directory)
        finally: os.close(directory)
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass




CHECKPOINT
def checkpoint_observation(path, *, protocol=1):
    path=verify_no_symlinks(path)
    if path.stat().st_size>32<<20:raise ValueError('Oversized checkpoint')
    value=json.loads(path.read_bytes())
    if (not isinstance(value,dict) or set(value)!={'sha256','observation'} or
            value['sha256']!=digest(value['observation'])):
        raise ValueError('Checkpoint checksum mismatch')
    if protocol==2:
        from .models import validate_observation_v2
        return validate_observation_v2(value['observation'])
    return validate_observation(value['observation'])


def save_checkpoint(path,value):
    # Hash and embed the exact same canonical bytes. Previously the full survey
    # was encoded once for its digest and again with expensive pretty indentation.
    # The envelope and reader stay compatible; every progress callback still
    # flushes/fsyncs its file and parent directory before returning.
    from .registry import canonical_json
    raw=canonical_json(value)
    checksum=hashlib.sha256(raw).hexdigest().encode('ascii')
    atomic_bytes(path,b'{"observation":'+raw+b',"sha256":"'+checksum+b'"}')




NUMERIC HELPERS
def _biome_arrays(points_by_feature):
    """One call-local integer index; never retain a mutable observation globally."""
    import numpy as np
    return {fid: np.asarray(points,dtype=np.int64) for fid,points in points_by_feature.items()
            if len(points)>64}


def _indexed_biome_summary(points, cx, cz, box, radii):
    """Exact integer distances and lexicographic XYZ ties, matching the V3 loop."""
    import numpy as np
    lo_x,hi_x,lo_z,hi_z=box
    selected=points[(points[:,0]>=lo_x)&(points[:,0]<hi_x)&
                    (points[:,2]>=lo_z)&(points[:,2]<hi_z)]
    if not len(selected):return [0,0,0,0],None,None
    d2=(selected[:,0]-cx)**2+(selected[:,2]-cz)**2
    nearest=int(d2.min());tied=selected[d2==nearest]
    index=np.lexsort((tied[:,2],tied[:,1],tied[:,0]))[0]
    witness=[int(n) for n in tied[index,:3]]
    return [int(nearest<=r*r) for r in radii]+[1],nearest,witness




V3 loop uses arrays only when a feature has>64points; smallerlists retain originalscalarloop. Index is per-call, np.int64 XYZ+sampleidx. Halfopenborder filter, squaredintegerdistance, exact lexical(d2,x,y,z)tie, countsboolean from minimumradius. Original V3 scalar loop had nearest=min(d2,x,y,z); complete flags remain fourFalse. V2 untouched.

Tests: oldreader+oldwriter roundtrip, tamper, fsync twice, replacefail oldbytes retained,temp cleanup, NaN rejection, scalarindependent random/negative/border/XYZtie oracle. Actual complete246summary output SHA beforeafter exactsamef182deacbd6b11143378f7b66bee0819c442b6441ad5e1db885475ad017020a4. 3unprofiledtrials median5.859->2.432secs; checkpoint.131->.061secs. Noendtoendclaim yet.