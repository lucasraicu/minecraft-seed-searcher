"""Instrument a PRIVATE copy of the pinned village Stronghold iterator.

Never changes installed prediction behavior. JSONL exposes RNG initialization,
angle/distance, unique region order, sorted candidates, viability and acceptance.
An independent modern trace is still required to locate the external divergence.
"""
import json
import subprocess
from pathlib import Path
from seed_search.backend import Backend

OUT=Path('runs/implementation-2026-10-08/stronghold-trace')
VENDOR=Path('vendor/cubiomes-bedrock').resolve()

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    source=(VENDOR/'finders.c').read_text()
    start=source.index('int nextVillageStronghold(');end=source.index('\nint getStaticStronghold(',start)
    body=source[start:end]
    body=body.replace('float angle = 2.0 * PI * nextFloat();','float draw = nextFloat();\n        float angle = 2.0 * PI * draw;')
    body=body.replace('int dist = 40 + nextInt(16);','int distance_draw = nextInt(16);\n        int dist = 40 + distance_draw;\n        fprintf(stdout,"{\\\"event\\\":\\\"initial_rng\\\",\\\"seed\\\":\\\"%lld\\\",\\\"angle_draw\\\":%.17g,\\\"distance_draw\\\":%d,\\\"angle\\\":%.17g,\\\"distance\\\":%d}\\n",(long long)g->seed,(double)draw,distance_draw,(double)angle,dist);')
    body=body.replace('int cz = (int)floor(sin(sh->angle) * sh->dist);','int cz = (int)floor(sin(sh->angle) * sh->dist);\n        fprintf(stdout,"{\\\"event\\\":\\\"step\\\",\\\"index\\\":%d,\\\"angle\\\":%.17g,\\\"distance\\\":%.17g,\\\"chunk\\\":[%d,%d]}\\n",sh->index,sh->angle,sh->dist,cx,cz);')
    body=body.replace('p = getLargeStructurePos(sc, g->seed, rx, rz);','p = getLargeStructurePos(sc, g->seed, rx, rz);\n                    fprintf(stdout,"{\\\"event\\\":\\\"region\\\",\\\"region\\\":[%d,%d],\\\"village\\\":[%d,%d]}\\n",rx,rz,p.x,p.z);')
    body=body.replace('if (!isViableStructurePos(Village, gm, p.x, p.z, 0))','int viable=isViableStructurePos(Village, gm, p.x, p.z, 0);\n                fprintf(stdout,"{\\\"event\\\":\\\"sorted_candidate\\\",\\\"order\\\":%d,\\\"village\\\":[%d,%d],\\\"biome_quart\\\":%d,\\\"viable\\\":%d}\\n",i,p.x,p.z,getBiomeAt(gm,4,p.x>>2,0,p.z>>2),viable);\n                if (!viable)',1)
    body=body.replace('sh->index++;\n                placed = 1;','sh->index++;\n                fprintf(stdout,"{\\\"event\\\":\\\"accepted\\\",\\\"index\\\":%d,\\\"position\\\":[%d,%d]}\\n",sh->index,sh->pos.x,sh->pos.z);\n                placed = 1;',1)
    private=OUT/'finders-trace.c';private.write_text('#include <stdio.h>\n'+source[:start]+body+source[end:])
    mainfile=OUT/'main.c';mainfile.write_text('''#include <stdlib.h>
#include "generator.h"
#include "finders.h"
int main(int argc,char **argv) {
    Generator g;setupGenerator(&g,MC_26_50,0);applySeed(&g,DIM_OVERWORLD,(uint64_t)strtoll(argv[1],0,10));
    StrongholdIter it={0};for(int i=0;i<3;i++)nextVillageStronghold(&it,&g);return 0;
}
''')
    binary=OUT/'trace';units=['noise','biomes','layers','biomenoise','cave','generator','util','quadbase','mt']
    command=['clang','-O3','-std=c11','-fwrapv','-I',str(VENDOR),str(private),str(mainfile),*[str(VENDOR/(u+'.c')) for u in units],'-lm','-o',str(binary)]
    build=subprocess.run(command,capture_output=True,text=True);(OUT/'build.log').write_text(build.stdout+build.stderr);build.check_returncode()
    summary=[]
    for seed in (-1,0,12345,4294979641,9):
        text=subprocess.check_output([str(binary.resolve()),str(seed)],text=True);rows=[json.loads(v) for v in text.splitlines()]
        (OUT/f'{seed}.jsonl').write_text(text)
        accepted=[tuple(r['position']) for r in rows if r['event']=='accepted']
        with Backend(seed) as b:all_starts=b.structures('stronghold',(-7000,-7000,7000,7000))
        assert all(p in all_starts for p in accepted if max(abs(v) for v in p)<=7000)
        summary.append({'seed':str(seed),'events':len(rows),'accepted':accepted,'trace_matches_installed_village_starts':True})
    (OUT/'summary.json').write_text(json.dumps({'rows':summary,'root_cause':'unresolved; no independent modern RNG/candidate trace supplied','negative_coordinate_exceptions_installed':False},indent=2)+'\n')

if __name__=='__main__':main()
