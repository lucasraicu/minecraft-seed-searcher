"""Versioned player-facing definitions. A product promise is not an observation."""
from copy import deepcopy

REVISION = 'catalog-products-v1'
SCOPE = dict(scope_type='origin_euclidean_circle', anchor=[0,0], radius=2000)
EVIDENCE = 'Research predictions of structure starts, not generated structures or verified world spawn.'
PILLARS = [
    ('realm','Realm/Server Seeds','Shared survival worlds with declared qualification evidence.'),
    ('presets','Presets','Sixteen fixed play-style starts.'),
    ('personalized','Personalized Selection','Choose supported requirements and a settlement or Origin anchor.'),
    ('rare','Rare Seeds','Unusual worlds and population-scoped research records.'),
]
# Stable ID, name, theme, exact player predicate, distance, additional dependencies.
PRESETS = [
 ('six_pack','The Six-Pack','Jackpot & God Starts','Village, ruined portal, desert pyramid, outpost, trial chamber and ancient city within 300 blocks of world spawn.',300,[]),
 ('loot_run','The Loot Run','Jackpot & God Starts','Ancient city and trial chamber within 200 blocks of world spawn.',200,[]),
 ('mansion_village','Mansion Village','Jackpot & God Starts','Woodland mansion and plains village within 300 blocks of world spawn.',300,['village_subtype']),
 ('triple_start','The Triple Start','Speedrun & Fast Starts','Village, shipwreck and ruined portal within 200 blocks of world spawn.',200,[]),
 ('temple_rush','Temple Rush','Speedrun & Fast Starts','Desert pyramid and ruined portal within 150 blocks of world spawn.',150,[]),
 ('nether_duo','Nether Duo','Speedrun & Fast Starts','Nether fortress and bastion within 200 blocks of the starter portal.',200,['nether_observations','starter_portal_reference']),
 ('cherry_haven','Cherry Blossom Haven',"Builders' & Biomes",'Cherry grove and plains village within 150 blocks of world spawn.',150,['village_subtype']),
 ('alpine_meadow','Alpine Meadow',"Builders' & Biomes",'Mountain meadow and cherry grove within 300 blocks of world spawn; flat high-altitude plateau and vistas require terrain evidence.',300,['meadow_subtype','terrain_surface']),
 ('bamboo_temple','Bamboo Temple',"Builders' & Biomes",'Bamboo jungle and jungle pyramid within 300 blocks of world spawn.',300,[]),
 ('frozen_frontier','The Frozen Frontier',"Builders' & Biomes",'Snowy village, igloo, ice spikes and ruined portal within 300 blocks of world spawn.',300,['village_subtype','ice_spikes_subtype','igloo_basement_evidence']),
 ('badlands_desert','Badlands & Desert',"Builders' & Biomes",'Badlands, desert pyramid, village and trail ruins within 300 blocks of world spawn.',300,[]),
 ('shipwreck_bay','Shipwreck Bay & Village','Ocean & Aquatic','Coastal village and at least two shipwrecks in a bay within 200 blocks of world spawn.',200,['coastline_and_bay']),
 ('mushroom_haven','Mushroom Haven','Ocean & Aquatic','Mushroom fields touching an ocean monument within 300 blocks of world spawn; safety requires separate evidence.',300,['biome_structure_contact','hostile_spawn_rules']),
 ('villagers_pillagers','Villagers & Pillagers','Combat & Outposts','Plains village and pillager outpost within 300 blocks of world spawn.',300,['village_subtype']),
 ('witch_next_door','Witch Next Door','Combat & Outposts','Plains village and swamp hut within 200 blocks of world spawn.',200,['village_subtype']),
 ('safe_nether','Safe Nether Outpost','Combat & Outposts','Warped forest and bastion within 200 blocks of the starter portal. Hostile-free or safe terrain is not established.',200,['nether_observations','starter_portal_reference','hostile_spawn_rules','terrain_surface']),
]
RECORDS = [
 ('megacity','The Megacity (Most Villages)','Maximum Structure Density','Most villages within 2,000 blocks; spawn reference must be integrated.',['estimated_spawn_layout']),
 ('trial_gauntlet','The Trial Gauntlet (Most Trial Chambers)','Maximum Structure Density','Most trial chambers; exact radius and reference point must be defined.',['record_scope_definition']),
 ('deep_dark_metropolis','The Deep Dark Metropolis (Most Ancient Cities)','Maximum Structure Density','Most ancient cities clustered in deep slate; exact cluster scope and terrain evidence required.',['record_scope_definition','underground_terrain']),
 ('outpost_siege','The Outpost Siege (Most Pillager Outposts)','Maximum Structure Density','Most outposts within a declared scope.',['record_scope_definition']),
 ('fortress_empire','The Nether Fortress Empire','Maximum Structure Density','Most fortresses within 500 blocks of the starter portal.',['nether_observations','starter_portal_reference']),
 ('bastion_fleet','The Bastion Fleet','Maximum Structure Density','Most clustered bastion remnants; exact cluster scope required.',['nether_observations','record_scope_definition']),
 ('ruined_kingdom','The Ruined Kingdom (Most Ruined Portals)','Maximum Structure Density','Most ruined portals within a declared scope.',['record_scope_definition']),
 ('desert_dynasty','The Desert Dynasty (Most Desert Pyramids)','Maximum Structure Density','Most desert pyramids within a declared scope.',['record_scope_definition']),
 ('sunken_armada','The Sunken Armada (Most Shipwrecks)','Maximum Structure Density','Most shipwrecks along coastlines and ocean floors within a declared scope.',['record_scope_definition','terrain_surface']),
 ('mansion_spawn','The 0m Woodland Mansion Spawn','Freak Proximity Spawns','Woodland mansion touching or within 50 blocks of world spawn.',['estimated_spawn_layout','structure_footprints']),
 ('city_spawn','The 0m Ancient City Spawn','Freak Proximity Spawns','World spawn directly above an ancient city at Y=-51.',['estimated_spawn_layout','structure_y_and_footprints']),
 ('monument_spawn','The 0m Ocean Monument Spawn','Freak Proximity Spawns','World spawn on a sandbar facing an ocean monument within 50 blocks.',['estimated_spawn_layout','terrain_surface','structure_footprints']),
 ('quad_overlap','The Quadruple Structure Overlap','Freak Proximity Spawns','Four structures physically colliding or within 100 blocks of each other at spawn.',['estimated_spawn_layout','structure_footprints','cluster_predicate']),
 ('direct_drop','The Direct-Drop Nether Portal','Freak Proximity Spawns','A portal at Overworld (0,0) leads inside a fortress corridor or bastion treasure room.',['portal_link_simulation','nether_structure_pieces']),
 ('quad_huts','The Quad Witch Hut','Technical Redstone & Farms','Four swamp huts within one player AFK 128-block sphere; Bedrock loading and farm suitability separately validated.',['structure_y_and_footprints','bedrock_farm_rules']),
 ('multiple_monuments','The Triple / Double Ocean Monument Farm','Technical Redstone & Farms','Two or three ocean monuments within a declared loading radius; farm suitability separately validated.',['record_scope_definition','bedrock_farm_rules','structure_footprints']),
 ('fortress_bastion','The Fortress + Bastion Overlap','Technical Redstone & Farms','Fortress and bastion within 64 blocks; overlap and farm suitability need piece/loading evidence.',['nether_structure_pieces','bedrock_farm_rules']),
 ('triple_mineshaft','The Intersecting Triple Mineshaft','Technical Redstone & Farms','Three mineshafts physically intersecting in a cave-spider spawner layout.',['structure_y_and_footprints','spawner_locations']),
 ('all_biome','The All-Biome 1,000m Sprint','Biome Rarity & Exploration','At least 14 biome families within a 1,000-block walking radius of spawn.',['estimated_spawn_layout','expanded_biome_registry','walkable_terrain']),
 ('mega_cherry','The Mega Cherry Grove','Biome Rarity & Exploration','Largest contiguous cherry grove spanning over 1,200 blocks.',['biome_contiguity','terrain_surface']),
 ('badlands_spine','The Badlands Continental Spine','Biome Rarity & Exploration','Unbroken badlands continent across multiple kilometers with exposed terracotta and gold mineshafts.',['biome_contiguity','terrain_surface','record_scope_definition']),
 ('deep_dark_void','The Endless Deep Dark Void','Biome Rarity & Exploration','Continuous deep-dark cave trench connecting multiple ancient cities.',['underground_terrain','biome_contiguity','cluster_predicate']),
]
RESEARCH_FEATURES = ('village','trial_chamber','ruined_portal','desert_pyramid','shipwreck')


def product_registry():
    products=[]
    def gated(pid,pillar,kind,label,category,criteria,dependencies,scope):
        products.append(dict(id=pid,pillar_id=pillar,kind=kind,label=label,category=category,
            criteria_summary=criteria,availability_status='gated',missing_dependencies=dependencies,
            evidence_needed=['Compatible public observation and exact predicate evaluator.']+
                            [d.replace('_',' ').capitalize()+'.' for d in dependencies],
            scope=scope,predicates=[dict(expression=criteria,evaluator=None)],
            ranking=dict(status='unavailable_until_predicate_defined',ties=['world_id_ascending'])))
    gated('realm.qualified','realm','realm','Realm/Server Qualification','Shared Survival',
          'Qualify public observations against an exact versioned Realm blueprint, all required floors and declared verification evidence.',
          ['realm_blueprint_binding','realm_public_qualification','scoped_game_verification'],
          dict(scope_type='realm_blueprint_defined',border_sides=[2048,4096,8192]))
    for pid,label,category,criteria,radius,deps in PRESETS:
        portal='starter_portal_reference' in deps
        gated('preset.'+pid,'presets','preset',label,category,criteria,
              (['exact_preset_evaluator','scoped_game_verification']+([] if portal else ['estimated_spawn_layout'])+deps),
              dict(scope_type='closed_euclidean_circle',radius=radius,
                   anchor='starter_portal' if portal else 'world_spawn',dimension='nether' if portal else 'overworld'))
    for pid,label,category,criteria,deps in RECORDS:
        gated('record.'+pid,'rare','record',label,category,criteria,
              ['exact_record_evaluator','scoped_game_verification']+deps,
              dict(scope_type='record_definition',definition_id=pid))
    for feature in RESEARCH_FEATURES:
        products.append(dict(id=f'research.origin.{feature}.r2000',pillar_id='rare',kind='research',
            label=feature.replace('_',' ').title()+' density preview',category='Available Research Previews',
            criteria_summary='Count predicted starts within 2,000 blocks of Origin (0,0), not spawn.',
            availability_status='research',missing_dependencies=[],evidence_needed=[EVIDENCE],scope=deepcopy(SCOPE),
            predicates=[dict(feature='structure.'+feature,method='predictor_viable_starts_v1',distance_squared_lte=4000000)],
            ranking=dict(order='count_descending',ties=['world_id_ascending'],limit=100)))
    return dict(ok=True,revision=REVISION,pillars=[dict(id=i,label=l,description=d) for i,l,d in PILLARS],
                products=products,evidence_label=EVIDENCE)


def launch_definitions():
    """One source of exact predicates for evaluation, retention and presentation."""
    import json
    from .registry import CONTRACT_ROOT
    return json.loads((CONTRACT_ROOT.parent / 'v2' / 'products.json').read_text())


def product_registry_v2():
    """Revised products replace earlier promises; legacy research stays separate."""
    result=product_registry();definitions=launch_definitions()
    # Terrain-heavy proposals remain historical v1 definitions, not launch cards.
    # Keep the frozen evaluator/retention contract unchanged for existing snapshots.
    result['products']=[]
    rows=[('realm','realm',p) for p in [definitions['realm'],*definitions.get('realm_sizes',[])]]
    rows += [('presets','preset',p) for p in definitions['presets']]
    rows += [('rare','record',p) for p in definitions['records']]
    for pillar,kind,p in rows:
        dimension=p.get('dimension','overworld')
        reference='the Nether coordinate projected from estimated world spawn (floor X/8, Z/8)' if dimension=='nether' else 'estimated world spawn'
        radius=p.get('radius');scope=dict(dimension=dimension,anchor='projected_world_spawn' if dimension=='nether' else 'world_spawn_estimated')
        if radius is not None:scope.update(radius=radius,scope_type='closed_horizontal_circle')
        category='Structure Density';criteria=''
        if kind=='realm':
            side=p['overworld_core']
            category='Shared Survival';scope=dict(dimension='overworld',anchor='realm_qualified_center',border_sides=[side])
            criteria=f'Qualify the versioned {side} Overworld / 1024 Nether Realm blueprint at one refined center. Score out of 1250 points (845 Overworld, 265 luxury biomes, 140 Nether). '
            if side!=2048:criteria+='Frozen size-specific count floors and bonus tiers; bounded center search. Fixed 1024 Nether square. Calibration controls validate rules, not seed-population prevalence.'
        elif kind=='preset':
            rename={'meadow_cherry':'alpine_meadow','village_two_shipwrecks':'shipwreck_bay','mushroom_monument':'mushroom_haven','warped_bastion':'safe_nether'}
            category=next((old[2] for old in PRESETS if old[0]==rename.get(p['id'].split('.')[-1],p['id'].split('.')[-1])),'Play Styles')
            features=[str(n)+' '+fid.removeprefix('structure.').replace('_',' ')+' predicted start(s)' for fid,n in p['structures'].items()]
            features += [family.replace('_',' ')+' biome witness' for family in p['biomes']]
            criteria=', '.join(features)+f' within {radius} {dimension} blocks of {reference}. All conditions share that reference.'
        elif p['kind']=='density':
            criteria=f'Most distinct predicted starts within {radius} {dimension} blocks of {reference}; complete scoped predictor inventory required.'
        elif p['kind']=='proximity':
            category='Start Proximity';criteria=f'Closest predicted start within {radius} {dimension} blocks of {reference}; distance is horizontal to its start coordinate.'
        elif p['kind']=='biome_sampler':
            category='Biome Exploration';criteria=f'Fourteen declared biome families witnessed within {radius} horizontal blocks of {reference}, using declared surface/cave heights. No walking-route or absence promise.'
        else:
            category='Structure Clusters'
            rules={'four_types':'Four distinct structure types, every pair at most 100 blocks apart',
                   'four_huts':'Four swamp-hut starts inside one minimum enclosing circle of radius 128',
                   'monument_cluster':'Two or three monument starts inside one minimum enclosing circle of radius 128',
                   'nether_pair':'A fortress and bastion start at most 64 Nether blocks apart'}
            criteria=rules[p['kind']]+f', all within {radius} {dimension} blocks of {reference}. No physical overlap or farm-suitability claim.'
        calibrated=kind!='realm' or p['overworld_core']==2048
        if not calibrated:
            import json
            from .registry import CONTRACT_ROOT
            policy=json.loads((CONTRACT_ROOT.parent/'v2'/'realm_scoring.json').read_text())
            from .realm_evaluation import load_calibration
            calibrated=policy['sizes'][str(p['overworld_core'])]['policy'] is not None and load_calibration() is not None
        result['products'].append(dict(id=p['id'],pillar_id=pillar,kind=kind,label=p['label'],category=category,
            criteria_summary=criteria,availability_status='predicted' if calibrated else 'gated',
            missing_dependencies=[] if calibrated else ['held_out_size_calibration'],
            evidence_needed=['Compatible source-bound predictor observations.'],scope=scope,
            predicates=[deepcopy(p)],ranking=dict(capacity=p['capacity'],ties=['world_id_ascending'])))
    result['revision']=definitions['revision']
    result['evidence_label']='Predicted starts and height-specific biome witnesses; scoped evidence accompanies each result.'
    return result
