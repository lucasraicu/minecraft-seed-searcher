"""Ablate unused setup in the diagnostic copy to inspect remaining costs."""
import shutil
from experiment import WORK, OPENMP, lazy_source, replace_once, OUT, write_json
from scripts import build_blueprint_batch as builder

source=WORK/'diagnostic';target=WORK/'diagnostic-optimized'
shutil.copytree(source,target,ignore=shutil.ignore_patterns('native-build'))
p=target/'native/blueprint_dynamic.inc';p.write_text(lazy_source(p.read_text()))
p=target/'vendor/cubiomes-bedrock/finders.c';text=p.read_text()
start=text.index('    case Mansion:',text.index('int isViableStructurePos('))
end=text.index('    case Ruined_Portal:',start);block=text[start:end]
block=replace_once(block,'                SurfaceNoise sn;\n','')
block=replace_once(block,'                initSurfaceNoise(&sn, DIM_OVERWORLD, g->seed);\n','')
block=replace_once(block,'mapApproxHeight(&height, &biome_id, g, &sn, x >> 2, z >> 2, 1, 1);',
                      'mapApproxHeight(&height, &biome_id, g, NULL, x >> 2, z >> 2, 1, 1);')
p.write_text(text[:start]+block+text[end:])
builder.ROOT=target
identity=builder.build(target/'native-build',openmp_prefix=OPENMP,work_chunk=16,cpu_native=True,lto=True)
write_json(OUT/'builds/diagnostic-optimized.json',identity)
