#!/usr/bin/env python3
# encoding: utf-8
#
# Tests for DataCite 4.6/4.7 controlled-vocabulary additions, XML generation,
# and relationTypeInformation support.

import copy
import pytest

from ckanext.doi.lib import datacite_compat
from ckanext.doi.lib.metadata import build_metadata_dict, build_xml_dict
from .helpers import constants


# ---------------------------------------------------------------------------
# Helpers — a minimal valid xml_dict that the validator accepts
# ---------------------------------------------------------------------------

def _minimal(**overrides):
    """Return a minimal valid xml_dict, optionally overriding fields."""
    d = copy.deepcopy(constants.XML_DICT)
    d.update(overrides)
    return d


# ---------------------------------------------------------------------------
# dateType — 'Coverage' (4.6)
# ---------------------------------------------------------------------------

def test_validate_date_type_coverage():
    d = _minimal(dates=[{'date': '2020-01-01/2024-12-31', 'dateType': 'Coverage'}])
    datacite_compat.validator.validate(d)


# ---------------------------------------------------------------------------
# resourceTypeGeneral — 'Award', 'Project' (4.6), 'Poster', 'Presentation' (4.7)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('rtype', ['Award', 'Project', 'Poster', 'Presentation'])
def test_validate_resource_type_general(rtype):
    d = _minimal()
    d['types'] = {'resourceType': rtype, 'resourceTypeGeneral': rtype}
    datacite_compat.validator.validate(d)


# ---------------------------------------------------------------------------
# relatedIdentifierType — 'CSTR', 'RRID' (4.6), 'RAiD', 'SWHID' (4.7)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('id_type', ['CSTR', 'RRID', 'RAiD', 'SWHID'])
def test_validate_related_identifier_type(id_type):
    d = _minimal(relatedIdentifiers=[{
        'relatedIdentifier': '10.1234/test',
        'relatedIdentifierType': id_type,
        'relationType': 'References',
    }])
    datacite_compat.validator.validate(d)


# ---------------------------------------------------------------------------
# contributorType — 'Translator' (4.6)
# ---------------------------------------------------------------------------

def test_validate_contributor_type_translator():
    d = _minimal(contributors=[{
        'name': 'Doe, Jane',
        'contributorType': 'Translator',
        'nameType': 'Personal',
    }])
    datacite_compat.validator.validate(d)


# ---------------------------------------------------------------------------
# relationType — 'HasTranslation', 'IsTranslationOf' (4.6), 'Other' (4.7)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('rel_type', ['HasTranslation', 'IsTranslationOf', 'Other'])
def test_validate_relation_type(rel_type):
    d = _minimal(relatedIdentifiers=[{
        'relatedIdentifier': '10.1234/test',
        'relatedIdentifierType': 'DOI',
        'relationType': rel_type,
    }])
    datacite_compat.validator.validate(d)


# ---------------------------------------------------------------------------
# Pre-existing 4.5 values still validate (regression check)
# ---------------------------------------------------------------------------

def test_existing_45_values_still_valid():
    """Ensure patching did not break the base schema45 enum values."""
    d = _minimal(
        dates=[{'date': '2024-01-01', 'dateType': 'Created'}],
        relatedIdentifiers=[{
            'relatedIdentifier': '10.1234/test',
            'relatedIdentifierType': 'DOI',
            'relationType': 'IsCitedBy',
        }],
        contributors=[{
            'name': 'Doe, Jane',
            'contributorType': 'Editor',
            'nameType': 'Personal',
        }],
    )
    d['types'] = {'resourceType': 'Dataset', 'resourceTypeGeneral': 'Dataset'}
    datacite_compat.validator.validate(d)


# ---------------------------------------------------------------------------
# Invalid values should still be rejected
# ---------------------------------------------------------------------------

def test_invalid_date_type_rejected():
    d = _minimal(dates=[{'date': '2024-01-01', 'dateType': 'CompletelyBogus'}])
    with pytest.raises(Exception):
        datacite_compat.validator.validate(d)


def test_invalid_resource_type_general_rejected():
    d = _minimal()
    d['types'] = {'resourceType': 'x', 'resourceTypeGeneral': 'NotReal'}
    with pytest.raises(Exception):
        datacite_compat.validator.validate(d)


# ---------------------------------------------------------------------------
# XML schemaLocation rewrite
# ---------------------------------------------------------------------------

def test_tostring_schema_location_47():
    """tostring() should reference kernel-4.7/metadata.xsd, not 4.5."""
    d = _minimal()
    xml = datacite_compat.tostring(d)
    assert 'kernel-4.7/metadata.xsd' in xml
    assert 'kernel-4.5/metadata.xsd' not in xml


def test_tostring_preserves_namespace():
    """The kernel-4 namespace URI must remain in the output."""
    d = _minimal()
    xml = datacite_compat.tostring(d)
    assert 'http://datacite.org/schema/kernel-4' in xml


# ---------------------------------------------------------------------------
# relationTypeInformation pass-through in metadata.py
# ---------------------------------------------------------------------------

@pytest.mark.ckan_config('ckanext.doi.publisher', 'Test Publisher')
def test_relation_type_information_passthrough():
    """relation_type_information from pkg_dict flows into the metadata dict."""
    from tests.test_pidinst import PIDINST_INSTRUMENT_PKG

    pkg = dict(PIDINST_INSTRUMENT_PKG)
    pkg['related_identifier_obj'] = [
        {
            'related_identifier': 'https://example.com/translated',
            'related_identifier_type': 'URL',
            'relation_type': 'HasTranslation',
            'relation_type_information': 'French translation of user manual',
        }
    ]

    metadata_dict = build_metadata_dict(pkg)
    xml_dict = build_xml_dict(metadata_dict)

    ri = metadata_dict['relatedIdentifiers'][0]
    assert ri['relationType'] == 'HasTranslation'
    assert ri['relationTypeInformation'] == 'French translation of user manual'

    # Should survive into xml_dict
    xi = xml_dict['relatedIdentifiers'][0]
    assert xi['relationTypeInformation'] == 'French translation of user manual'


@pytest.mark.ckan_config('ckanext.doi.publisher', 'Test Publisher')
def test_relation_type_information_absent_when_not_set():
    """relationTypeInformation should NOT appear when the source field is empty."""
    from tests.test_pidinst import PIDINST_INSTRUMENT_PKG

    pkg = dict(PIDINST_INSTRUMENT_PKG)
    pkg['related_identifier_obj'] = [
        {
            'related_identifier': 'https://example.com/ref',
            'related_identifier_type': 'URL',
            'relation_type': 'References',
        }
    ]

    metadata_dict = build_metadata_dict(pkg)
    ri = metadata_dict['relatedIdentifiers'][0]
    assert 'relationTypeInformation' not in ri


# ---------------------------------------------------------------------------
# Verbose XML logging flag (smoke test — we just check it doesn't crash)
# ---------------------------------------------------------------------------

@pytest.mark.ckan_config('ckanext.doi.verbose_xml', 'true')
@pytest.mark.ckan_config('ckanext.doi.publisher', 'Test Publisher')
def test_verbose_xml_flag_does_not_crash():
    """Enabling verbose_xml should not cause an error."""
    from tests.test_pidinst import PIDINST_INSTRUMENT_PKG

    metadata_dict = build_metadata_dict(PIDINST_INSTRUMENT_PKG)
    xml_dict = build_xml_dict(metadata_dict)
    xml_dict['doi'] = '10.5072/verbose-test'
    # Just ensure tostring works (the INFO log line is the actual side-effect)
    xml = datacite_compat.tostring(xml_dict)
    assert len(xml) > 0
