from __future__ import annotations
import json
import math
import os
import platform
import resource
import statistics
import time
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import get_context
from pathlib import Path

import numpy as np
from . import BACKEND_COMMIT, TARGET_VERSION
from .backend import Backend, STRUCTURES, biome_name, model_metadata
from .config import discovery_grid, load_config
from .geometry import island_components
from .seeds import seed_from_index

def metadata(config_hash):
    return {"target_game_version":TARGET_VERSION,"backend_commit":BACKEND_COMMIT,
            "backend":model_metadata(),"config_sha256":config_hash,
            "review_policy":"chunkbase_matching_version_terrain",
            "version_mapping":"Bedrock 26.52 -> MC_26_50 (bounded predictor comparisons, not full game emulation)",
            "chunkbase_checked":False,"actual_minecraft_evidence":"separate_optional_observations",
            "terrain_accuracy":"raw_density_estimate; historical Chunkbase MAE 1, max 5 blocks on 135 columns",
            "platform":platform.platform(),"cpu_logical_count":os.cpu_count(),
            "python":platform.python_version(),"large_search_enabled":False}

def save_json(path,value):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,allow_nan=False)+"\n")

def seed_list(count):
    result=[0,1,12345]
    for index in range(1,100):
        seed=seed_from_index(index)
        if seed not in result:
            result.append(seed)
        if len(result)>=count:
            break
    return result[:count]

def points_grid(x0,z0,side,step):
    # Inclusive border samples; geometric footprint remains `side` square.
    axis=np.arange(0,side+1,step,dtype=np.int32)
    xx,zz=np.meshgrid(axis+x0,axis+z0)
    return np.column_stack((xx.ravel(),zz.ravel()))

def _coarse_worker(args):
    seed,grid=args
    start=time.perf_counter()
    with Backend(seed) as b:
        b.grid(*grid)
    return {"seed":str(seed),"seconds":time.perf_counter()-start}

def benchmark(cfg,config_hash,output,count=3,worker_counts=(4,8,12)):
    maximum=min(10,cfg["search"]["preflight_maximum_seeds"])
    if not 1<=count<=maximum:
        raise ValueError(f"Preflight stage benchmark is limited to {maximum} seeds")
    if any(not 1<=w<=12 for w in worker_counts):
        raise ValueError("Benchmark worker counts must be in 1–12")
    grid=discovery_grid(cfg)
    side=cfg["deployment"]["overworld_side_blocks"]
    half=side//2
    bounds=(grid[0],grid[1],grid[0]+grid[2]*grid[4],grid[1]+grid[3]*grid[4])
    low,high=cfg["search"]["center_axis_bounds_blocks"]
    nh=cfg["deployment"]["nether_side_blocks"]//2
    nb=(math.floor(low/8)-nh,math.floor(low/8)-nh,math.ceil(high/8)+nh,math.ceil(high/8)+nh)
    refinement=points_grid(-half,-half,side,cfg["search"]["refinement_spacing_blocks"])
    shoreline=points_grid(-128,-128,256,4)
    rows=[]
    for seed in seed_list(count):
        print(f"Benchmark seed {seed}: measuring fixed diagnostic workloads...",flush=True)
        start=time.perf_counter()
        b=Backend(seed)
        row={"seed":str(seed),"generator_setup_seconds":time.perf_counter()-start}
        with b:
            start=time.perf_counter(); coarse=b.grid(*grid)
            row["coarse_biome_climate_seconds"]=time.perf_counter()-start
            row["coarse_points"]=int(coarse["biomes"].size)
            start=time.perf_counter()
            candidates=island_components(coarse["approx_height"]>=63,grid[0],grid[1],grid[4],[low,high])
            row["coarse_component_seconds"]=time.perf_counter()-start
            row["diagnostic_component_count"]=len(candidates)
            # These full-envelope adapters are measured independently of landscape filtering.
            row["structure_seconds"]={}; row["predicted_structure_counts"]={}
            for name in STRUCTURES:
                start=time.perf_counter()
                positions=b.structures(name,nb if name in ("fortress","bastion") else bounds)
                row["structure_seconds"][name]=time.perf_counter()-start
                row["predicted_structure_counts"][name]=len(positions)
            print(f"  discovery {row['coarse_biome_climate_seconds']:.3f}s; checking density at {len(refinement):,} points",flush=True)
            start=time.perf_counter(); heights,_=b.heights(refinement,8)
            row["one_full_border_density_refinement_seconds"]=time.perf_counter()-start
            row["refinement_points"]=len(refinement)
            row["density_height_range"]=[int(heights.min()),int(heights.max())]
            start=time.perf_counter(); b.heights(shoreline,8)
            row["one_256_block_shoreline_patch_seconds"]=time.perf_counter()-start
            row["shoreline_patch_points"]=len(shoreline)
        rows.append(row)
        print(f"  one full-border density refinement {row['one_full_border_density_refinement_seconds']:.3f}s; structure checks {sum(row['structure_seconds'].values()):.3f}s",flush=True)
    parallel=[]
    jobs=[(s,grid) for s in seed_list(maximum)]
    for workers in worker_counts:
        print(f"Coarse-only process benchmark: {len(jobs)} seeds, {workers} workers (includes startup)",flush=True)
        start=time.perf_counter()
        with ProcessPoolExecutor(max_workers=workers,mp_context=get_context("spawn")) as pool:
            samples=list(pool.map(_coarse_worker,jobs))
        wall=time.perf_counter()-start
        parallel.append({"workers":workers,"seed_count":len(jobs),"wall_seconds_including_startup":wall,
                         "effective_seconds_per_seed":wall/len(jobs),"worker_samples":samples})
    scalar_keys=[k for k,v in rows[0].items() if k.endswith("seconds") and isinstance(v,float)]
    summary={key:{"median":statistics.median(r[key] for r in rows),"minimum":min(r[key] for r in rows),
                  "maximum":max(r[key] for r in rows)} for key in scalar_keys}
    structure_times=[sum(r["structure_seconds"].values()) for r in rows]
    summary["all_structure_adapter_seconds"]={"median":statistics.median(structure_times),
                                               "minimum":min(structure_times),"maximum":max(structure_times)}
    rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    result={"metadata":metadata(config_hash),"workload":"bounded_stage_microbenchmarks_not_complete_search",
            "profile_seed_count":count,"unique_seeds_including_parallel_tests":len(jobs),
            "coarse_grid":{"x0":grid[0],"z0":grid[1],"nx":grid[2],"nz":grid[3],"spacing":grid[4]},
            "overworld_structure_bounds":list(bounds),"nether_structure_bounds":list(nb),
            "surface_estimator":"raw_terrain_density_without_caves_aquifers_or_chunk_interpolation",
            "density_vertical_step":8,"stage_seconds":summary,"rows":rows,"coarse_only_parallel":parallel,
            "main_process_peak_rss_mb":rss/(1024*1024 if platform.system()=="Darwin" else 1024),
            "full_search_seconds_per_seed":None,
            "notes":["Refinement is a fixed 3008-square workload, not automatic multi-center refinement.",
                     "Actual total cost depends on survivors and number/size of refined candidate regions.",
                     "Parallel tests measure only coarse sampling and include process import/startup overhead.",
                     "Predicted counts do not certify real-world structures or target rarity."]}
    save_json(Path(output)/"benchmark.json",result)
    lines=["# Preflight performance measurements","","Fixed diagnostic workloads on this Mac; **not a completed search benchmark**.","",
           "| Stage | Median seconds | Observed range |","|---|---:|---:|"]
    for key,stats in summary.items():
        lines.append(f"| {key.replace('_',' ')} | {stats['median']:.3f} | {stats['minimum']:.3f}–{stats['maximum']:.3f} |")
    lines.extend(["","Coarse-only parallel tests (10 seeds at most; startup included):","",
                  "| Workers | Batch seconds | Effective seconds/seed |","|---|---:|---:|"])
    for p in parallel:
        lines.append(f"| {p['workers']} | {p['wall_seconds_including_startup']:.3f} | {p['effective_seconds_per_seed']:.3f} |")
    lines.extend(["","Full search time per seed remains unmeasured. More candidate islands mean more refinement work.",
                  "These are local prediction timings; phone inspection is separate.","",
                  f"Backend: `{BACKEND_COMMIT}`; proposed 26.50 model for 26.52 remains unverified."])
    (Path(output)/"BENCHMARK.md").write_text("\n".join(lines)+"\n")
    return result

def probe(cfg,config_hash,seed,output,center=None):
    from .wood import wood_masks
    from .reports import render_probe
    out=Path(output);out.mkdir(parents=True,exist_ok=True)
    grid=discovery_grid(cfg)
    with Backend(seed) as b:
        print(f"Probe seed {seed}: generating discovery diagnostics",flush=True)
        coarse=b.grid(*grid)
        candidates=island_components(coarse["approx_height"]>=63,grid[0],grid[1],grid[4],cfg["search"]["center_axis_bounds_blocks"])
        if center is None:
            center=tuple(candidates[0]["center"]) if candidates else (0,0)
        low,high=cfg["search"]["center_axis_bounds_blocks"]
        if not all(low<=v<=high and v%8==0 for v in center):
            raise ValueError("Probe center must be on the eight-block grid inside the center envelope")
        side=cfg["deployment"]["overworld_side_blocks"];half=side//2
        step=cfg["search"]["refinement_spacing_blocks"]
        points=points_grid(center[0]-half,center[1]-half,side,step)
        print(f"  refining {len(points):,} density columns around {center}",flush=True)
        start=time.perf_counter();h,ids=b.heights(points,8)
        elapsed=time.perf_counter()-start
        n=side//step+1
        height=h.reshape(n,n);biomes=ids.reshape(n,n)
        woodland,sparse=wood_masks(biomes)
        structures={}
        nh=cfg["deployment"]["nether_side_blocks"]//2
        nc=(center[0]//8,center[1]//8)
        for name in STRUCTURES:
            bounds=(nc[0]-nh,nc[1]-nh,nc[0]+nh,nc[1]+nh) if name in ("fortress","bastion") else (center[0]-half,center[1]-half,center[0]+half,center[1]+half)
            structures[name]=[list(p) for p in b.structures(name,bounds)]
        # First compatibility observations are fixed, independently of which
        # predicted candidate was chosen for the map. They are not claims of fit.
        validation_points=np.array([[0,0],[256,256],[256,-256]],dtype=np.int32)
        vh,vi=b.heights(validation_points,1)
        points_data=[{"x":int(x),"z":int(z),"predicted_density_ground_y":int(y),
                      "predicted_surface_kind":"water" if y<63 else "land",
                      "predicted_surface_biome":biome_name(i),"actual_ground_y":None,
                      "actual_surface_kind":None,"actual_wooded":None}
                     for (x,z),y,i in zip(validation_points,vh,vi)]
    np.savez_compressed(out/"terrain.npz",height=height,biomes=biomes,points=points)
    report={"metadata":metadata(config_hash),"seed":str(seed),"center":list(center),"nether_center":list(nc),
            "island_isolation":"unverified","raw_density_refinement_seconds":elapsed,
            "approximation_limitations":["Caves, aquifers, decorations and actual chunk interpolation excluded.",
                                         "Vertical stride eight may miss thin overhangs.",
                                         "Woodland biome coverage is not actual canopy or log density."],
            "discovery_candidates":candidates,"structures":structures,"initial_phone_points":points_data,
            "surface_biome_inventory":{biome_name(i):int(np.count_nonzero(biomes==i)) for i in np.unique(biomes)}}
    save_json(out/"probe.json",report)
    observation={"schema_version":1,"game_version":TARGET_VERSION,"seed":str(seed),
                 "observation_source":"phone_actual_game","points":points_data,
                 "border_center":list(center),"default_generation_confirmed":None,
                 "landscape":{"actual_island_separated":None,"known_bridge_example":None,
                              "actual_surrounding_mountains":None,"actual_surrounding_forest_abundant":None},
                 "structures":[{"type":name,"dimension":"nether" if name in ("fortress","bastion") else "overworld",
                                "actual_x":None,"actual_y":None,"actual_z":None,
                                "actual_generated":None,"notes":""} for name in STRUCTURES],
                 "notes":"Fill actual observations only; leave unvisited facts null. border_center is diagnostic, not a verified island."}
    save_json(out/"phone_observations.template.json",observation)
    lines=["# Phone validation — first observations","",
           f"Create a disposable **default-generation Bedrock {TARGET_VERSION} world with seed `{seed}`**, cheats and Show Coordinates enabled.",
           "Use Spectator mode for inspection. These predictions have not been checked in game.","",
           "```text","/gamemode spectator","```","",
           "At each X/Z, report water versus land, natural ground Y if on land, and whether the surroundings are wooded.",
           "Ground Y is feet Y minus one when standing on the natural ground, excluding logs/leaves.","",
           "| Location | Command | Predicted ground / biome |","|---|---|---|"]
    for p in points_data:
        lines.append(f"| {p['x']}, {p['z']} | `/tp @s {p['x']} 320 {p['z']}` | {p['predicted_density_ground_y']} / {p['predicted_surface_biome']} |")
    lines.extend(["","After the first terrain observations, check these core structures from the indicated reference positions:","",
                  f"`/tp @s {center[0]} 320 {center[1]}`",
                  "```text","/locate structure minecraft:trial_chambers","/locate structure minecraft:stronghold",
                  "/locate structure minecraft:mineshaft","```","",
                  "For the Nether, use:","","```text",
                  f"/execute in nether run tp @s {nc[0]} 80 {nc[1]}",
                  "/locate structure minecraft:fortress","/locate structure minecraft:bastion_remnant","```","",
                  "Send the coordinates returned by each command, including structures outside the border. Do not assume they are inside.",
                  "The matching predicted starts are recorded in `probe.json`; compare nearby starts rather than assuming identical locate offsets.","",
                  "| Type | Nearest predicted start inside border (X, Z) | Distance from reference center |",
                  "|---|---|---:|"])
    for name in STRUCTURES:
        reference=nc if name in ("fortress","bastion") else center
        positions=structures[name]
        if positions:
            p=min(positions,key=lambda p:((p[0]-reference[0])**2+(p[1]-reference[1])**2,p))
            distance=math.hypot(p[0]-reference[0],p[1]-reference[1])
            lines.append(f"| {name} | {p[0]}, {p[1]} | {distance:.1f} |")
        else:
            lines.append(f"| {name} | None predicted in this square; actual presence unknown | — |")
    lines.extend(["","Fill `actual_x` and `actual_z` for a `/locate` result. Leave `actual_y` null if the command gives no usable Y.",
                  "Set `actual_generated` only after visiting: true when the structure is present; false for an inspected prediction that is absent. Leave unvisited entries null.",
                  "`compare` reports nearby placement/viable starts and offsets, but does not equate a locate coordinate with a start or certify a structure match.","",
                  "Island separation, an actual bridge negative example, surrounding mountains and forest abundance still need landscape inspection.",
                  "The map center is a diagnostic prediction, not a proposed final seed or a verified island.","",
                  "Sources: [locate syntax](https://learn.microsoft.com/en-us/minecraft/creator/commands/commands/locate?view=minecraft-bedrock-stable), "
                  "[dimension commands](https://learn.microsoft.com/en-us/minecraft/creator/commands/commands/execute?view=minecraft-bedrock-stable)."])
    (out/"PHONE_CHECKS.md").write_text("\n".join(lines)+"\n")
    render_probe(out/"terrain.png",height,biomes,woodland,sparse,points,seed,center)
    return report

def compare_observations(path,output,cfg=None,config_hash=None):
    from .observations import compare_structures, landscape_observations, optional_bool
    if cfg is None:
        cfg,config_hash=load_config()
    data=json.loads(Path(path).read_text())
    if not isinstance(data,dict):
        raise ValueError("Require an observation object")
    if data.get("game_version")!=TARGET_VERSION or data.get("observation_source")!="phone_actual_game":
        raise ValueError("Require target-version observations explicitly identified as actual phone game data")
    if data.get("schema_version",1)!=1:
        raise ValueError("Require observation schema_version 1")
    optional_bool(data.get("default_generation_confirmed"), "default_generation_confirmed")
    points=data.get("points",[])
    if not isinstance(points,list) or len(points)>1000:
        raise ValueError("Expected at most 1,000 terrain observation points")
    comparisons=[]
    with Backend(data["seed"]) as b:
        canonical_seed=str(b.seed)
        for p in points:
            x,z=p["x"],p["z"]
            h,ids=b.heights([[x,z]],1)
            actual=p.get("actual_ground_y")
            kind=p.get("actual_surface_kind")
            if actual is not None and (not isinstance(actual,int) or isinstance(actual,bool) or not -64<=actual<=319):
                raise ValueError("actual_ground_y must be an integer natural-block Y in -64..319")
            if kind not in (None,"land","water"):
                raise ValueError("actual_surface_kind must be land, water, or null")
            optional_bool(p.get("actual_wooded"),"actual_wooded")
            comparisons.append({"x":x,"z":z,"predicted_ground_y":int(h[0]),"actual_ground_y":actual,
                                "height_error":int(h[0])-actual if actual is not None else None,
                                "surface_kind_matches":(kind==("water" if h[0]<63 else "land")) if kind else None,
                                "actual_wooded":p.get("actual_wooded"),"predicted_biome":biome_name(ids[0]),
                                "actual_tree_description":p.get("actual_tree_description"),
                                "actual_tree_top_y":p.get("actual_tree_top_y"),
                                "measurement_method":p.get("measurement_method")})
        structures=compare_structures(b,data,cfg)
    landscape=landscape_observations(data)
    observed=sum(p["actual_ground_y"] is not None or p["surface_kind_matches"] is not None for p in comparisons)
    result={"metadata":metadata(config_hash),"seed":canonical_seed,"game_version":TARGET_VERSION,"points":comparisons,
            "border_center":data.get("border_center"),"structures":structures,"landscape_observations":landscape,
            "default_generation_confirmed":data.get("default_generation_confirmed"),
            "observed_structure_positions":sum(r["actual_position_xz"] is not None for r in structures),
            "visited_structure_positions":sum(r["actual_generated"] is not None for r in structures),
            "observed_woodland_points":sum(p["actual_wooded"] is not None for p in comparisons),
            "observation_notes":data.get("notes",""),
            "observed_points":observed,"compatibility":"pending_full_fixture_review",
            "large_search_enabled":False,"notes":"A small sample does not certify all terrain, biomes, or structures."}
    save_json(output,result)
    return result
