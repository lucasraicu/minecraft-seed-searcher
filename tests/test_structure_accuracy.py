"""Tests for Pillar 1: structure prediction accuracy, piece integrity, and village slope."""
import pytest
from seed_search.backend import Backend
from seed_search.realm.structure_accuracy import (
    check_stronghold_integrity,
    check_village_topography,
    evaluate_finalist_accuracy
)


def test_stronghold_portal_details_returns_valid_structure():
    with Backend(12345) as b:
        strongholds = b.structures('stronghold', (-2048, -2048, 2048, 2048))
        assert len(strongholds) > 0
        sx, sz = strongholds[0]
        
        details = b.stronghold_portal_details(sx, sz)
        assert 'has_portal_room' in details
        assert 'portal_eyes' in details
        assert 'bounding_box' in details
        assert 'valid_depth' in details
        assert len(details['bounding_box']) == 6
        assert 0 <= details['portal_eyes'] <= 12


def test_check_stronghold_integrity_evaluates_piece():
    with Backend(12345) as b:
        strongholds = b.structures('stronghold', (-2048, -2048, 2048, 2048))
        sh = check_stronghold_integrity(b, strongholds[0][0], strongholds[0][1])
        assert sh.has_portal_room is True
        assert sh.status in ('VALID', 'EXTREME_ELEVATION', 'NO_PORTAL_ROOM')


def test_village_topography_samples_grade_delta():
    with Backend(12345) as b:
        villages = b.structures('village', (-1024, -1024, 1024, 1024))
        assert len(villages) > 0
        
        topos = check_village_topography(b, villages[:3])
        assert len(topos) == len(villages[:3])
        for v in topos:
            assert v.grade_delta >= 0
            assert len(v.corner_heights) == 4
            assert v.status in ('HABITABLE', 'CLIFFSIDE_STILTS', 'FLOODED', 'FLOODED_CLIFFSIDE')


def test_evaluate_finalist_accuracy_composite_score():
    with Backend(12345) as b:
        shs = b.structures('stronghold', (-2048, -2048, 2048, 2048))
        vis = b.structures('village', (-1024, -1024, 1024, 1024))
        
        report = evaluate_finalist_accuracy(b, shs, vis)
        assert 'accuracy_score' in report
        assert 0.0 <= report['accuracy_score'] <= 1.0
        assert 'prediction_pass' in report
        assert isinstance(report['prediction_pass'], bool)
        assert report['certified'] is False
        assert 'evidence_provenance' in report

