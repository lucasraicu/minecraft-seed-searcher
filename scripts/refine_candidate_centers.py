"""Reevaluate one finalist over every eligible 16- or 8-block v3 center."""
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from seed_search.realm.blueprint import evaluate_dynamic_seed
from seed_search.realm.config import dynamic_v3_blueprint_config, validate_config
from seed_search.realm.cli import load
from seed_search.realm.capabilities import identity


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed',required=True)
    parser.add_argument('--config',type=Path,help='Use the finalist run policy; default is full v3 palette')
    parser.add_argument('--grid-step',type=int,choices=(8,16),default=16)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():parser.error('Choose a fresh output file')
    cfg=load(args.config) if args.config else dynamic_v3_blueprint_config()
    validate_config(cfg)
    initial=evaluate_dynamic_seed(0,args.seed,cfg,short_circuit=False)
    refined=evaluate_dynamic_seed(0,args.seed,cfg,short_circuit=False,center_grid_step=args.grid_step)
    def rank(record):
        if not record['anchors']:return (float('inf'),)
        a=record['anchors'][0]
        return (-a['baseline_score_observed'],a['radial_key'],a['origin_distance_squared'],*a['evaluation_center'])
    result={'config':cfg,'computation_identity':identity(),'initial':initial,'refined':refined,
            'recommended_source':min(('initial','refined'),key=lambda key:rank({'initial':initial,'refined':refined}[key])),
            'scope':'independent pinned predictor, no BDS/world-generation certification'}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    for label,record in [('initial',initial),('refined',refined)]:
        print(label,[(a['evaluation_center'],a['baseline_score_observed']) for a in record['anchors']])


if __name__=='__main__':main()
