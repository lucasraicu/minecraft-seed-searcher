import os,sys,time
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'src'))
from seed_search.realm.native_batch import Prototype
from seed_search.realm.config import dynamic_blueprint_config
from seed_search.seeds import seed_from_index
p=Prototype('runs/dynamic-baseline-1664/native',dynamic_blueprint_config())
Path('/tmp/minecraft-sol-audit-20261015/sample.pid').write_text(str(os.getpid()))
seeds=[seed_from_index(i,2026101401) for i in range(70000000,70016384)]
for i in range(5):
 with p.sweep(seeds,1,retention='survivors'):pass
print('sampling workload completed')
