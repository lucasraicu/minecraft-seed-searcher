"""Private post-gate attribution. Never used for throughput comparisons."""
import shutil
from experiment import WORK, OUT, OPENMP, replace_once, write_json
from scripts import build_blueprint_batch as builder

target=WORK/'diagnostic-gate'
shutil.copytree(WORK/'diagnostic-optimized',target,ignore=shutil.ignore_patterns('native-build'))
p=target/'native/blueprint_dynamic.inc';text=p.read_text()
gate=(WORK/'dark-gate/native/blueprint_dynamic.inc').read_text()
helper=gate[gate.index('/* Necessary Y=63 witness only;'):gate.index('static int nb_eval_dynamic(')]
text=replace_once(text,'static int nb_eval_dynamic(',helper+'static int nb_eval_dynamic(')
text=replace_once(text,'    double sol_stage_started_9=sol_audit_time();',
    '    double sol_gate_started=sol_audit_time();\n'
    '    possible=nb_audit_dark_possible(w,feasible);\n'
    '    sol_audit_elapsed(12,sol_audit_time()-sol_gate_started);\n'
    '    if(possible<0){code=possible;goto done;}if(!possible)goto done;\n'
    '    double sol_stage_started_9=sol_audit_time();')
p.write_text(text)
# Remove the now-empty legacy initializer timing hook. Slot12 measures the gate.
p=target/'vendor/cubiomes-bedrock/finders.c';text=p.read_text()
text=replace_once(text,'                double sol_component_12=sol_audit_time();\n','')
text=replace_once(text,'                sol_audit_elapsed(12,sol_audit_time()-sol_component_12);\n','')
p.write_text(text)
builder.ROOT=target
identity=builder.build(target/'native-build',openmp_prefix=OPENMP,work_chunk=16,cpu_native=True,lto=True)
write_json(OUT/'builds/diagnostic-gate.json',identity)
