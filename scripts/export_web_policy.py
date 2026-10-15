"""Generate the website's profile metadata from the validated engine policies."""
import json
from pathlib import Path

from seed_search.realm.config import (
    dynamic_blueprint_config, marine_baseline_blueprint_config,
    two_group_blueprint_config, validate_config,
)

ROOT=Path(__file__).resolve().parents[1]


def profiles():
    result={}
    for key,name,factory in (
        ('dynamic1664','1664 sliding center',dynamic_blueprint_config),
        ('marine2048','2048 marine baseline',marine_baseline_blueprint_config),
        ('twoGroup2048','2048 historical baseline',two_group_blueprint_config),
    ):
        cfg=factory();validate_config(cfg)
        counts={**cfg['structures']['minimum_counts'],**cfg['structures']['nether_minimum_counts']}
        floors=cfg['structures']['hard_floors']
        strict={'stronghold','mansion','outpost','fortress','monument','bastion'} if key=='dynamic1664' else {'stronghold','desert_pyramid','jungle_temple','outpost'}
        if key=='marine2048':strict.update(('monument','shipwreck'))
        result[key]={'name':name,'revision':cfg['screening_revision'],'counts':counts,'floors':floors,
                     'flexible':[item for item in counts if item not in strict and item in floors],
                     'overworldSide':cfg['deployment']['overworld_side_blocks'],
                     'netherSide':cfg['deployment']['nether_side_blocks'],
                     'maxMisses':2 if key=='dynamic1664' else 8,
                     'deferredMarine':bool(cfg['structures']['deferred_until_coastal_terrain'])}
    return result


if __name__=='__main__':
    (ROOT/'web-ui/src/constants/searchProfiles.json').write_text(json.dumps(profiles(),indent=2)+'\n')
