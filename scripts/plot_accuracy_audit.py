"""Export a terrain comparison figure from the frozen audit observations."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
D=Path('runs/accuracy-audit')
rows=json.loads((D/'biome-terrain-comparison.json').read_text())['points']
rows=[v for v in rows if v['mode']=='surface']
x=np.array([v['chunkbase_marker_y'] for v in rows]);y=np.array([v['local_height'] for v in rows]);p=np.array([v['cheap_height_proxy'] for v in rows])
fig,axes=plt.subplots(1,2,figsize=(11,4.4),layout='constrained')
axes[0].scatter(x,y,s=20,alpha=.75,color='#2563eb',label='135 sampled columns')
axes[0].plot([min(x)-5,max(x)+5],[min(x)-5,max(x)+5],color='#475569',linewidth=1,label='Equal heights')
axes[0].axhline(63,color='#ef4444',alpha=.35,linewidth=1)
axes[0].axvline(63,color='#ef4444',alpha=.35,linewidth=1)
axes[0].set(xlabel='Chunkbase marker Y',ylabel='Local density ground Y',title='Density height agreement')
axes[0].legend(frameon=False,fontsize=8)
axes[1].hist(y-x,bins=np.arange(-20.5,21.5,1),alpha=.7,color='#2563eb',label='Density estimate: MAE 1.00 blocks')
axes[1].hist(p-x,bins=np.arange(-20.5,21.5,1),histtype='step',linewidth=1.8,color='#f97316',label='Cheap proxy: MAE 2.84 blocks')
axes[1].set(xlabel='Local minus Chunkbase height (blocks)',ylabel='Columns',title='Height error distribution')
axes[1].legend(frameon=False,fontsize=8)
for ax in axes:ax.spines[['top','right']].set_visible(False);ax.grid(alpha=.12)
fig.suptitle('Bedrock 26.52 predictor comparison · four seeds',fontsize=13)
fig.savefig(D/'terrain-comparison.png',dpi=180)
print(D/'terrain-comparison.png')
