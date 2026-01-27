#!/usr/bin/env python3
# encoding: utf-8
#
# This file is part of ckanext-doi
# Created by the Natural History Museum in London, UK

import pytest
from datacite import schema45

from ckanext.doi.lib.metadata import build_metadata_dict, build_xml_dict


# PIDINST instrument package dict
PIDINST_INSTRUMENT_PKG = {
    'id': 'test-instrument-123',
    'name': 'test-seismometer',
    'title': 'Broadband Seismometer Station XYZ',
    'type': 'instrument',
    'state': 'active',
    'private': False,
    'owner': [
        {
            'owner_name': 'Australian National University',
            'owner_contact': 'geophysics@anu.edu.au',
            'owner_identifier': 'https://ror.org/019wvm592',
            'owner_identifier_type': 'ROR'
        }
    ],
    'manufacturer': [
        {
            'manufacturer_name': 'Guralp Systems',
            'manufacturer_identifier': 'https://www.guralp.com',
            'manufacturer_identifier_type': 'URL'
        }
    ],
    'alternate_identifier_obj': [
        {
            'alternate_identifier': 'SN-2024-0123',
            'alternate_identifier_type': 'SerialNumber',
            'alternate_identifier_name': 'Device Serial Number'
        }
    ],
    'related_identifier_obj': [
        {
            'related_identifier': 'https://manual.example.com/seismometer',
            'related_identifier_type': 'URL',
            'relation_type': 'IsDescribedBy',
            'related_identifier_name': 'User Manual'
        }
    ],
    'description': 'A broadband seismometer for earthquake monitoring',
    'metadata_created': '2024-01-15T10:30:00',
    'metadata_modified': '2024-01-15T10:30:00',
    'tags': [],
    'resources': []
}


@pytest.mark.ckan_config('ckanext.doi.publisher', 'Test Publisher')
@pytest.mark.ckan_config('ckanext.doi.resource_type', 'Instrument')
def test_pidinst_owner_mapping():
    """Test that PIDINST 'owner' field maps to DataCite 'contributors' with HostingInstitution type"""
    metadata_dict = build_metadata_dict(PIDINST_INSTRUMENT_PKG)
    
    assert 'contributors' in metadata_dict
    assert len(metadata_dict['contributors']) == 1
    
    contributor = metadata_dict['contributors'][0]
    assert contributor['name'] == 'Australian National University'
    assert contributor['contributorType'] == 'HostingInstitution'
    assert contributor['nameType'] == 'Organizational'
    assert 'nameIdentifiers' in contributor
    assert contributor['nameIdentifiers'][0]['nameIdentifier'] == 'https://ror.org/019wvm592'
    assert contributor['nameIdentifiers'][0]['nameIdentifierScheme'] == 'ROR'


@pytest.mark.ckan_config('ckanext.doi.publisher', 'Test Publisher')
def test_pidinst_manufacturer_mapping():
    """Test that PIDINST 'manufacturer' field maps to DataCite 'creators'"""
    metadata_dict = build_metadata_dict(PIDINST_INSTRUMENT_PKG)
    
    assert 'creators' in metadata_dict
    assert len(metadata_dict['creators']) == 1
    
    creator = metadata_dict['creators'][0]
    assert creator['name'] == 'Guralp Systems'
    assert creator['nameType'] == 'Organizational'
    assert 'nameIdentifiers' in creator
    assert creator['nameIdentifiers'][0]['nameIdentifier'] == 'https://www.guralp.com'
    assert creator['nameIdentifiers'][0]['nameIdentifierScheme'] == 'URL'


@pytest.mark.ckan_config('ckanext.doi.publisher', 'Test Publisher')
def test_pidinst_alternate_identifiers():
    """Test that PIDINST alternate_identifier_obj maps correctly"""
    metadata_dict = build_metadata_dict(PIDINST_INSTRUMENT_PKG)
    
    assert 'alternateIdentifiers' in metadata_dict
    
    # Should include both the URL (from permalink) and serial number
    serial_numbers = [
        alt for alt in metadata_dict['alternateIdentifiers']
        if alt['alternateIdentifierType'] == 'SerialNumber'
    ]
    
    assert len(serial_numbers) == 1
    assert serial_numbers[0]['alternateIdentifier'] == 'SN-2024-0123'


@pytest.mark.ckan_config('ckanext.doi.publisher', 'Test Publisher')
def test_pidinst_related_identifiers():
    """Test that PIDINST related_identifier_obj maps correctly"""
    metadata_dict = build_metadata_dict(PIDINST_INSTRUMENT_PKG)
    
    assert 'relatedIdentifiers' in metadata_dict
    assert len(metadata_dict['relatedIdentifiers']) == 1
    
    related = metadata_dict['relatedIdentifiers'][0]
    assert related['relatedIdentifier'] == 'https://manual.example.com/seismometer'
    assert related['relatedIdentifierType'] == 'URL'
    assert related['relationType'] == 'IsDescribedBy'


@pytest.mark.ckan_config('ckanext.doi.publisher', 'Test Publisher')
@pytest.mark.ckan_config('ckanext.doi.resource_type', 'Instrument')
def test_instrument_resource_type():
    """Test that resourceTypeGeneral is set to 'Instrument' for PIDINST"""
    metadata_dict = build_metadata_dict(PIDINST_INSTRUMENT_PKG)
    xml_dict = build_xml_dict(metadata_dict)
    
    assert xml_dict['types']['resourceTypeGeneral'] == 'Instrument'
    assert xml_dict['types']['resourceType'] == 'instrument'


@pytest.mark.ckan_config('ckanext.doi.publisher', 'Test Publisher')
@pytest.mark.ckan_config('ckanext.doi.datacite_schema_version', '4.5')
def test_schema_version_45():
    """Test that schema version can be configured to 4.5"""
    metadata_dict = build_metadata_dict(PIDINST_INSTRUMENT_PKG)
    xml_dict = build_xml_dict(metadata_dict)
    
    # Schema version should contain kernel-4 (the URL format uses kernel-4 for 4.x versions)
    assert 'kernel-4' in xml_dict['schemaVersion']


@pytest.mark.ckan_config('ckanext.doi.publisher', 'Test Publisher')
def test_schema45_validation():
    """Test that generated XML validates against DataCite Schema 4.5"""
    metadata_dict = build_metadata_dict(PIDINST_INSTRUMENT_PKG)
    xml_dict = build_xml_dict(metadata_dict)
    
    # Add DOI (required for validation) - DataCite 4.5 uses 'doi' property
    xml_dict['doi'] = '10.5072/test-instrument'
    
    # Validate using schema45 validator
    try:
        schema45.validator.validate(xml_dict)
        # If no exception was raised, validation passed
        assert True
    except Exception as e:
        pytest.fail(f"Validation failed: {e}")


@pytest.mark.ckan_config('ckanext.doi.publisher', 'Test Publisher')
def test_legacy_author_fallback():
    """Test backwards compatibility: falls back to 'author' field when 'owner' not present"""
    legacy_pkg = {
        'id': 'test-dataset-456',
        'name': 'test-dataset',
        'title': 'Test Dataset',
        'type': 'dataset',
        'state': 'active',
        'private': False,
        'author': [
            {
                'author_name': 'Jane Smith',
                'author_name_type': 'Personal',
                'author_affiliation': 'Test University',
                'author_affiliation_identifier': '',
                'author_affiliation_identifier_type': '',
                'author_identifier': '0000-0001-2345-6789',
                'author_identifier_type': 'ORCID'
            }
        ],
        'description': 'A test dataset',
        'metadata_created': '2024-01-15T10:30:00',
        'metadata_modified': '2024-01-15T10:30:00',
        'tags': [],
        'resources': []
    }
    
    metadata_dict = build_metadata_dict(legacy_pkg)
    
    # Should fall back to author field
    assert 'creators' in metadata_dict
    assert len(metadata_dict['creators']) == 1
    assert metadata_dict['creators'][0]['name'] == 'Jane Smith'


@pytest.mark.ckan_config('ckanext.doi.publisher', 'Test Publisher')
def test_multiple_owners():
    """Test handling of multiple owners (hosting institutions)"""
    pkg_with_multiple_owners = dict(PIDINST_INSTRUMENT_PKG)
    pkg_with_multiple_owners['owner'] = [
        {
            'owner_name': 'University A',
            'owner_contact': 'contact@university-a.edu',
            'owner_identifier': 'https://ror.org/111111111',
            'owner_identifier_type': 'ROR'
        },
        {
            'owner_name': 'University B',
            'owner_contact': 'contact@university-b.edu',
            'owner_identifier': 'https://ror.org/222222222',
            'owner_identifier_type': 'ROR'
        }
    ]
    
    metadata_dict = build_metadata_dict(pkg_with_multiple_owners)
    
    assert len(metadata_dict['contributors']) == 2
    assert metadata_dict['contributors'][0]['name'] == 'University A'
    assert metadata_dict['contributors'][0]['contributorType'] == 'HostingInstitution'
    assert metadata_dict['contributors'][1]['name'] == 'University B'
    assert metadata_dict['contributors'][1]['contributorType'] == 'HostingInstitution'


@pytest.mark.ckan_config('ckanext.doi.publisher', 'Test Publisher')
def test_missing_optional_pidinst_fields():
    """Test that missing optional PIDINST fields don't cause errors"""
    minimal_instrument = {
        'id': 'minimal-instrument',
        'name': 'minimal-instrument',
        'title': 'Minimal Instrument',
        'type': 'instrument',
        'state': 'active',
        'private': False,
        'manufacturer': [
            {
                'manufacturer_name': 'Test Manufacturer'
                # No identifiers
            }
        ],
        # No owner, no alternate_identifier_obj, no related_identifier_obj
        'description': 'Minimal test',
        'metadata_created': '2024-01-15T10:30:00',
        'metadata_modified': '2024-01-15T10:30:00',
        'tags': [],
        'resources': []
    }
    
    # Should not raise exceptions
    metadata_dict = build_metadata_dict(minimal_instrument)
    xml_dict = build_xml_dict(metadata_dict)
    
    assert 'creators' in metadata_dict
    assert len(metadata_dict['creators']) == 1
    assert metadata_dict['creators'][0]['name'] == 'Test Manufacturer'
