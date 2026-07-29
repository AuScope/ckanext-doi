# Changelog

## v4.0.0 (UNRELEASED)

### Fixes

- Parse composite CKAN fields as JSON, including `null`, `true`, and `false`,
  while retaining support for legacy Python-repr values.
- Prevent null composite values from being emitted into DataCite string fields,
  and preserve the package permalink when alternate identifiers are malformed.
- Map PIDINST funder identifier types to the constrained DataCite
  `funderIdentifierType` values without changing owner or manufacturer schemes.
- Keep CKAN package saves successful when DataCite validation or API calls fail,
  log the full error, and avoid minting a DOI until its metadata is accepted.
- Log optional metadata extraction failures at warning level.

### Repair tooling

- Add `--mint-unpublished` to `doi update-doi` so locally allocated but
  unregistered DOIs can be repaired.
- Add `--dry-run` metadata validation and change reporting without DataCite
  POSTs or DOI minting.
- Continue bulk repairs after individual record failures and print updated,
  skipped, and failed totals.

### Breaking Changes

- **MAJOR**: Upgraded from DataCite Metadata Schema v4.3 to v4.5
- Changed default `resourceTypeGeneral` from "Dataset" to "Instrument" for PIDINST instrument registries
- Updated datacite Python library dependency from 1.1.2 to >=1.1.3

### Features

- **PIDINST Support**: Implemented PIDINST (Persistent Identification of Instruments) schema mapping
  - Map `owner` field to DataCite creators (instrument owners/responsible organizations)
  - Map `manufacturer` field to DataCite contributors with Producer role
  - Support for `alternate_identifier_obj` (serial numbers, inventory numbers)
  - Support for `related_identifier_obj` (enhanced relationship types)
- **Configurable Schema Version**: New config option `ckanext.doi.datacite_schema_version` (default: 4.5)
- **Configurable Resource Type**: New config option `ckanext.doi.resource_type` (default: Instrument)
- **DataCite 4.5 Features**:
  - Native "Instrument" resourceTypeGeneral support
  - Wikidata identifier support in fundingReferences (no longer restricted)
  - Enhanced identifier and relation type support

### Backwards Compatibility

- **Legacy Dataset Support**: Automatic fallback to `author` field when `owner`/`manufacturer` not present
- **Existing DOIs**: All existing DOIs remain valid; metadata can be updated via `doi update-doi` command
- **Mixed Deployments**: Support for both instrument registries and data repositories in same CKAN instance

### Documentation

- Added comprehensive `MIGRATION_DATACITE_45.md` migration guide
- Updated README with PIDINST field mapping tables
- Updated configuration documentation with new options
- Enhanced code documentation in `metadata.py` with PIDINST mapping details

### Changed

- Updated `build_metadata_dict()` to prioritize PIDINST fields over legacy dataset fields
- Updated `build_xml_dict()` to support configurable schema version and resource type
- Modified imports from `schema43` to `schema45` throughout codebase
- Improved error handling for missing PIDINST fields with graceful fallbacks

### See Also

- [DataCite 4.5 Schema Documentation](https://schema.datacite.org/meta/kernel-4.5/)
- [PIDINST Schema](https://github.com/rdawg-pidinst/schema)

---

## v3.1.12 (2024-02-13)

### Fix

- correct casing for schemeURI property

## v3.1.11 (2024-01-15)

### Docs

- update readme to clarify wording, fix links, and fix whitespace

### Chores/Misc

- add build section to read the docs config

## v3.1.10 (2023-12-04)

### Fix

- update ckantools to patch bug with get_setting
- add helper to correctly determine test mode status

### Style

- use single quotes

### Chores/Misc

- add regex for version line in citation file
- add citation.cff to list of files with version
- add contributing guidelines
- add code of conduct
- add citation file
- update support.md links

## v3.1.9 (2023-09-25)

### Fix

- add new functions to support CKAN 2.10

### Docs

- update docs with updated test info

### Tests

- add tests to confirm plugin CKAN 2.9/2.10 differences work ok
- move with_doi_table fixture to conftest so others can use
- add testing on ckan 2.10.x as well as 2.9.x

### CI System(s)

- switch back to a single workflow test file but with multiple jobs
- run CI tests against ckan 2.9.x and 2.10.x

## v3.1.8 (2023-07-17)

### Docs

- update logos

## v3.1.7 (2023-04-11)

### Build System(s)

- fix postgres not loading when running tests in docker

### Chores/Misc

- add action to sync branches when commits are pushed to main

## v3.1.6 (2023-02-20)

### Docs

- fix api docs generation script

### Chores/Misc

- small fixes to align with other extensions

## v3.1.5 (2023-01-31)

### Docs

- **readme**: change logo url from blob to raw

## v3.1.4 (2023-01-31)

### Docs

- **readme**: direct link to logo in readme
- **readme**: fix github actions badge

## v3.1.3 (2023-01-30)

### Build System(s)

- **docker**: use 'latest' tag for test docker image

## v3.1.2 (2022-12-12)

### Style

- change quotes in setup.py to single quotes

### Build System(s)

- include top-level data files in theme folder
- add package data

## v3.1.1 (2022-12-01)

### Docs

- **readme**: format test section
- **readme**: update installation steps, add test mode details

## v3.1.0 (2022-11-28)

### Fix

- change case on plugin name
- unpin ckantools version

### Docs

- fix markdown-include references
- add section delimiter

### Style

- apply formatting changes

### Build System(s)

- set changelog generation to incremental
- pin ckantools minor version
- add include-markdown plugin to mkdocs

### CI System(s)

- add cz_nhm dependency
- **commitizen**: fix message template
- add pypi release action

### Chores/Misc

- clear old changelog
- use cz_nhm commitizen config
- improve commitizen message template
- move cz config into separate file
- standardise package files

## v3.0.7 (2022-06-20)

## v3.0.6 (2022-05-23)

## v3.0.5 (2022-05-17)

## v3.0.4 (2022-03-03)

## v3.0.3 (2021-04-15)

## v3.0.1 (2021-04-01)

## v3.0.0 (2021-03-09)

## v2.0.2 (2020-11-25)

## v1.0.0-alpha (2019-07-23)

## v0.0.3 (2018-05-08)

## v0.0.2 (2018-01-09)

## v0.0.1 (2017-08-24)
