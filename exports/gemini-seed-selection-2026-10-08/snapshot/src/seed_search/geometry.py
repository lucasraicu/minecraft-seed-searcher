"""Diagnostic connected land components; never certify real isolation."""
from __future__ import annotations
import math
import numpy as np
from scipy import ndimage

def band(value, low, high):
    return min(1.0,value/low,high/value) if value>0 else 0.0

def island_components(land: np.ndarray, x0: int, z0: int, spacing: int, center_bounds):
    labels,count=ndimage.label(land,np.ones((3,3),dtype=int))
    slices=ndimage.find_objects(labels)
    sizes=np.bincount(labels.ravel())
    result=[]
    low,high=center_bounds
    for label,sl in enumerate(slices,1):
        if sl is None:
            continue
        zs,xs=sl
        if zs.start==0 or xs.start==0 or zs.stop==land.shape[0] or xs.stop==land.shape[1]:
            continue
        area=int(sizes[label])*spacing**2
        diameter=2*math.sqrt(area/math.pi)
        rr,cc=np.nonzero(labels[sl]==label)
        xx=x0+(cc+xs.start)*spacing
        zz=z0+(rr+zs.start)*spacing
        cx,cz=float(xx.mean()),float(zz.mean())
        i=int(np.lexsort((zz,xx,(xx-cx)**2+(zz-cz)**2))[0])
        center=(int(xx[i]),int(zz[i]))
        if not(low<=center[0]<=high and low<=center[1]<=high):
            continue
        result.append({"center":list(center),"predicted_area_blocks2":area,
                       "equivalent_diameter":diameter,"evidence":"predicted",
                       "isolation_verified":False,"size_score":band(diameter,300,700)})
    return sorted(result,key=lambda p:(-p["size_score"],p["center"]))


def components(land,x0,z0,spacing,center_bounds):
    """Keep finite-edge uncertainty rather than declaring ocean beyond a raster."""
    labels,count=ndimage.label(land,np.ones((3,3),int))
    sizes=np.bincount(labels.ravel()); result=[]
    for ident,sl in enumerate(ndimage.find_objects(labels),1):
        if sl is None: continue
        zs,xs=sl; rr,cc=np.nonzero(labels[sl]==ident)
        xx=x0+(cc+xs.start)*spacing; zz=z0+(rr+zs.start)*spacing
        centroid=(float(xx.mean()),float(zz.mean()))
        eligible=(xx%8==0)&(zz%8==0)&(xx>=center_bounds[0])&(xx<=center_bounds[1])&(zz>=center_bounds[0])&(zz<=center_bounds[1])
        if not eligible.any(): continue
        xx=xx[eligible];zz=zz[eligible]
        i=np.lexsort((zz,xx,(xx-centroid[0])**2+(zz-centroid[1])**2))[0]
        diameter=2*math.sqrt(sizes[ident]*spacing**2/math.pi)
        touches=zs.start==0 or xs.start==0 or zs.stop==land.shape[0] or xs.stop==land.shape[1]
        result.append({'label':ident,'center':[int(xx[i]),int(zz[i])],'centroid':list(centroid),
                       'area':int(sizes[ident])*spacing**2,'equivalent_diameter':diameter,
                       'bounds':[x0+xs.start*spacing,z0+zs.start*spacing,x0+(xs.stop-1)*spacing,z0+(zs.stop-1)*spacing],
                       'touches_raster_boundary':touches,'isolation':'unknown' if touches else 'predicted_separated',
                       'center_displacement':math.dist((int(xx[i]),int(zz[i])),centroid)})
    return labels,result

def largest_gap(mask):
    a=np.asarray(mask,dtype=bool)
    if a.all(): return 360.0
    if not a.any(): return 0.0
    doubled=np.concatenate((a,a)); best=run=0
    for v in doubled:
        run=run+1 if v else 0;best=max(best,run)
    return min(len(a),best)*360/len(a)

def angular_metrics(height,island,center,x0,z0,step,cfg,unknown=None,high_mask=None):
    """Outermost component exit handles ponds/crescents; gaps measured from shore."""
    if unknown is None: unknown=np.zeros_like(island)
    n=cfg['water']['angular_samples']; reach=cfg['overworld']['surrounding_range_from_shore_blocks']
    gaps=[]; high_heights=[]; high_distances=[]; enclosed=[]; high=[]; unresolved=[]
    max_distance=math.hypot(*height.shape)*step
    for angle in np.arange(n)*2*math.pi/n:
        d=np.arange(0,max_distance+step,step/2)
        xx=np.rint((center[0]+np.cos(angle)*d-x0)/step).astype(int)
        zz=np.rint((center[1]+np.sin(angle)*d-z0)/step).astype(int)
        valid=(xx>=0)&(zz>=0)&(xx<height.shape[1])&(zz<height.shape[0])
        xx,zz,d=xx[valid],zz[valid],d[valid]
        indices=np.flatnonzero(island[zz,xx])
        if not len(indices): enclosed.append(False);high.append(False);unresolved.append(True);continue
        shore=indices[-1]; dist=d-d[shore]
        zone=(np.arange(len(d))>shore)&(dist<=reach)
        if not zone.any(): enclosed.append(False);high.append(False);unresolved.append(True);continue
        ext=zone&(height[zz,xx]>=63)&~island[zz,xx]&~unknown[zz,xx]
        unknown_ray=bool(unknown[zz[zone],xx[zone]].any() or dist[-1]<reach)
        unresolved.append(unknown_ray);enclosed.append(bool(ext.any()))
        if ext.any(): gaps.append(float(dist[np.flatnonzero(ext)[0]]))
        mountains=ext&(height[zz,xx]>=63+cfg['mountains']['minimum_height_above_water_blocks'])
        if high_mask is not None: mountains &= high_mask[zz,xx]
        high.append(bool(mountains.any()))
        if mountains.any():
            at=np.flatnonzero(mountains)[0]; high_heights.append(int(height[zz[at],xx[at]])-63);high_distances.append(float(dist[at]))
    ef=sum(enclosed)/n;hf=sum(high)/n;uf=sum(unresolved)/n
    return {'rays':n,'unknown_rays':sum(unresolved),'enclosure_fraction_bounds':[ef,min(1,ef+uf)],
            'high_terrain_fraction_bounds':[hf,min(1,hf+uf)],
            'median_gap':float(np.median(gaps)) if gaps else None,
            'gap_percentiles':np.percentile(gaps,[10,50,90]).tolist() if gaps else None,
            'preferred_gap_fraction':sum(cfg['water']['preferred_gap_blocks'][0]<=v<=cfg['water']['preferred_gap_blocks'][1] for v in gaps)/n,
            'largest_water_opening_degrees':largest_gap(~np.array(enclosed)&~np.array(unresolved)),
            'largest_mountain_gap_degrees':largest_gap(~np.array(high)&~np.array(unresolved)),
            'median_high_relative_height':float(np.median(high_heights)) if high_heights else None,
            'median_mountain_distance_from_shore':float(np.median(high_distances)) if high_distances else None,
            'enclosure_preference_met':ef>=cfg['water']['preferred_enclosure_fraction']}
