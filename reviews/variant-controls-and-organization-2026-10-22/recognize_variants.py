"""Independent physical signatures. Missing or shared signals never imply absence."""
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent

def normalized(name):
    if name in ('minecraft:snow','minecraft:snow_block'):return 'snow_block'
    if name in ('minecraft:red_bed','minecraft:bed'):return 'bed'
    if name.endswith('_carpet')or name=='minecraft:carpet':return 'carpet'
    if name in ('minecraft:oak_trapdoor','minecraft:trapdoor'):return 'trapdoor'
    if name in ('minecraft:lit_furnace','minecraft:furnace'):return 'furnace'
    return name

def turn(x,z,rotation,mirror):
    if mirror:x=-x
    for _ in range(rotation):x,z=-z,x
    return x,z

def match_template(blocks,template,include,anchor_name):
    pattern=[b for b in template['blocks']if include(b)]
    anchor=next(b for b in pattern if normalized(b['name'])==normalized(anchor_name))
    targets=[p for p,n in blocks.items()if normalized(n)==normalized(anchor_name)]
    matches=[]
    for target in targets:
        for rotation in range(4):
            for mirror in (False,True):
                ax,ay,az=anchor['pos'];rx,rz=turn(ax,az,rotation,mirror)
                origin=(target[0]-rx,target[1]-ay,target[2]-rz)
                for b in pattern:
                    x,y,z=b['pos'];x,z=turn(x,z,rotation,mirror)
                    position=(origin[0]+x,origin[1]+y,origin[2]+z)
                    if normalized(blocks.get(position,''))!=normalized(b['name']):break
                else:matches.append(dict(origin=list(origin),rotation=rotation,mirror=mirror,matched_blocks=len(pattern)))
    return matches

def igloo(blocks,templates):
    # Match furniture, colored floor, both ice windows and the full floor footprint.
    def top(b):return b['name']!='minecraft:air'and(b['pos'][1]==0 or b['name']not in ('minecraft:snow_block',))
    bottom=templates['igloo/igloo_bottom.nbt']
    lab_names={'minecraft:brewing_stand','minecraft:cauldron','minecraft:ladder','minecraft:chest'}
    labs=match_template(blocks,bottom,lambda b:b['name']in lab_names,'minecraft:brewing_stand')
    plain=match_template(blocks,templates['igloo/igloo_top_no_trapdoor.nbt'],top,'minecraft:crafting_table')
    trapped=match_template(blocks,templates['igloo/igloo_top_trapdoor.nbt'],top,'minecraft:crafting_table')
    connected=[]
    for hut in trapped:
        for lab in labs:
            if abs(hut['origin'][0]-lab['origin'][0])<=16 and abs(hut['origin'][2]-lab['origin'][2])<=16 and lab['origin'][1]<hut['origin'][1]:connected.append(dict(hut=hut,lab=lab))
    value=True if connected and not plain else False if plain and not trapped and not labs else None
    return dict(value=value,plain=plain,trapped=trapped,laboratories=labs,connected=connected,reason='positive template signatures; missing/clipped/conflicting signatures UNKNOWN')

def bastion(entities):
    positive=[];negative=[]
    for e in entities:
        loot=e.get('loot_table','').removesuffix('.json')
        if loot.endswith('/bastion_treasure'):positive.append(e)
        elif loot.endswith('/bastion_bridge')or loot.endswith('/bastion_hoglin_stable'):negative.append(e)
        elif e.get('id')=='MobSpawner'and e.get('spawn_entity')in ('minecraft:magma_cube','magma_cube'):positive.append(e)
    value=True if positive and not negative else False if negative and not positive else None
    reason='matched treasure signature'if value is True else'matched explicit other-subtype signature'if value is False else'no unique signature or conflicting signatures; shared bastion_other and absence are UNKNOWN'
    return dict(value=value,treasure_signals=positive,other_subtype_signals=negative,reason=reason)

def from_report(report):
    blocks={}
    for r in report.get('results',[]):
        for point in r.get('pointRows',[]):blocks[point['x'],point['y'],point['z']]=point['block']
        if not r['volume']:continue
        x0,y0,z0,x1,y1,z1=r['volume'];values=iter(r['indices'])
        for x in range(x0,x1):
            for z in range(z0,z1):
                for y in range(y0,y1):blocks[x,y,z]=r['palette'][next(values)]
        try:next(values);raise ValueError('Trailing volume data')
        except StopIteration:pass
    return blocks

def igloo_positive_entities(entities,templates,start):
    """Exclusive basement loot + actual brewing displacement + surface furniture."""
    top=templates['igloo/igloo_top_no_trapdoor.nbt']
    surface=[b for b in top['blocks']if b['name']in('minecraft:furnace','minecraft:red_bed')]
    furnace=next(b for b in surface if b['name']=='minecraft:furnace');matches=[]
    nearby=[e for e in entities if max(abs(e['position'][0]-start[0]),abs(e['position'][2]-start[1]))<=32]
    for e in nearby:
        if e['id']!='Furnace':continue
        for rotation in range(4):
            for mirror in(False,True):
                x,z=turn(furnace['pos'][0],furnace['pos'][2],rotation,mirror);origin=[e['position'][0]-x,e['position'][1]-furnace['pos'][1],e['position'][2]-z]
                for b in surface:
                    x,z=turn(b['pos'][0],b['pos'][2],rotation,mirror);pos=[origin[0]+x,origin[1]+b['pos'][1],origin[2]+z];kind='Bed'if b['name']=='minecraft:red_bed'else'Furnace'
                    if not any(v['id']==kind and v['position']==pos for v in nearby):break
                else:matches.append(dict(origin=origin,rotation=rotation,mirror=mirror))
    signals=[]
    for chest in nearby:
        if chest['id']!='Chest'or not chest.get('loot_table','').removesuffix('.json').endswith('/igloo_chest'):continue
        for brew in nearby:
            if brew['id']!='BrewingStand':continue
            for hut in matches:
                dx,dz=turn(4,0,hut['rotation'],hut['mirror'])
                if [brew['position'][i]-chest['position'][i]for i in range(3)]!=[dx,1,dz]:continue
                if not 0<hut['origin'][1]-chest['position'][1]<=64:continue
                cx,cz=turn(4,-2,hut['rotation'],hut['mirror'])
                expected=[chest['position'][0]+cx,chest['position'][1],chest['position'][2]+cz]
                cauldron=next((e for e in nearby if e['id']=='Cauldron'and e['position']==expected),None)
                if cauldron is not None:signals.append(dict(hut=hut,chest=chest,brewing_stand=brew,cauldron=cauldron))
    return dict(value=True if signals else None,signals=signals,reason='Exclusive unopened igloo basement loot and actual lab displacement below matching surface furniture; absence UNKNOWN')

def static_checks(templates):
    count=0
    for rotation in range(4):
        for mirror in (False,True):
            for expected in (False,True):
                blocks={}
                paths=['igloo/igloo_top_'+('trapdoor'if expected else'no_trapdoor')+'.nbt']
                if expected:paths+=['igloo/igloo_bottom.nbt']
                for path in paths:
                    for b in templates[path]['blocks']:
                        x,y,z=b['pos'];x,z=turn(x,z,rotation,mirror)
                        blocks[x-200,y+(30 if 'bottom' in path else 64),z+24]=b['name']
                result=igloo(blocks,templates);assert result['value']is expected,result
                del blocks[next(p for p,n in blocks.items()if n=='minecraft:crafting_table')]
                assert igloo(blocks,templates)['value']is None
                count+=2
    for entities,expected in [([],None),([{'loot_table':'loot_tables/chests/bastion_other'}],None),([{'loot_table':'loot_tables/chests/bastion_treasure'}],True),([{'loot_table':'loot_tables/chests/bastion_bridge'}],False),([{'id':'MobSpawner','spawn_entity':'minecraft:magma_cube'}],True),([{'loot_table':'loot_tables/chests/bastion_treasure'},{'loot_table':'loot_tables/chests/bastion_bridge'}],None),([{'spawn_entity':'minecraft:magma_cube'}],None)]:
        assert bastion(entities)['value']is expected;count+=1
    assert normalized('minecraft:snow')==normalized('minecraft:snow_block')!=normalized('minecraft:snow_layer');count+=1
    for rotation in range(4):
        entities=[]
        for path,y0 in[('igloo/igloo_top_no_trapdoor.nbt',64),('igloo/igloo_bottom.nbt',30)]:
            for b in templates[path]['blocks']:
                kind={'minecraft:furnace':'Furnace','minecraft:red_bed':'Bed','minecraft:brewing_stand':'BrewingStand','minecraft:cauldron':'Cauldron','minecraft:chest':'Chest'}.get(b['name'])
                if not kind:continue
                x,z=turn(b['pos'][0],b['pos'][2],rotation,False);entities.append(dict(id=kind,position=[x-200,y0+b['pos'][1],z+24],loot_table='loot_tables/chests/igloo_chest.json'if kind=='Chest'else''))
        assert igloo_positive_entities(entities,templates,[-200,24])['value']is True;count+=1
        assert igloo_positive_entities([e for e in entities if e['id']!='Cauldron'],templates,[-200,24])['value']is None;count+=1
    return count

if __name__=='__main__':
    path=Path('/Users/lucasraicu/.local/share/antigravity-worker-mcp/variant-controls-approved-20261022/templates.json')
    templates={r['path']:r for r in json.loads(path.read_text())}
    print(json.dumps(dict(static_signature_checks=static_checks(templates))))
