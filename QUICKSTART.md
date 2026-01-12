# Quick Start: Testing with Docker

## TL;DR - Run Tests Now

### Option 1: Run All Tests (Recommended)

**Linux/Mac:**

```bash
chmod +x run-tests.sh
./run-tests.sh
```

**Windows (PowerShell):**

```powershell
.\run-tests.ps1
```

### Option 2: Manual Commands

```bash
# Build and run all tests
docker-compose run --rm latest

# Run only PIDINST tests
docker-compose run --rm latest pytest tests/test_pidinst.py -v

# Run with coverage
docker-compose run --rm latest pytest --cov=ckanext.doi tests/
```

## What Gets Tested

### ✅ PIDINST Functionality

- Owner → Creators mapping
- Manufacturer → Contributors (Producer) mapping
- Alternate identifiers (serial numbers)
- Related identifiers (manuals, related instruments)
- Instrument resource type
- Schema 4.5 validation

### ✅ Backwards Compatibility

- Legacy `author` field fallback
- Existing dataset support
- Schema validation

### ✅ DataCite Integration

- Schema 4.5 support
- XML generation
- Validation

## Expected Output

You should see output like:

```
================================ test session starts ================================
tests/test_pidinst.py::test_pidinst_owner_mapping PASSED                     [  8%]
tests/test_pidinst.py::test_pidinst_manufacturer_mapping PASSED              [ 16%]
tests/test_pidinst.py::test_pidinst_alternate_identifiers PASSED             [ 25%]
tests/test_pidinst.py::test_pidinst_related_identifiers PASSED               [ 33%]
tests/test_pidinst.py::test_instrument_resource_type PASSED                  [ 41%]
tests/test_pidinst.py::test_schema_version_45 PASSED                         [ 50%]
tests/test_pidinst.py::test_schema45_validation PASSED                       [ 58%]
tests/test_pidinst.py::test_legacy_author_fallback PASSED                    [ 66%]
tests/test_pidinst.py::test_multiple_owners PASSED                           [ 75%]
tests/test_pidinst.py::test_missing_optional_pidinst_fields PASSED           [ 83%]

============================== 10 passed in 2.34s ================================
```

## Quick Verification

### 1. Check Schema 4.5 is Available

```bash
docker-compose run --rm latest python -c "from datacite import schema45; print('✓ Schema 4.5 OK')"
```

### 2. Test PIDINST Mapping

```bash
docker-compose run --rm latest python << 'EOF'
from ckanext.doi.lib.metadata import build_metadata_dict

pkg = {
    'id': 'test',
    'name': 'test',
    'title': 'Test Instrument',
    'owner': [{'owner_name': 'Test Org'}],
    'metadata_created': '2024-01-15',
    'tags': [],
    'resources': []
}

metadata = build_metadata_dict(pkg)
print('✓ Creators:', metadata['creators'][0]['name'])
EOF
```

### 3. Verify Resource Type

```bash
docker-compose run --rm latest pytest tests/test_pidinst.py::test_instrument_resource_type -v
```

## Troubleshooting

### Issue: "schema45 not found"

**Solution:** Rebuild the Docker image

```bash
docker-compose build latest --no-cache
```

### Issue: Tests don't run

**Solution:** Check Docker is running

```bash
docker ps
docker-compose ps
```

### Issue: Import errors in tests

**Solution:** Check volumes are mounted

```bash
docker-compose run --rm latest ls -la /base/src/ckanext-doi/ckanext/doi/lib/
```

## Interactive Testing

Start a shell in the container for manual testing:

```bash
docker-compose run --rm latest bash
```

Inside the container:

```bash
# Run specific test
pytest tests/test_pidinst.py::test_pidinst_owner_mapping -v

# Run with detailed output
pytest tests/test_pidinst.py -vv -s

# Check imports
python -c "from datacite import schema45; print(schema45.__file__)"

# Test metadata generation
python tests/manual_test_pidinst.py
```

## Next Steps After Tests Pass

1. ✅ All tests pass → Ready to deploy
2. ⚠️ Some tests fail → Check TESTING.md for detailed debugging
3. 🔧 Need customization → See MIGRATION_DATACITE_45.md

## Documentation

- Full testing guide: [TESTING.md](TESTING.md)
- Migration guide: [MIGRATION_DATACITE_45.md](MIGRATION_DATACITE_45.md)
- Configuration: [CONFIG_GUIDE.md](CONFIG_GUIDE.md)
- Main README: [README.md](README.md)
