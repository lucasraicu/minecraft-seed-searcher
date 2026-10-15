with open("reviews/split-audit-2026-10-15/gemini/probes/mem/trace_allocs.c") as f:
    text = f.read()

# Let's run trace_allocs and parse stdout
import subprocess
res = subprocess.run(["./reviews/split-audit-2026-10-15/gemini/probes/mem/trace_allocs"], capture_output=True, text=True)
lines = [l for l in res.stdout.splitlines() if l.startswith("malloc #")]
raw_dynamic_indices = {31, 32, 33, 34, 35, 36, 37}

nb_alloc_bytes = 0
raw_malloc_bytes = 0

for line in lines:
    parts = line.split()
    idx = int(parts[1].replace("#", "").replace(":", ""))
    sz = int(parts[2])
    if idx in raw_dynamic_indices:
        raw_malloc_bytes += sz
    else:
        nb_alloc_bytes += sz

print(f"Total nb_alloc bytes:  {nb_alloc_bytes:,} bytes ({nb_alloc_bytes/(1<<20):.3f} MiB)")
print(f"Total raw malloc bytes:{raw_malloc_bytes:,} bytes ({raw_malloc_bytes/(1<<20):.3f} MiB)")
print(f"Total live heap bytes: {nb_alloc_bytes + raw_malloc_bytes:,} bytes ({(nb_alloc_bytes + raw_malloc_bytes)/(1<<20):.3f} MiB)")
