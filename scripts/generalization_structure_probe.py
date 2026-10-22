"""Exact locate-reference analysis; never changes admission or asserts absence."""
from collections import Counter, defaultdict
import re
from seed_search.realm.predictor_diagnostics import COMMANDS, LOCATE
from seed_search.realm.structure_coordinates import project_navigation_reference

OUTCOMES = {'reference_exact', 'navigation_exact', 'different_reference', 'no_location',
            'verifier_unavailable', 'error', 'unknown', 'discovery_location'}
TEMPLES = {'desert_pyramid', 'jungle_temple', 'swamp_hut', 'igloo'}


def _point(p):
    if (not isinstance(p, list) or len(p) != 2 or
            any(type(v) is not int or not -(1 << 31) <= v < (1 << 31) for v in p)):
        raise ValueError('Expected strict signed32 [x,z]')
    return list(p)


def assess_locates(cases, results, *, prediction_revision, bds_build):
    if not isinstance(cases, list) or not isinstance(results, list): raise ValueError('Expected case/result lists')
    seen = set(); validated = []
    for case in cases:
        required = {'case_id', 'structure_type', 'dimension', 'predicted', 'origin', 'disposition'}
        if not isinstance(case, dict) or not required.issubset(case): raise ValueError('Invalid case fields')
        ident = case['case_id']
        if not isinstance(ident, str) or not ident or ident in seen: raise ValueError('Duplicate/invalid case ID')
        seen.add(ident)
        if not isinstance(case['structure_type'], str) or not re.fullmatch('[a-z_]+', case['structure_type']): raise ValueError('Invalid structure name')
        if case['dimension'] not in ('overworld', 'nether', 'the_end'): raise ValueError('Invalid dimension')
        if case['disposition'] not in ('retained', 'rejected', 'discovery'): raise ValueError('Invalid disposition')
        if (case['predicted'] is None) != (case['disposition'] == 'discovery'): raise ValueError('Prediction/disposition mismatch')
        validated.append(dict(case_id=ident, structure_type=case['structure_type'], dimension=case['dimension'],
            disposition=case['disposition'], predicted=None if case['predicted'] is None else _point(case['predicted']),
            origin=_point(case['origin']), reported=None, outcome='unknown',
            grouped_command=case['structure_type'] in TEMPLES, interpretation='Missing observation; no absence conclusion'))
    observed = {}
    for result in results:
        if (not isinstance(result, dict) or not isinstance(result.get('case_id'), str) or
                not isinstance(result.get('output'), list) or any(not isinstance(s, str) for s in result['output'])):
            raise ValueError('Invalid result schema')
        ident = result['case_id']
        if ident not in seen: raise ValueError('Orphan result')
        if ident in observed: raise ValueError('Duplicate result')
        observed[ident] = result
    for row in validated:
        if prediction_revision != 'cubiomes-bedrock-26.50' or bds_build != '1.26.52.3':
            row['interpretation'] = 'Unsupported build scope; no comparison or coordinate projection'
            continue
        result = observed.get(row['case_id'])
        if result is None: continue
        lines = result['output']; matches = [m for s in lines if (m := LOCATE.search(s))]
        if len(matches) > 1:
            row.update(outcome='error', interpretation='Ambiguous locate response; no presence/absence conclusion'); continue
        if not matches:
            if any(any(x in s for x in ('Syntax error', 'Unknown command', 'Unknown structure')) for s in lines):
                row.update(outcome='verifier_unavailable', interpretation='Locate capability unavailable; retain uncertainty')
            elif any('No valid structure' in s or 'Could not find' in s for s in lines):
                row.update(outcome='no_location', interpretation='Locate returned no reference; not proof of physical absence')
            else:
                row.update(outcome='error', interpretation='Unrecognized game response; not absence')
            continue
        match = matches[0]
        expected = COMMANDS.get(row['structure_type'], row['structure_type'])
        if match[1] != expected:
            row.update(outcome='error', interpretation='Reported command differs from requested feature'); continue
        try: reported = _point([int(match[2]), int(match[3])])
        except ValueError:
            row.update(outcome='error', interpretation='Game reference outside allowed coordinate range'); continue
        row['reported'] = reported
        if row['predicted'] is None:
            row.update(outcome='discovery_location', interpretation='Independent game-located reference; not an instance census')
        elif reported == row['predicted']:
            row.update(outcome='reference_exact', interpretation='Game locate agrees with predicted reference; not a physical census')
        else:
            projected = project_navigation_reference(row['structure_type'], *row['predicted'],
                prediction_revision=prediction_revision, bds_build=bds_build, dimension=row['dimension'])
            if projected is not None and reported == [projected.navigation_x, projected.navigation_z]:
                row.update(outcome='navigation_exact', interpretation='Exact agreement under declared navigation convention')
            else:
                row.update(outcome='different_reference', interpretation='Locate returned another reference; candidate existence remains unresolved')
        if row['grouped_command']: row['interpretation'] += '; grouped temple command does not confirm subtype'
        if row['disposition'] == 'rejected' and row['outcome'] in ('reference_exact', 'navigation_exact'):
            row['interpretation'] += '; possible over-rejection: retain and investigate this candidate'
    return validated


def summarize_structures(rows):
    if not isinstance(rows, list): raise ValueError('Expected rows')
    dispositions = defaultdict(Counter); types = defaultdict(Counter)
    for row in rows:
        if row.get('outcome') not in OUTCOMES: raise ValueError('Invalid outcome')
        dispositions[row['disposition']][row['outcome']] += 1
        types[row['structure_type']][row['outcome']] += 1
    return dict(total=len(rows), by_disposition={k: dict(v) for k, v in dispositions.items()},
                by_type={k: dict(v) for k, v in types.items()})
