# Exact source for low-cost spawn proposal review
Read SPAWN_CORRECTION_PROPOSAL.md plus these source excerpts; do not infer a deployed fix. All runs used isolated helper, unchanged repository finders.c and no new game worlds.

```c
static
uint64_t calcFitness(const Generator *g, int x, int z)
{
    int64_t np[6];
    uint32_t flags = SAMPLE_NO_DEPTH | SAMPLE_NO_BIOME;
    sampleBiomeNoise(&g->bn, np, x>>2, 0, z>>2, NULL, flags);
    const int64_t spawn_np[][2] = {
        {-10000,10000},{-10000,10000},{-1100,10000},{-10000,10000},{0,0},
        {-10000,-1600},{1600,10000} // [6]: weirdness for the second noise point
    };
    uint64_t ds = 0, ds1 = 0, ds2 = 0;
    uint64_t a, b, q, i;
    for (i = 0; i < 5; i++)
    {
        a = +np[i] - (uint64_t)spawn_np[i][1];
        b = -np[i] + (uint64_t)spawn_np[i][0];
        q = (int64_t)a > 0 ? a : (int64_t)b > 0 ? b : 0;
        ds += q * q;
    }
    a = +np[5] - (uint64_t)spawn_np[5][1];
    b = -np[5] + (uint64_t)spawn_np[5][0];
    q = (int64_t)a > 0 ? a : (int64_t)b > 0 ? b : 0;
    ds1 = ds + q*q;
    a = +np[5] - (uint64_t)spawn_np[6][1];
    b = -np[5] + (uint64_t)spawn_np[6][0];
    q = (int64_t)a > 0 ? a : (int64_t)b > 0 ? b : 0;
    ds2 = ds + q*q;
    ds = ds1 <= ds2 ? ds1 : ds2;
    // apply dependence on distance from origin
    a = (int64_t)x*x;
    b = (int64_t)z*z;
    if (g->mc < MC_1_21_60)
    {
        double s = (double)(a + b) / (2500 * 2500);
        q = (uint64_t)(s*s * 1e8) + ds;
    }
    else
    {
        q = ds * (2048LL * 2048LL) + a + b;
    }
    return q;
}

static
void findFittest(const Generator *g, Pos *pos, uint64_t *fitness, double maxrad, double step)
{
    double rad, ang;
    Pos p = *pos;
    for (rad = step; rad <= maxrad; rad += step)
    {
        for (ang = 0; ang <= PI*2; ang += step/rad)
        {
            int x = p.x + (int)(sin(ang) * rad);
            int z = p.z + (int)(cos(ang) * rad);
            uint64_t fit = calcFitness(g, x, z);
            // Then update pos and fitness if combined total is lower/better
            if (fit < *fitness)
            {
                pos->x = x;
                pos->z = z;
                *fitness = fit;
            }
        }
    }
}

static
Pos findFittestPos(const Generator *g)
{
    Pos spawn = {0, 0};
    uint64_t fitness = calcFitness(g, 0, 0);
    findFittest(g, &spawn, &fitness, 2048.0, 512.0);
    findFittest(g, &spawn, &fitness, 512.0, 32.0);
    // center of chunk
    spawn.x = (spawn.x & ~15) + 8;
    spawn.z = (spawn.z & ~15) + 8;
    return spawn;
}


```
```python
#!/usr/bin/env python3
"""Build vendor-based estimateSpawn helper outside the repository."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from seed_search.realm.native_identity import native_source_fingerprint

UNITS = 'noise biomes layers biomenoise cave generator finders util quadbase mt'.split()
SYSTEM_SYMLINKS = {Path('/var'), Path('/tmp'), Path('/etc'), Path('/private/var'), Path('/private/tmp')}

C_SOURCE = r"""/* Minimal estimateSpawn helper: reads canonical signed64 seed lines, applies
 * MC_26_50 DIM_OVERWORLD, calls estimateSpawn twice, outputs JSON row.
 */
#include "finders.h"
#include "generator.h"
#include <errno.h>
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>

static int parse_seed(const char *s, int64_t *out) {
    char *end;
    errno = 0;
    intmax_t v = strtoimax(s, &end, 10);
    if (errno != 0 || end == s || *end != '\0' || v < INT64_MIN || v > INT64_MAX) {
        return 0;
    }
    *out = (int64_t)v;
    return 1;
}

int main(void) {
    Generator *g = calloc(1, sizeof(*g));
    if (!g) return 2;
    setupGenerator(g, MC_26_50, 0);
    char line[256];
    while (fgets(line, sizeof(line), stdin)) {
        char *nl = strchr(line, '\n');
        if (nl) *nl = '\0';
        else if (!feof(stdin)) { free(g); return 3; }
        char *s = line;
        while (isspace((unsigned char)*s)) s++;
        if (!*s) continue;
        char *end = s + strlen(s);
        while (end > s && isspace((unsigned char)*(end - 1))) end--;
        *end = '\0';
        int64_t seed = 0;
        if (!parse_seed(s, &seed)) { free(g); return 3; }
        char canonical[32];
        snprintf(canonical, sizeof(canonical), "%" PRId64, seed);
        if (strcmp(canonical, s)) { free(g); return 3; }
        applySeed(g, DIM_OVERWORLD, (uint64_t)seed);
        Pos p1 = estimateSpawn(g, NULL);
        applySeed(g, DIM_OVERWORLD, (uint64_t)seed);
        Pos p2 = estimateSpawn(g, NULL);
        printf("{\"seed\":\"%s\",\"estimate\":[%d,%d],\"repeat_estimate\":[%d,%d]}\n",
               s, p1.x, p1.z, p2.x, p2.z);
        fflush(stdout);
    }
    free(g);
    return ferror(stdin) ? 3 : 0;
}
"""


def validate_output_path(output_path):
    path = Path(output_path)
    output = path.resolve()
    manifest = Path(str(output) + '.build.json')
    try:
        raw_rel = path.is_relative_to(ROOT)
    except ValueError:
        raw_rel = False
    if raw_rel or output.is_relative_to(ROOT) or output == ROOT:
        raise ValueError('Use a new output path outside the repository')
    if path.is_symlink() or output.is_symlink():
        raise ValueError('Output path cannot be a symlink')
    for parent in path.parents:
        if parent not in SYSTEM_SYMLINKS and parent.is_symlink():
            raise ValueError('Refuse symlink traversal in output path')
    if path.exists() or output.exists():
        raise ValueError('Output path already exists')
    if manifest.exists() or manifest.is_symlink() or Path(str(path) + '.build.json').exists():
        raise ValueError('Build manifest already exists')
    return output, manifest


def build_spawn_estimator(output_path):
    output, manifest = validate_output_path(output_path)
    vendor = ROOT / 'vendor/cubiomes-bedrock'
    sources = [vendor / (u + '.c') for u in UNITS]
    inputs = sources + sorted(vendor.glob('*.h')) + sorted((vendor / 'tables').glob('*.h'))
    hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
    hashes['embedded:spawn_estimator.c'] = hashlib.sha256(C_SOURCE.encode('utf-8')).hexdigest()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        c_file = Path(td) / 'spawn_estimator.c'
        c_file.write_text(C_SOURCE)
        command = ['cc', '-O2', '-std=c11', '-fwrapv', '-I', str(vendor),
                   str(c_file), *map(str, sources), '-lm', '-o', str(output)]
        subprocess.run(command, check=True, timeout=60)
    source_sha = native_source_fingerprint()
    if not source_sha:
        raise ValueError('Native source fingerprint unavailable')
    compiler_line = subprocess.check_output(['cc', '--version'], text=True, timeout=10).splitlines()[0]
    record = dict(command=command, compiler=compiler_line,
                  binary_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),
                  source_sha256=source_sha, input_source_hashes=hashes, inputs=hashes)
    manifest.write_text(json.dumps(record, indent=2) + '\n')
    return output


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='Output executable path')
    args = parser.parse_args(argv)
    try:
        output = build_spawn_estimator(args.output)
    except ValueError as exc:
        parser.error(str(exc))
    print(output)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

```
