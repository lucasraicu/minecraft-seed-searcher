"""Per-type coverage, keeping attempted checks distinct from confirmed witnesses."""
from collections import Counter
import hashlib
import json
from pathlib import Path

DIMENSIONS = {'overworld': 0, 'nether': -1}
GROUPED = {'desert_pyramid', 'jungle_temple', 'swamp_hut', 'igloo'}


def coverage(manifest, inventory, results):
    """Describe the frozen model scope; a match never certifies all seeds/patches."""
    if results.get('manifest_sha256') is None:
        raise ValueError('Results must identify their frozen manifest')
    expected = {d: {r['name'] for r in inventory if r['version_active'] and
                   r['generates'] and r['dimension'] == number}
                for d, number in DIMENSIONS.items()}
    biomes = []
    structures = []
    for dimension, names in expected.items():
        for name in sorted(names):
            planned = [(w['seed'], p) for w in manifest['worlds'] for p in w['predictions']
                       if p['dimension'] == dimension and p['biome_name'] == name]
            rows = [r for r in results['biome_rows'] if r['dimension'] == dimension
                    and r['predicted_name'] == name]
            matched = [r for r in rows if r['outcome'] == 'match']
            biomes.append(dict(dimension=dimension, name=name, planned_points=len(planned),
                attempted_points=len(rows), outcomes=dict(Counter(r['outcome'] for r in rows)),
                matching_seeds=sorted({r['seed'] for r in matched}),
                by_cohort={group: dict(Counter(r['outcome'] for r in rows if r['cohort'] == group))
                           for group in ('blind', 'targeted')},
                status='matching_witness_observed' if matched else 'missing_matching_witness'))
        names = {q['structure_type'] for w in manifest['worlds'] for q in w['structures']
                 if q['dimension'] == dimension}
        for name in sorted(names):
            planned = [q for w in manifest['worlds'] for q in w['structures']
                       if q['dimension'] == dimension and q['structure_type'] == name]
            rows = [r for r in results['structure_rows'] if r['dimension'] == dimension
                    and r['structure_type'] == name]
            exact = [r for r in rows if r['outcome'] in ('reference_exact', 'navigation_exact')]
            rejected_exact = [r['case_id'] for r in exact if r['disposition'] == 'rejected']
            discovery_gaps = [r['case_id'] for r in results.get('independent_discovery', [])
                              if r['dimension'] == dimension and r['structure_type'] == name
                              and r['inventory_relation'] == 'possible_omission_requires_followup']
            # /locate temple does not identify which temple subtype exists there.
            status = ('over_rejection_observed' if rejected_exact else
                      'discovery_requires_followup' if discovery_gaps else
                      'grouped_subtype_unresolved' if name in GROUPED else
                      'matching_reference_observed' if exact else 'missing_matching_reference')
            structures.append(dict(dimension=dimension, name=name, planned_queries=len(planned),
                attempted_queries=len(rows), matching_reference_seeds=sorted({r['seed'] for r in exact}),
                rejected_exact_reference_cases=rejected_exact, unmatched_discovery_cases=discovery_gaps,
                outcomes=dict(Counter(r['outcome'] for r in rows)), status=status,
                by_cohort_and_disposition={group: {role: dict(Counter(r['outcome'] for r in rows
                    if r['cohort'] == group and r['disposition'] == role))
                    for role in ('retained', 'rejected', 'discovery')} for group in ('blind', 'targeted')}))
    return dict(revision='generalization-type-coverage-v1', manifest_sha256=results['manifest_sha256'],
                dimensions=list(DIMENSIONS), biomes=biomes, structures=structures,
                limitations=['A matching witness is not all-seed accuracy, recall or an exhaustive count.',
                             'A query with no location or a different reference does not prove absence.',
                             'Grouped temple queries cannot verify their individual subtypes.'],
                generated_count=None, exhaustive_count=None)


def write_coverage(campaign, *, partial=False):
    base = Path(campaign)
    raw = (base / 'manifest.json').read_bytes()
    results_raw = (base / ('partial-results.json' if partial else 'results.json')).read_bytes()
    inventory_raw = (base / 'biome-inventory.json').read_bytes()
    results = json.loads(results_raw)
    if hashlib.sha256(raw).hexdigest() != results['manifest_sha256']:
        raise ValueError('Coverage input manifest differs from results')
    value = coverage(json.loads(raw), json.loads(inventory_raw), results)
    value.update(results_sha256=hashlib.sha256(results_raw).hexdigest(),
                 biome_inventory_sha256=hashlib.sha256(inventory_raw).hexdigest())
    target = base / ('partial-coverage.json' if partial else 'coverage.json')
    target.write_text(json.dumps(value, indent=2) + '\n')
    return dict(path=str(target), biome_types=len(value['biomes']), structure_types=len(value['structures']),
        biome_gaps=[r['name'] for r in value['biomes'] if r['status'] != 'matching_witness_observed'],
        structure_gaps=[r['name'] for r in value['structures'] if r['status'] != 'matching_reference_observed'])


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--campaign', type=Path, required=True)
    parser.add_argument('--partial', action='store_true')
    args = parser.parse_args()
    print(json.dumps(write_coverage(args.campaign, partial=args.partial)))
