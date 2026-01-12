# DataCite Schema 4.5 and PIDINST Migration Guide

## Overview

This extension has been upgraded from DataCite Metadata Schema v4.3 to v4.5, with enhanced support for PIDINST (Persistent Identification of Instruments) instrument registries.

## What Changed

### 1. DataCite Schema Version

- **Before**: DataCite Metadata Schema v4.3
- **After**: DataCite Metadata Schema v4.5 (configurable)
- **Impact**: Access to new DataCite features, including native "Instrument" resource type

### 2. Primary Use Case

- **Before**: Generic data repository (Dataset-centric)
- **After**: Instrument registry (PIDINST-centric) with dataset fallback

### 3. Metadata Mapping

#### PIDINST Instrument Schema (Primary)

| Field         | Old Mapping              | New Mapping                      | Notes                                       |
| ------------- | ------------------------ | -------------------------------- | ------------------------------------------- |
| Creators      | `author`                 | `owner`                          | Instrument owners/responsible organizations |
| Contributors  | `author` (ContactPerson) | `manufacturer` (Producer)        | Instrument manufacturers                    |
| Alternate IDs | URL only                 | `alternate_identifier_obj` + URL | Support for serial numbers, inventory IDs   |
| Related IDs   | `related_resource`       | `related_identifier_obj`         | Enhanced relationship types                 |
| Resource Type | Dataset                  | Instrument                       | DataCite 4.5 native type                    |

#### Legacy Dataset Schema (Fallback)

The extension maintains backwards compatibility. If PIDINST fields (`owner`, `manufacturer`) are not present, it falls back to legacy `author` field mapping.

## Configuration Changes

### New Configuration Options

Add these to your CKAN configuration file (e.g., `production.ini`):

```ini
# DataCite Schema Version (default: 4.5)
# Options: 4.3, 4.4, 4.5
ckanext.doi.datacite_schema_version = 4.5

# Resource Type General (default: Instrument)
# Options: Dataset, Instrument, PhysicalObject, Software, etc.
# See: https://schema.datacite.org/meta/kernel-4.5/doc/DataCite-MetadataKernel_v4.5.pdf
ckanext.doi.resource_type = Instrument
```

### Existing Configuration (No Changes Required)

These settings remain unchanged:

```ini
# Required settings
ckanext.doi.account_name = YOUR_DATACITE_ACCOUNT
ckanext.doi.account_password = YOUR_PASSWORD
ckanext.doi.prefix = 10.XXXX
ckanext.doi.publisher = Your Institution Name
ckanext.doi.test_mode = True

# Optional settings
ckanext.doi.site_url = https://your-site.org
ckanext.doi.site_title = Your Site Title
```

## PIDINST Schema Field Mapping

Based on `intrument_schema.yaml`, the following CKAN scheming fields are mapped to DataCite:

### Required Fields

| CKAN Field     | DataCite Element          | Example                                                                                                               |
| -------------- | ------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| `title`        | titles[0].title           | "Seismometer XYZ-123"                                                                                                 |
| `owner`        | creators                  | [{"owner_name": "University Observatory", "owner_identifier": "https://ror.org/...", "owner_identifier_type": "ROR"}] |
| `manufacturer` | contributors (Producer)   | [{"manufacturer_name": "InstrumentCorp", "manufacturer_identifier": "...", "manufacturer_identifier_type": "..."}]    |
| `(config)`     | publisher                 | "AuScope Instrument Registry"                                                                                         |
| `(auto)`       | publicationYear           | 2025                                                                                                                  |
| `(config)`     | types.resourceTypeGeneral | "Instrument"                                                                                                          |

### Optional Fields

| CKAN Field                          | DataCite Element     | Notes                             |
| ----------------------------------- | -------------------- | --------------------------------- |
| `alternate_identifier_obj`          | alternateIdentifiers | Serial numbers, inventory numbers |
| `related_identifier_obj`            | relatedIdentifiers   | Related instruments, documents    |
| `description`                       | descriptions         | Technical description             |
| `date` (scheming repeating)         | dates                | Commissioned, DeCommissioned      |
| `funder`                            | fundingReferences    | Project funding information       |
| `location_choice` / `location_data` | geoLocations         | Geographic location of instrument |

### Field Structure Examples

#### Owner (Creator)

```python
{
    "owner_name": "Australian National University",
    "owner_contact": "contact@anu.edu.au",
    "owner_identifier": "https://ror.org/019wvm592",
    "owner_identifier_type": "ROR"
}
```

#### Manufacturer (Contributor)

```python
{
    "manufacturer_name": "Guralp Systems",
    "manufacturer_identifier": "https://www.guralp.com",
    "manufacturer_identifier_type": "URL"
}
```

#### Alternate Identifier

```python
{
    "alternate_identifier": "SN-2024-0123",
    "alternate_identifier_type": "SerialNumber",
    "alternate_identifier_name": "Device Serial Number"
}
```

#### Related Identifier

```python
{
    "related_identifier": "10.5281/zenodo.1234567",
    "related_identifier_type": "DOI",
    "relation_type": "IsDescribedBy",
    "related_identifier_name": "User Manual"
}
```

## Migration Steps

### 1. Update Dependencies

```bash
# Activate your CKAN virtual environment
source /usr/lib/ckan/default/bin/activate

# Upgrade the extension
pip install --upgrade ckanext-doi

# Or if installing from source
cd /usr/lib/ckan/default/src/ckanext-doi
git pull
pip install -e .
```

### 2. Update Configuration

Add new configuration options to your CKAN config file:

```bash
# Edit your config file
vim /etc/ckan/default/production.ini

# Add:
ckanext.doi.datacite_schema_version = 4.5
ckanext.doi.resource_type = Instrument
```

### 3. Test DOI Generation

Test with a sample instrument dataset:

```bash
# Create or update a test package
ckan -c /etc/ckan/default/production.ini package create name=test-instrument \
    title="Test Instrument" \
    owner='[{"owner_name": "Test Institution"}]'

# Update DOI metadata (in test mode)
ckan -c /etc/ckan/default/production.ini doi update-doi test-instrument
```

### 4. Verify Existing DOIs

The extension is backwards compatible. Existing DOIs will continue to work. To update their metadata to the new schema:

```bash
# Update all DOIs to new metadata schema
ckan -c /etc/ckan/default/production.ini doi update-doi

# Or update specific package
ckan -c /etc/ckan/default/production.ini doi update-doi PACKAGE_ID
```

## Backwards Compatibility

### Legacy Dataset Support

If your CKAN instance uses traditional dataset schemas (not PIDINST), the extension will automatically fall back to legacy field mappings:

- `author` → creators (if `owner` not present)
- `author` → contributors as ContactPerson (if `manufacturer` not present)
- `related_resource` → relatedIdentifiers (if `related_identifier_obj` not present)

### Mixed Deployments

You can run both instrument registries and data repositories in the same CKAN instance:

```ini
# Default to Instrument for main registry
ckanext.doi.resource_type = Instrument
```

Then use the `IDoi` plugin interface to override on a per-dataset basis in your custom extension:

```python
from ckan.plugins import implements
from ckanext.doi.interfaces import IDoi

class MyCustomPlugin(plugins.SingletonPlugin):
    implements(IDoi)

    def build_xml_dict(self, metadata_dict, xml_dict):
        # Override for specific dataset types
        if metadata_dict.get('resourceType') == 'dataset':
            xml_dict['types']['resourceTypeGeneral'] = 'Dataset'
        return xml_dict
```

## Testing

### Verify Schema Version

Check that the correct schema is being used:

```python
from ckanext.doi.lib.metadata import build_xml_dict, build_metadata_dict

# Load a package
pkg = toolkit.get_action('package_show')({}, {'id': 'your-package-id'})

# Build metadata
metadata = build_metadata_dict(pkg)
xml_dict = build_xml_dict(metadata)

# Check schema version
print(xml_dict['schemaVersion'])  # Should be: http://datacite.org/schema/kernel-4

# Check resource type
print(xml_dict['types']['resourceTypeGeneral'])  # Should be: Instrument
```

### Validate Against DataCite

```python
from datacite import schema45

# Validate the generated XML
xml_dict['identifiers'] = [{'identifierType': 'DOI', 'identifier': '10.5072/test'}]
schema45.validator.validate(xml_dict)  # Should not raise exception

# Generate XML
xml_doc = schema45.tostring(xml_dict)
print(xml_doc)
```

## Troubleshooting

### Issue: "datacite.schema45 not found"

**Cause**: Datacite library version too old

**Solution**:

```bash
pip install --upgrade 'datacite>=1.1.3'
```

### Issue: "Instrument not a valid resourceTypeGeneral"

**Cause**: Using DataCite schema < 4.5

**Solution**: Update config:

```ini
ckanext.doi.datacite_schema_version = 4.5
```

### Issue: "Required field 'creators' cannot be None"

**Cause**: Missing `owner` field in PIDINST schema

**Solution**: Ensure your scheming schema includes the `owner` field, or provide legacy `author` field:

```python
# In package dict:
{
    "owner": [
        {"owner_name": "Institution Name"}
    ]
}
```

### Issue: DOIs not updating after migration

**Cause**: Cached metadata or test mode restrictions

**Solution**:

1. Clear CKAN cache
2. Verify test_mode setting
3. Manually trigger update:
   ```bash
   ckan -c $CONFIG doi update-doi
   ```

## DataCite 4.5 New Features

This upgrade enables access to DataCite 4.5 features:

1. **Native Instrument Type**: `resourceTypeGeneral = Instrument`
2. **Enhanced Identifiers**: Wikidata support in fundingReferences
3. **Improved Relations**: More relationType options for instruments
4. **Better Validation**: Stricter schema validation

## References

- [DataCite Metadata Schema 4.5](https://schema.datacite.org/meta/kernel-4.5/)
- [PIDINST Schema](https://github.com/rdawg-pidinst/schema)
- [DataCite Python Library](https://github.com/inveniosoftware/datacite)
- [ckanext-doi Documentation](https://ckanext-doi.readthedocs.io/)

## Support

For issues or questions:

1. Check the [ckanext-doi issues](https://github.com/NaturalHistoryMuseum/ckanext-doi/issues)
2. Review the updated [metadata.py](ckanext/doi/lib/metadata.py) source code
3. Consult DataCite documentation for schema details
