# Quick Configuration Guide for DataCite 4.5 + PIDINST

## Minimal Configuration (Instrument Registry)

Add these to your CKAN configuration file (e.g., `/etc/ckan/default/production.ini`):

```ini
# ============================================================================
# DataCite DOI Configuration for PIDINST Instrument Registry
# ============================================================================

# Required: DataCite Account Credentials
ckanext.doi.account_name = YOUR_REPOSITORY_ACCOUNT_NAME
ckanext.doi.account_password = YOUR_PASSWORD
ckanext.doi.prefix = 10.XXXX

# Required: Publisher Information
ckanext.doi.publisher = AuScope Instrument Registry

# Required: Test/Production Mode
ckanext.doi.test_mode = True

# New: DataCite Schema Version (default: 4.5)
ckanext.doi.datacite_schema_version = 4.5

# New: Resource Type (default: Instrument)
ckanext.doi.resource_type = Instrument

# Optional: Site URLs
ckanext.doi.site_url = https://instruments.auscope.org.au
ckanext.doi.site_title = AuScope Instrument Registry
```

## Configuration Options Reference

| Option                                | Required | Default         | Description                      | Values              |
| ------------------------------------- | -------- | --------------- | -------------------------------- | ------------------- |
| `ckanext.doi.account_name`            | ✅       | -               | DataCite Repository account name | String              |
| `ckanext.doi.account_password`        | ✅       | -               | DataCite Repository password     | String              |
| `ckanext.doi.prefix`                  | ✅       | -               | DOI prefix from DataCite account | e.g., `10.1234`     |
| `ckanext.doi.publisher`               | ✅       | -               | Publishing institution name      | String              |
| `ckanext.doi.test_mode`               | ✅       | `True`          | Enable test/production mode      | `True`/`False`      |
| `ckanext.doi.datacite_schema_version` | ❌       | `4.5`           | DataCite schema version          | `4.3`, `4.4`, `4.5` |
| `ckanext.doi.resource_type`           | ❌       | `Instrument`    | Default resourceTypeGeneral      | See below           |
| `ckanext.doi.site_url`                | ❌       | `ckan.site_url` | Landing page base URL            | URL                 |
| `ckanext.doi.site_title`              | ❌       | -               | Site title for citations         | String              |

## Resource Type Values

Valid values for `ckanext.doi.resource_type` (DataCite 4.5):

- `Instrument` ← Use for instrument registries (PIDINST)
- `Dataset` ← Use for traditional data repositories
- `PhysicalObject` ← Use for sample repositories
- `Software`
- `Workflow`
- `Service`
- `Model`
- `Image`
- `Text`
- `Collection`
- `Other`

See [DataCite Resource Type General](https://datacite-metadata-schema.readthedocs.io/en/4.5/properties/resourcetype/#resource-type-general) for full list.

## Deployment Scenarios

### Scenario 1: Pure Instrument Registry (PIDINST)

```ini
ckanext.doi.publisher = AuScope Instrument Registry
ckanext.doi.datacite_schema_version = 4.5
ckanext.doi.resource_type = Instrument
```

Datasets MUST have:

- `owner` field (mapped to creators)
- `manufacturer` field (mapped to contributors)

### Scenario 2: Traditional Data Repository

```ini
ckanext.doi.publisher = Data Archive Center
ckanext.doi.datacite_schema_version = 4.5
ckanext.doi.resource_type = Dataset
```

Datasets MUST have:

- `author` field (mapped to creators)

### Scenario 3: Mixed Repository (Instruments + Datasets)

```ini
ckanext.doi.publisher = Research Data Portal
ckanext.doi.datacite_schema_version = 4.5
ckanext.doi.resource_type = Instrument  # default
```

Then implement custom logic via `IDoi` plugin interface to set resource type per-dataset:

```python
class MyPlugin(plugins.SingletonPlugin):
    plugins.implements(IDoi)

    def build_xml_dict(self, metadata_dict, xml_dict):
        # Check dataset type and set accordingly
        if metadata_dict.get('resourceType') == 'dataset':
            xml_dict['types']['resourceTypeGeneral'] = 'Dataset'
        elif metadata_dict.get('resourceType') == 'instrument':
            xml_dict['types']['resourceTypeGeneral'] = 'Instrument'
        return xml_dict
```

### Scenario 4: Sample Repository (IGSN)

```ini
ckanext.doi.publisher = Sample Repository
ckanext.doi.datacite_schema_version = 4.5
ckanext.doi.resource_type = PhysicalObject
ckan.plugins = ... igsn_theme doi
```

## Testing Configuration

Use separate credentials for test and production:

### Test Mode (development.ini)

```ini
ckanext.doi.test_mode = True
ckanext.doi.account_name = YOUR_TEST_ACCOUNT
ckanext.doi.account_password = YOUR_TEST_PASSWORD
ckanext.doi.prefix = 10.XXXX  # Test prefix
```

### Production Mode (production.ini)

```ini
ckanext.doi.test_mode = False
ckanext.doi.account_name = YOUR_PRODUCTION_ACCOUNT
ckanext.doi.account_password = YOUR_PRODUCTION_PASSWORD
ckanext.doi.prefix = 10.YYYY  # Production prefix
```

⚠️ **Important**: Test DOIs will NOT resolve on doi.org. They can only be viewed at:

- DataCite Fabrica test: https://doi.test.datacite.org
- Test API: https://mds.test.datacite.org

## Verification

After configuration, verify settings:

```bash
# Check configuration is loaded
ckan -c /etc/ckan/default/production.ini config-tool ckanext.doi

# Test DOI generation
ckan -c /etc/ckan/default/production.ini doi update-doi YOUR_PACKAGE_ID

# Check Python library imports
python -c "from datacite import schema45; print('Schema 4.5 available')"
```

## Troubleshooting

### "schema45 module not found"

```bash
pip install --upgrade 'datacite>=1.1.3'
```

### "Instrument not valid resourceTypeGeneral"

Ensure `ckanext.doi.datacite_schema_version = 4.5`

### "Required field creators cannot be None"

Check that datasets have either:

- `owner` field (for PIDINST), or
- `author` field (for legacy datasets)

## Migration Checklist

- [ ] Update dependencies: `pip install --upgrade ckanext-doi`
- [ ] Add new config options to `.ini` file
- [ ] Set test_mode appropriately
- [ ] Verify DataCite credentials
- [ ] Test with sample dataset: `ckan doi update-doi test-package`
- [ ] Check generated XML: View in DataCite Fabrica
- [ ] Update existing DOIs: `ckan doi update-doi` (all packages)
- [ ] Switch test_mode to False for production
- [ ] Monitor error logs for any issues

## Support

For detailed migration instructions, see `MIGRATION_DATACITE_45.md`.
