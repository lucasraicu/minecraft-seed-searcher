"""Trace private pinned C copies; preserve installed behavior and unknown authority.

Record active lazy MT state, seed epochs/draw positions, angle precision, exact
floor/truncation differences, search windows, candidate order and viability.
An independent exact-build trace is still needed to identify a game divergence.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / 'vendor/cubiomes-bedrock'
SEEDS = (-1, 0, 9, 12345, 4294979641, -(1 << 63), (1 << 63) - 1)

MT_TRACE = r'''
int ss_trace_enabled;
static uint64_t ss_trace_epoch, ss_trace_draw;
static void ss_trace_state(const char *event) {
 if (!ss_trace_enabled) return;
 fprintf(stdout,"{\"event\":\"%s\",\"epoch\":%llu,\"draw\":%llu,\"index\":%zu,\"lazy_initialized_slots\":%zu,\"population_cache_initialized\":%d,\"population_cache_seed\":\"%llu\",\"population_a\":%d,\"population_b\":%d,\"active_mt\":[",event,(unsigned long long)ss_trace_epoch,(unsigned long long)ss_trace_draw,state.index,state.index_fast,mt_initialized,(unsigned long long)mt_ws,mt_a,mt_b);
 for(size_t i=0;i<state.index_fast;i++)fprintf(stdout,"%s%u",i?",":"",state.MT[i]);
 fprintf(stdout,"]}\n");
}
'''


def replace_once(source, old, new):
    assert source.count(old) == 1, old
    return source.replace(old, new, 1)


def build(folder):
    folder.mkdir(parents=True, exist_ok=True)
    mt = (VENDOR / 'mt.c').read_text()
    mt = replace_once(mt, '\n#define M32(x)', MT_TRACE + '\n#define M32(x)')
    mt = replace_once(mt, '  state.index_fast = PERIOD + 1;\n  state.index = SIZE;\n}', r'''  state.index_fast = PERIOD + 1;
  state.index = SIZE;
  if(ss_trace_enabled) {
    ss_trace_epoch++;ss_trace_draw=0;
    fprintf(stdout,"{\"event\":\"mt_seed\",\"seed_lower32\":%u,\"epoch\":%llu}\n",value,(unsigned long long)ss_trace_epoch);
    ss_trace_state("mt_seed_state");
  }
}''')
    mt = replace_once(mt, '  return temper(generate());', r'''  size_t before=state.index,lazy_before=state.index_fast;
  uint32_t value=temper(generate());
  if(ss_trace_enabled) {
    ss_trace_draw++;
    fprintf(stdout,"{\"event\":\"mt_draw\",\"epoch\":%llu,\"draw\":%llu,\"value\":%u,\"index_before\":%zu,\"index_after\":%zu,\"lazy_before\":%zu,\"lazy_after\":%zu}\n",(unsigned long long)ss_trace_epoch,(unsigned long long)ss_trace_draw,value,before,state.index,lazy_before,state.index_fast);
  }
  return value;''')
    (folder / 'mt-trace.c').write_text(mt)
    source = (VENDOR / 'finders.c').read_text()
    start = source.index('int nextVillageStronghold(')
    end = source.index('\nint getStaticStronghold(', start)
    body = source[start:end]
    body = replace_once(body, 'float angle = 2.0 * PI * nextFloat();', r'''float angle_draw = nextFloat();
        double angle_double = 2.0 * PI * angle_draw;
        float angle = angle_double;
        fprintf(stdout,"{\"event\":\"initial_angle\",\"full64_seed\":\"%lld\",\"draw_as_float\":%.17g,\"angle_before_float_cast\":%.17g,\"angle_after_float_cast\":%.17g}\n",(long long)g->seed,(double)angle_draw,angle_double,(double)angle);''')
    body = replace_once(body, 'int dist = 40 + nextInt(16);', r'''int distance_draw = nextInt(16);
        int dist = 40 + distance_draw;
        fprintf(stdout,"{\"event\":\"initial_distance\",\"draw_mod16\":%d,\"distance\":%d}\n",distance_draw,dist);''')
    body = replace_once(body, 'int cz = (int)floor(sin(sh->angle) * sh->dist);', r'''int cz = (int)floor(sin(sh->angle) * sh->dist);
        double rawx=cos(sh->angle)*sh->dist,rawz=sin(sh->angle)*sh->dist;
        fprintf(stdout,"{\"event\":\"attempt\",\"stronghold_index\":%d,\"angle_double\":%.17g,\"distance\":%.17g,\"raw_chunk\":[%.17g,%.17g],\"floor_chunk\":[%d,%d],\"hypothetical_truncated_chunk\":[%d,%d]}\n",sh->index,sh->angle,sh->dist,rawx,rawz,cx,cz,(int)rawx,(int)rawz);''')
    body = replace_once(body, 'Pos r1 = chunkToRegion(maxChunkX, maxChunkZ, sc.regionSize);', r'''Pos r1 = chunkToRegion(maxChunkX, maxChunkZ, sc.regionSize);
            fprintf(stdout,"{\"event\":\"window\",\"inclusive_chunk_bounds\":[%d,%d,%d,%d],\"inclusive_region_bounds\":[%d,%d,%d,%d],\"region_size_chunks\":%d}\n",minChunkX,minChunkZ,maxChunkX,maxChunkZ,r0.x,r0.z,r1.x,r1.z,sc.regionSize);''')
    body = replace_once(body, 'p = getLargeStructurePos(sc, g->seed, rx, rz);', r'''p = getLargeStructurePos(sc, g->seed, rx, rz);
                    fprintf(stdout,"{\"event\":\"region_candidate\",\"region\":[%d,%d],\"village_block\":[%d,%d],\"village_chunk\":[%d,%d]}\n",rx,rz,p.x,p.z,p.x>>4,p.z>>4);''')
    old = 'if (!isViableStructurePos(Village, gm, p.x, p.z, 0))'
    assert body.count(old) == 2
    body = body.replace(old, r'''int viable=isViableStructurePos(Village,gm,p.x,p.z,0);
                fprintf(stdout,"{\"event\":\"sorted_candidate\",\"order\":%d,\"position\":[%d,%d],\"biome_quart\":%d,\"viable\":%d}\n",i,p.x,p.z,getBiomeAt(gm,4,p.x>>2,0,p.z>>2),viable);
                if (!viable)''', 1)
    body = body.replace('sh->index++;\n                placed = 1;', r'''sh->index++;
                fprintf(stdout,"{\"event\":\"accepted\",\"index\":%d,\"stronghold_stairway_block\":[%d,%d],\"village_start_offset\":[-4,-4]}\n",sh->index,sh->pos.x,sh->pos.z);
                placed = 1;''', 1)
    (folder / 'finders-trace.c').write_text('#include <stdio.h>\n' + source[:start] + body + source[end:])
    (folder / 'main.c').write_text(r'''#include <stdlib.h>
#include "generator.h"
#include "finders.h"
extern int ss_trace_enabled;
int main(int argc,char **argv) {
 if(argc!=2)return 2;
 Generator g;setupGenerator(&g,MC_26_50,0);
 applySeed(&g,DIM_OVERWORLD,(uint64_t)strtoll(argv[1],0,10));
 ss_trace_enabled=1;
 StrongholdIter it={0};for(int i=0;i<3;i++)nextVillageStronghold(&it,&g);
 return 0;
}
''')
    units = ('noise', 'biomes', 'layers', 'biomenoise', 'cave', 'generator', 'util', 'quadbase')
    binary = folder / 'trace'
    command = ['clang', '-O3', '-std=c11', '-fwrapv', '-I', str(VENDOR),
               str(folder / 'finders-trace.c'), str(folder / 'mt-trace.c'), str(folder / 'main.c'),
               *[str(VENDOR / (u + '.c')) for u in units], '-lm', '-o', str(binary)]
    result = subprocess.run(command, capture_output=True, text=True)
    (folder / 'build.log').write_text(result.stdout + result.stderr)
    result.check_returncode()
    return binary


def main(output):
    from seed_search import _native
    from seed_search.backend import Backend
    installed_hash = hashlib.sha256(Path(_native.__file__).read_bytes()).hexdigest()
    folder = Path(output).resolve()
    binary = build(folder)
    summary = []
    for seed in SEEDS:
        text = subprocess.check_output([str(binary), str(seed)], text=True)
        (folder / f'{seed}.jsonl').write_text(text)
        events = [json.loads(line) for line in text.splitlines()]
        accepted = [tuple(e['stronghold_stairway_block']) for e in events if e['event'] == 'accepted']
        assert len(accepted) == 3 and len(set(accepted)) == 3
        with Backend(seed) as backend:
            installed = set()
            for x, z in accepted:
                installed.update(map(tuple, backend.structures('stronghold', (x, z, x, z))))
        assert set(accepted).issubset(installed)
        draws = [e for e in events if e['event'] == 'mt_draw']
        assert draws and all(e['index_after'] == (0 if e['index_before'] == 624 else e['index_before']) + 1 for e in draws)
        summary.append({'seed': str(seed), 'events': len(events), 'accepted': accepted,
                        'mt_draws': len(draws), 'trace_matches_installed_village_starts': True,
                        'attempts_with_floor_truncation_difference': sum(e['floor_chunk'] != e['hypothetical_truncated_chunk'] for e in events if e['event'] == 'attempt')})
    assert hashlib.sha256(Path(_native.__file__).read_bytes()).hexdigest() == installed_hash
    report = {'seeds': summary, 'private_source_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (folder / 'finders-trace.c', folder / 'mt-trace.c', folder / 'main.c')},
              'installed_native_sha256': installed_hash,
              'installed_native_unchanged': True, 'actual_game_trace_available': False,
              'mt_tail_policy': 'Only active lazy-initialized slots are recorded; retained inactive tail bytes are excluded.',
              'rounding_alternative_status': 'Diagnostic only; no rounding change installed.',
              'root_cause': 'UNRESOLVED: same-model trace parity cannot identify the first divergence from exact Bedrock without an independent game trace.'}
    (folder / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    main(parser.parse_args().output)
