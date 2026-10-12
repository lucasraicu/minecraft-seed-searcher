"""Embed the current supported catalog and prepare the browser fallback."""
import json
import re
from pathlib import Path
from seed_search.backend import STRUCTURES, biome_catalog

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs'
families = json.loads((ROOT / 'runs/count-bits-2026-10-11/biome-variants-identity.json').read_text())['families']
limits = json.loads((ROOT / 'runs/count-bits-2026-10-11/overworld-count-limits.json').read_text())
ceilings = {x['structure']: x['geometric_or_model_ceiling'] for x in limits['structures']}
ceilings.update(fortress=9, bastion=9, ruined_portal_nether=9)
labels = {'trial_chamber':'Trial Chamber','stronghold':'Stronghold','mineshaft':'Mineshaft','ancient_city':'Ancient City','village':'Village','ruined_portal':'Ruined Portal','shipwreck':'Shipwreck','monument':'Ocean Monument','outpost':'Pillager Outpost','fortress':'Nether Fortress','bastion':'Bastion Remnant','desert_pyramid':'Desert Pyramid / Sand Temple','jungle_temple':'Jungle Temple','swamp_hut':'Swamp Hut','igloo':'Igloo','ocean_ruin':'Ocean Ruin','mansion':'Woodland Mansion','buried_treasure':'Buried Treasure','trail_ruins':'Trail Ruins','abandoned_camp':'Abandoned Camp','ruined_portal_nether':'Nether Ruined Portal','end_city':'End City'}
family_labels = {'plains_meadow':'Plains / Meadow','dark_pale':'Dark Forest / Pale Garden','rivers_shores':'Rivers / Shores','snowy_ice':'Snow / Ice','mushroom':'Mushroom Fields','cherry':'Cherry Grove'}
structures = [{'id':s,'label':labels[s], 'dimension':1 if s=='end_city' else -1 if s in ('fortress','bastion','ruined_portal_nether') else 0,'ceiling':ceilings.get(s)} for s in STRUCTURES]
groups = [{'id':name,'label':family_labels.get(name,name.replace('_',' ').title()),**value} for name,value in families.items()]
live = {x['id']:x for x in biome_catalog() if x['version_active'] and x['generates']}
listed = [i for group in groups for i in group['ids']]
assert len(STRUCTURES)==22 and len(live)==66
assert len(listed)==len(set(listed))==66 and set(listed)==set(live)
for group in groups:
    assert group['capacity']==len(group['ids'])
    for i,name in zip(group['ids'],group['variants'],strict=True):
        assert live[i]['dimension']==group['dimension'] and live[i]['name']==name
data = {'structures':structures,'families':groups}
(OUT/'seed-requirement-catalog.json').write_text(json.dumps(data,indent=2)+'\n')
source = OUT/'seed-requirement-picker.html'
text = source.read_text()
text = text.replace('__CATALOG_DATA__',json.dumps(data,separators=(',',':')))
assert '__CATALOG_DATA__' not in text
source.write_text(text)
fallback = re.sub(r'/\* HOST_ACTION_START \*/.*?/\* HOST_ACTION_END \*/',"root.querySelector('#seed-send').remove();",text,flags=re.S)
assert 'sendFollowUpMessage' not in fallback
(OUT/'seed-requirement-picker-browser-source.html').write_text(fallback)
print(json.dumps({'structures':len(structures),'biomes':len(listed),'overworld_biomes':sum(x['dimension']==0 for x in live.values()),'catalog_matches_live_detector':True}))
