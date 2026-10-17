"""Build scalar/SIMD controls for compare_noise.py; never changes production files."""
from pathlib import Path
import subprocess

REPO=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
scalar=subprocess.run(['git','show','15ab3ad:vendor/cubiomes-bedrock/noise.c'],cwd=REPO,check=True,capture_output=True,text=True).stdout
scalar+='\nvoid sampleDoublePerlin_4x(const DoublePerlinNoise *n,const double x[4],const double y[4],const double z[4],double out[4]) {for(int i=0;i<4;i++)out[i]=sampleDoublePerlin(n,x[i],y[i],z[i]);}\n'
(OUT/'noise_scalar_control.c').write_text(scalar)
units=['biomes','layers','biomenoise','cave','generator','finders','util','quadbase','mt']
base=['clang','-O3','-ffp-contract=off','-fwrapv','-std=c11','-dynamiclib','-Ivendor/cubiomes-bedrock',str(OUT/'noise_probe_wrapper.c')]
for name,source in [('scalar',OUT/'noise_scalar_control.c'),('simd',REPO/'vendor/cubiomes-bedrock/noise.c')]:
    command=base+[str(source)]+[f'vendor/cubiomes-bedrock/{u}.c' for u in units]+['-o',str(OUT/f'noise_{name}.dylib')]
    result=subprocess.run(command,cwd=REPO,capture_output=True,text=True)
    (OUT/f'noise_{name}_build.log').write_text(result.stdout+result.stderr)
    result.check_returncode()
