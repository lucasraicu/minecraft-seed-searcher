"""Finite density rasters, adaptive sea-level columns, and coast connectivity."""
import numpy as np
from scipy import ndimage
from .geometry import components

LIMITS=['Raw density omits caves, aquifers, decoration and actual chunk interpolation.',
        'Sea-level uncertainty includes the observed five-block predictor height error.',
        'One-block coast samples remain density predictions, not exact liquid blocks.',
        'Discovery/refinement budgets can miss islands; deferred components are reported.']

def sample_points(backend,points,vertical_step=8):
    points=np.asarray(points,dtype=np.int32)
    hs=[];bs=[]
    for i in range(0,len(points),100_000):
        h,b=backend.heights(points[i:i+100_000],vertical_step);hs.append(h);bs.append(b)
    if not hs:return np.array([],dtype=np.int32),np.array([],dtype=np.int32)
    return np.concatenate(hs),np.concatenate(bs)

def raster(backend,bounds,step,adaptive=True):
    x0,z0,x1,z1=bounds
    xa=np.arange(x0,x1+1,step,dtype=np.int32);za=np.arange(z0,z1+1,step,dtype=np.int32)
    xx,zz=np.meshgrid(xa,za);pts=np.column_stack((xx.ravel(),zz.ravel()))
    h,b=sample_points(backend,pts)
    more=0
    if adaptive:
        near=np.abs(h-63)<=5;more=int(near.sum())
        if more:h[near],b[near]=sample_points(backend,pts[near],1)
    shape=(len(za),len(xa))
    return {'height':h.reshape(shape),'biomes':b.reshape(shape),'bounds':[x0,z0,int(xa[-1]),int(za[-1])],
            'step':step,'points':len(pts),'sea_level_stride1_points':more}

def coast_component(backend,discovered,cfg,analysis_bounds):
    step=cfg['search']['shoreline_spacing_blocks']; pad=64
    a=discovered['bounds'];cap=cfg['search']['maximum_refinement_patch_side_blocks']
    bounds=[max(analysis_bounds[0],(a[0]-pad)//step*step),max(analysis_bounds[1],(a[1]-pad)//step*step),
            min(analysis_bounds[2],-(-(a[2]+pad)//step)*step),min(analysis_bounds[3],-(-(a[3]+pad)//step)*step)]
    if max(bounds[2]-bounds[0],bounds[3]-bounds[1])>cap:
        return None,{'reason':'refinement_patch_budget','center':discovered['center'],'isolation':'unknown'}
    r=raster(backend,bounds,step)
    land=r['height']>=63
    # Sample every integer column in a coast band. Interior replication is an
    # explicit approximation; all transition cells are overwritten by stride-one
    # density columns, so narrow connections at sampled coasts are not skipped.
    transition=ndimage.binary_dilation(land,iterations=2)^ndimage.binary_erosion(land,iterations=2,border_value=0)
    highland=np.repeat(np.repeat(land,step,axis=0),step,axis=1)[:(land.shape[0]-1)*step+1,:(land.shape[1]-1)*step+1]
    band=np.repeat(np.repeat(transition,step,axis=0),step,axis=1)[:highland.shape[0],:highland.shape[1]]
    rr,cc=np.nonzero(band)
    pts=np.column_stack((bounds[0]+cc,bounds[1]+rr))
    h=sample_land(backend,pts)
    highland[rr,cc]=h
    sampled=band.copy(); extra=0
    # Follow newly revealed narrow land connections through initially coarse
    # water cells until the coast closes or reaches the finite patch edge.
    while True:
        frontier=ndimage.binary_dilation(highland,iterations=step)&~ndimage.binary_erosion(highland,iterations=step,border_value=0)&~sampled
        fr,fc=np.nonzero(frontier)
        if not len(fr):break
        fh=sample_land(backend,np.column_stack((bounds[0]+fc,bounds[1]+fr)))
        before=highland[fr,fc].copy();highland[fr,fc]=fh;sampled[fr,fc]=True;extra+=len(fr)
        if np.array_equal(before,highland[fr,fc]):break
    labels,cs=components(highland,bounds[0],bounds[1],1,cfg['search']['center_axis_bounds_blocks'])
    # The discovery anchor may become water. Use nearest overlapping component
    # and keep anchor displacement visible, rather than inventing land at center.
    anchor=discovered['center'];candidates=[]
    for c in cs:
        if c['touches_raster_boundary']:continue
        if c['bounds'][0]<=anchor[0]+64 and c['bounds'][2]>=anchor[0]-64 and c['bounds'][1]<=anchor[1]+64 and c['bounds'][3]>=anchor[1]-64:
            candidates.append(c)
    if not candidates:
        return None,{'reason':'density_connected_or_no_closed_component','center':anchor,'isolation':'unknown',
                     'density_points':r['points']+len(pts)+extra+r['sea_level_stride1_points']}
    c=min(candidates,key=lambda c:(np.linalg.norm(np.array(c['center'])-anchor),-c['area'],c['center']))
    c['coast_one_block_columns']=len(pts)+extra;c['coarse_anchor']=anchor
    selected=labels==c['label']
    c['sea_level_uncertain_coast_samples']=int(np.count_nonzero(np.abs(r['height']-63)<=5))
    c['isolation_verified']=False
    c['evidence']='predicted_density_with_one_block_coast_sampling'
    return {'component':c,'mask':selected,'height':r['height'],'biomes':r['biomes'],
            'bounds':bounds,'step':step,'points':r['points']+len(pts)+extra+r['sea_level_stride1_points']},None


def island_mask_on_raster(coast,terrain):
    x0,z0=terrain['bounds'][:2];step=terrain['step']
    xx,zz=np.meshgrid(np.arange(terrain['height'].shape[1])*step+x0,np.arange(terrain['height'].shape[0])*step+z0)
    cc=xx-coast['bounds'][0];rr=zz-coast['bounds'][1]
    valid=(cc>=0)&(rr>=0)&(cc<coast['mask'].shape[1])&(rr<coast['mask'].shape[0])
    mask=np.zeros_like(valid);mask[valid]=coast['mask'][rr[valid],cc[valid]]
    return mask


def sample_land(backend,points):
    points=np.asarray(points,dtype=np.int32);out=[]
    for i in range(0,len(points),100_000):
        batch=points[i:i+100_000]
        out.append(backend.land(batch) if hasattr(backend,'land') else backend.heights(batch,1)[0]>=63)
    return np.concatenate(out) if out else np.array([],dtype=bool)


def preliminary_component(backend,discovered,cfg,analysis_bounds):
    """Cheap 16-block density topology before one-block coast work."""
    step=cfg['search']['refinement_spacing_blocks'];pad=128
    a=discovered['bounds']
    bounds=[max(analysis_bounds[0],(a[0]-pad)//step*step),max(analysis_bounds[1],(a[1]-pad)//step*step),
            min(analysis_bounds[2],-(-(a[2]+pad)//step)*step),min(analysis_bounds[3],-(-(a[3]+pad)//step)*step)]
    if max(bounds[2]-bounds[0],bounds[3]-bounds[1])>cfg['search']['maximum_refinement_patch_side_blocks']:
        return None,{'reason':'preliminary_patch_budget','center':discovered['center'],'isolation':'unknown'},0
    r=raster(backend,bounds,step)
    _,cs=components(r['height']>=63,*bounds[:2],step,cfg['search']['center_axis_bounds_blocks'])
    # Retain components intersecting the original discovery box; nearby unrelated
    # land is not substituted for the intended island.
    cs=[c for c in cs if not(c['bounds'][2]<a[0] or c['bounds'][0]>a[2] or c['bounds'][3]<a[1] or c['bounds'][1]>a[3])]
    closed=[c for c in cs if not c['touches_raster_boundary']]
    points=r['points']+r['sea_level_stride1_points']
    if not closed:
        return None,{'reason':'preliminary_density_connected_or_no_closed_land','center':discovered['center'],'isolation':'unknown'},points
    c=min(closed,key=lambda c:(np.linalg.norm(np.array(c['center'])-discovered['center']),-c['area'],c['center']))
    c['discovery_anchor']=discovered['center']
    return c,None,points
