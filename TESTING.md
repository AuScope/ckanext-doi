# Testing Guide for DataCite 4.5 + PIDINST

This guide shows how to test the upgraded DOI extension using Docker Compose, without needing a local Python environment.

## Quick Start

### 1. Run Existing Unit Tests

Test against CKAN 2.9.x:

```bash
docker-compose run --rm latest
```

Test against CKAN 2.10.x:

```bash
docker-compose run --rm next
```

Both commands will:

- Build the Docker image with updated dependencies
- Run the full pytest suite
- Show test results and coverage

### 2. Run Specific Tests

Test only metadata generation:

```bash
docker-compose run --rm latest pytest tests/test_generate.py -v
```

Test PIDINST-specific functionality:

```bash
docker-compose run --rm latest pytest tests/test_generate.py::test_pidinst_owner_mapping -v
```

### 3. Interactive Testing

Start an interactive shell in the container:

```bash
docker-compose run --rm latest bash
```

Then inside the container:

```bash
# Run Python tests
pytest tests/ -v

# Or test imports manually
python -c "from datacite import schema45; print('Schema 4.5 OK')"

# Or test metadata generation
python tests/manual_test_pidinst.py
```

## Manual Testing with Sample Data

### Test 1: PIDINST Instrument Metadata

Create `tests/manual_test_pidinst.py`:

```python
#!/usr/bin/env python3
"""Manual test for PIDINST instrument metadata mapping"""

import sys
from ckanext.doi.lib.metadata import build_metadata_dict, build_xml_dict
from datacite import schema45

# Sample instrument package dict following PIDINST schema
INSTRUMENT_PKG = {
    'id': 'test-instrument-123',
    'name': 'test-seismometer',
    'title': 'Broadband Seismometer Station XYZ',
    'type': 'instrument',
    'state': 'active',
    'private': False,

    # PIDINST: Owner (becomes creators)
    'owner': [
        {
            'owner_name': 'Australian National University',
            'owner_contact': 'geophysics@anu.edu.au',
            'owner_identifier': 'https://ror.org/019wvm592',
            'owner_identifier_type': 'ROR'
        }
    ],

    # PIDINST: Manufacturer (becomes contributors)
    'manufacturer': [
        {
            'manufacturer_name': 'Guralp Systems',
            'manufacturer_identifier': 'https://www.guralp.com',
            'manufacturer_identifier_type': 'URL'
        }
    ],

    # PIDINST: Alternate identifiers
    'alternate_identifier_obj': [
        {
            'alternate_identifier': 'SN-2024-0123',
            'alternate_identifier_type': 'SerialNumber',
            'alternate_identifier_name': 'Device Serial Number'
        }
    ],

    # PIDINST: Related identifiers
    'related_identifier_obj': [
        {
            'related_identifier': 'https://www.guralp.com/documents/MAN-CMG-0003.pdf',
            'related_identifier_type': 'URL',
            'relation_type': 'IsDescribedBy',
            'related_identifier_name': 'User Manual'
        }
    ],

    'notes': 'A broadband seismometer for earthquake monitoring',
    'metadata_created': '2024-01-15T10:30:00',
    'metadata_modified': '2024-01-15T10:30:00',
    'tags': [],
    'resources': []
}

def test_pidinst_mapping():
    """Test PIDINST field mapping to DataCite"""
    print("\\n" + "="*70)
    print("Testing PIDINST → DataCite 4.5 Mapping")
    print("="*70)

    # Build metadata
    print("\\n1. Building metadata dict...")
    metadata_dict = build_metadata_dict(INSTRUMENT_PKG)

    # Check creators (from owner)
    print("\\n2. Checking creators (from 'owner' field)...")
    assert 'creators' in metadata_dict, "Missing creators"
    assert len(metadata_dict['creators']) > 0, "No creators found"
    print(f"   ✓ Found {len(metadata_dict['creators'])} creator(s)")
    print(f"   Creator: {metadata_dict['creators'][0]}")

    # Check contributors (from manufacturer)
    print("\\n3. Checking contributors (from 'manufacturer' field)...")
    assert 'contributors' in metadata_dict, "Missing contributors"
    assert len(metadata_dict['contributors']) > 0, "No contributors found"
    print(f"   ✓ Found {len(metadata_dict['contributors'])} contributor(s)")
    print(f"   Contributor: {metadata_dict['contributors'][0]}")
    assert metadata_dict['contributors'][0]['contributorType'] == 'Producer'

    # Check alternate identifiers
    print("\\n4. Checking alternate identifiers...")
    assert 'alternateIdentifiers' in metadata_dict
    serial_number = [a for a in metadata_dict['alternateIdentifiers']
                     if a.get('alternateIdentifierType') == 'SerialNumber']
    assert len(serial_number) > 0, "Serial number not found"
    print(f"   ✓ Serial number: {serial_number[0]['alternateIdentifier']}")

    # Check related identifiers
    print("\\n5. Checking related identifiers...")
    assert 'relatedIdentifiers' in metadata_dict
    assert len(metadata_dict['relatedIdentifiers']) > 0
    print(f"   ✓ Found {len(metadata_dict['relatedIdentifiers'])} related identifier(s)")

    # Build XML dict
    print("\\n6. Building XML dict...")
    xml_dict = build_xml_dict(metadata_dict)

    # Check resource type
    print("\\n7. Checking resource type...")
    assert xml_dict['types']['resourceTypeGeneral'] == 'Instrument'
    print(f"   ✓ Resource type: {xml_dict['types']['resourceTypeGeneral']}")

    # Check schema version
    print("\\n8. Checking schema version...")
    assert 'kernel-4' in xml_dict['schemaVersion']
    print(f"   ✓ Schema version: {xml_dict['schemaVersion']}")

    # Validate against DataCite schema
    print("\\n9. Validating against DataCite Schema 4.5...")
    xml_dict['identifiers'] = [{'identifierType': 'DOI', 'identifier': '10.5072/test'}]
    try:
        schema45.validator.validate(xml_dict)
        print("   ✓ Validation passed!")
    except Exception as e:
        print(f"   ✗ Validation failed: {e}")
        raise

    # Generate XML
    print("\\n10. Generating XML...")
    xml_string = schema45.tostring(xml_dict)
    print(f"   ✓ Generated {len(xml_string)} bytes of XML")

    print("\\n" + "="*70)
    print("✓ All PIDINST tests passed!")
    print("="*70)

    return xml_dict

def test_legacy_dataset_mapping():
    """Test backwards compatibility with legacy dataset fields"""
    print("\\n" + "="*70)
    print("Testing Legacy Dataset → DataCite Mapping")
    print("="*70)

    LEGACY_PKG = {
        'id': 'test-dataset-456',
        'name': 'test-dataset',
        'title': 'Test Dataset',
        'type': 'dataset',
        'state': 'active',
        'private': False,

        # Legacy: author field
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

        'notes': 'A test dataset',
        'metadata_created': '2024-01-15T10:30:00',
        'metadata_modified': '2024-01-15T10:30:00',
        'tags': [],
        'resources': []
    }

    print("\\n1. Building metadata dict from legacy fields...")
    metadata_dict = build_metadata_dict(LEGACY_PKG)

    print("\\n2. Checking fallback to 'author' field...")
    assert 'creators' in metadata_dict
    assert len(metadata_dict['creators']) > 0
    print(f"   ✓ Creator from author: {metadata_dict['creators'][0]['name']}")

    print("\\n3. Building XML dict...")
    xml_dict = build_xml_dict(metadata_dict)

    # With default config, should still be Instrument
    # In practice, you'd configure this differently for data repos
    print(f"\\n4. Resource type: {xml_dict['types']['resourceTypeGeneral']}")

    print("\\n" + "="*70)
    print("✓ Legacy dataset compatibility confirmed!")
    print("="*70)

if __name__ == '__main__':
    try:
        # Mock config for testing
        from unittest.mock import MagicMock
        import ckan.plugins.toolkit as toolkit
        toolkit.config = {
            'ckan.plugins': '',
            'ckanext.doi.publisher': 'Test Publisher',
            'ckanext.doi.datacite_schema_version': '4.5',
            'ckanext.doi.resource_type': 'Instrument'
        }

        test_pidinst_mapping()
        test_legacy_dataset_mapping()

        print("\\n✅ All manual tests passed!\\n")
        sys.exit(0)
    except Exception as e:
        print(f"\\n❌ Test failed: {e}\\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
```

Run this test:

```bash
docker-compose run --rm latest python tests/manual_test_pidinst.py
```

### Test 2: Schema Version Validation

Create `tests/test_schema_version.sh`:

```bash
#!/bin/bash
# Test that schema45 is available and working

set -e

echo "Testing DataCite Schema 4.5 Support"
echo "===================================="

# Test 1: Import schema45
echo -e "\\n1. Testing import..."
python -c "from datacite import schema45; print('✓ schema45 imported successfully')"

# Test 2: Check validator
echo -e "\\n2. Testing validator..."
python -c "from datacite import schema45; print('✓ Validator:', type(schema45.validator))"

# Test 3: Validate minimal example
echo -e "\\n3. Testing validation..."
python << EOF
from datacite import schema45

xml_dict = {
    'identifiers': [{'identifierType': 'DOI', 'identifier': '10.5072/test'}],
    'creators': [{'name': 'Test Creator'}],
    'titles': [{'title': 'Test Instrument'}],
    'publisher': 'Test Publisher',
    'publicationYear': '2024',
    'types': {
        'resourceType': 'Instrument',
        'resourceTypeGeneral': 'Instrument'
    },
    'schemaVersion': 'http://datacite.org/schema/kernel-4'
}

schema45.validator.validate(xml_dict)
print('✓ Validation passed')
print('✓ Instrument resource type supported')
EOF

echo -e "\\n===================================="
echo "✅ All schema tests passed!"
```

Run this test:

```bash
docker-compose run --rm latest bash tests/test_schema_version.sh
```

## Integration Testing

### Option 1: Using Docker Compose with Mock DataCite

The existing tests mock the DataCite API, so you don't need real credentials:

```bash
# Build and run all tests
docker-compose build latest
docker-compose run --rm latest

# Check test output for:
# - "test_pidinst_owner_mapping"
# - "test_schema45_validation"
# - All tests passing
```

### Option 2: Test with Real DataCite Test Account

If you have DataCite test credentials, create a test config:

Create `docker-compose.test.yml`:

```yaml
version: "3"

services:
  test-with-datacite:
    build:
      context: .
      dockerfile: docker/Dockerfile_latest
    environment:
      PYTHONUNBUFFERED: 1
      CKAN_SQLALCHEMY_URL: postgresql://ckan:password@db/ckan_test
      CKAN_SOLR_URL: http://solr:8983/solr/ckan
      CKAN_REDIS_URL: redis://redis:6379/0
      CKAN_INI: test.ini
      # DataCite test credentials
      CKANEXT__DOI__ACCOUNT_NAME: ${DATACITE_TEST_USER}
      CKANEXT__DOI__ACCOUNT_PASSWORD: ${DATACITE_TEST_PASSWORD}
      CKANEXT__DOI__PREFIX: ${DATACITE_TEST_PREFIX}
      CKANEXT__DOI__PUBLISHER: "Test Instrument Registry"
      CKANEXT__DOI__TEST_MODE: "true"
      CKANEXT__DOI__DATACITE_SCHEMA_VERSION: "4.5"
      CKANEXT__DOI__RESOURCE_TYPE: "Instrument"
    depends_on:
      - db
      - solr
      - redis
    volumes:
      - ./ckanext:/base/src/ckanext-doi/ckanext
      - ./tests:/base/src/ckanext-doi/tests
    command: pytest tests/test_api.py -v
```

Create `.env` file:

```bash
DATACITE_TEST_USER=your-test-account
DATACITE_TEST_PASSWORD=your-test-password
DATACITE_TEST_PREFIX=10.XXXXX
```

Run:

```bash
docker-compose -f docker-compose.test.yml run --rm test-with-datacite
```

## Verification Checklist

After running tests, verify:

- [ ] ✓ `schema45` imports successfully
- [ ] ✓ PIDINST `owner` field maps to `creators`
- [ ] ✓ PIDINST `manufacturer` field maps to `contributors` (Producer)
- [ ] ✓ `alternate_identifier_obj` appears in alternateIdentifiers
- [ ] ✓ `related_identifier_obj` appears in relatedIdentifiers
- [ ] ✓ `resourceTypeGeneral` is "Instrument"
- [ ] ✓ Schema version is "kernel-4"
- [ ] ✓ Validation passes against DataCite Schema 4.5
- [ ] ✓ Legacy `author` field still works (backwards compat)
- [ ] ✓ All existing tests still pass

## Troubleshooting

### "datacite.schema45 not found"

Rebuild Docker image:

```bash
docker-compose build latest --no-cache
```

### "Validation failed"

Check the generated XML:

```bash
docker-compose run --rm latest python << EOF
from ckanext.doi.lib.metadata import build_metadata_dict, build_xml_dict
from datacite import schema45
import json

# ... your pkg_dict here ...

metadata = build_metadata_dict(pkg_dict)
xml_dict = build_xml_dict(metadata)
xml_dict['identifiers'] = [{'identifierType': 'DOI', 'identifier': '10.5072/test'}]

print(json.dumps(xml_dict, indent=2))
print("\\n" + "="*70)
print(schema45.tostring(xml_dict))
EOF
```

### Tests fail with import errors

Check that volumes are mounted correctly:

```bash
docker-compose run --rm latest ls -la /base/src/ckanext-doi/ckanext/doi/lib/
```

## CI/CD Integration

For GitHub Actions or similar:

```yaml
name: Test DOI Extension

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Build Docker image
        run: docker-compose build latest

      - name: Run tests
        run: docker-compose run --rm latest

      - name: Test PIDINST mapping
        run: docker-compose run --rm latest pytest tests/test_generate.py::test_pidinst_owner_mapping -v
```

## Next Steps

1. **Run unit tests**: `docker-compose run --rm latest`
2. **Check for PIDINST tests**: Look for new test functions in test output
3. **Manual verification**: Use the manual test script above
4. **Integration test**: If you have DataCite credentials, test real DOI minting

All tests should pass without needing to install anything locally! 🎉
