"""Integration test: mint a draft DOI on DataCite, verify fields, clean up.

Requires a ``tests/.env`` file with real DataCite credentials.
If the file is absent or incomplete the test is skipped, not failed.
Run with::

    pytest tests/test_datacite_integration.py -v -s --log-cli-level=INFO
"""

import logging
import random
import string
from pathlib import Path
from unittest.mock import patch

import pytest
import xmltodict
from datacite import DataCiteMDSClient
from datacite.errors import DataCiteError, DataCiteNotFoundError

from ckan.plugins import toolkit
from ckanext.doi.lib import datacite_compat
from ckanext.doi.lib.metadata import build_metadata_dict, build_xml_dict

log = logging.getLogger(__name__)

_TESTS_DIR = Path(__file__).parent
_ENV_FILE = _TESTS_DIR / '.env'

_REQUIRED_VARS = [
    'CKANEXT__DOI__ACCOUNT_NAME',
    'CKANEXT__DOI__ACCOUNT_PASSWORD',
    'CKANEXT__DOI__PREFIX',
    'CKANEXT__DOI__PUBLISHER',
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_dotenv(path):
    """Minimal safe .env file parser (no dependency on python-dotenv)."""
    env = {}
    if not path.is_file():
        return env
    with open(path, encoding='utf-8') as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith('#'):
                continue
            key, sep, value = line.partition('=')
            if not sep:
                continue
            key = key.strip()
            value = value.strip()
            # handle quoted values
            if len(value) >= 2 and value[0] in ('"', "'") and value[-1] == value[0]:
                value = value[1:-1]
            else:
                # strip trailing inline comment (preceded by whitespace)
                for i, ch in enumerate(value):
                    if ch == '#' and i > 0 and value[i - 1] in (' ', '\t'):
                        value = value[:i].rstrip()
                        break
            if key:
                env[key] = value
    return env


def _env_to_ckan_key(env_key):
    """``CKANEXT__DOI__FOO`` -> ``ckanext.doi.foo``."""
    return env_key.lower().replace('__', '.')


def _datacite_config():
    """Load ``tests/.env`` and return ``(config_dict, skip_reason | None)``."""
    if not _ENV_FILE.is_file():
        return None, (
            f'{_ENV_FILE} not found -- copy .env.example to .env '
            f'and fill in your DataCite credentials to run this test'
        )
    raw = _load_dotenv(_ENV_FILE)
    missing = [k for k in _REQUIRED_VARS if not raw.get(k)]
    if missing:
        return None, f'Missing in {_ENV_FILE.name}: {", ".join(missing)}'

    cfg = {_env_to_ckan_key(k): v for k, v in raw.items()}

    if cfg.get('ckanext.doi.dev_mode', 'false').lower() in ('true', '1', 'yes'):
        return None, 'dev_mode is enabled; skipping real DataCite integration test'

    return cfg, None


def _xml_text(node):
    """Extract text content from an xmltodict node (str or ``{#text: ...}``)."""
    if isinstance(node, str):
        return node
    if isinstance(node, dict):
        return node.get('#text', str(node))
    return str(node)


# Representative PIDINST instrument package with a Coverage date.
_TEST_PKG = {
    'id': 'datacite-integration-test',
    'name': 'integration-test-seismometer',
    'title': 'Integration Test Seismometer',
    'type': 'instrument',
    'state': 'active',
    'private': False,
    'manufacturer': [{'manufacturer_name': 'Test Manufacturer Inc.'}],
    'owner': [
        {
            'owner_name': 'Integration Test University',
            'owner_contact': 'lab@test-university.example',
            'owner_relationship_type': 'HostingInstitution',
        }
    ],
    'date': [
        {'date_value': '2025-01-01/2025-12-31', 'date_type': 'Coverage'},
    ],
    'description': 'Integration test instrument for DataCite draft verification',
    'metadata_created': '2025-01-15T10:00:00',
    'metadata_modified': '2025-01-15T10:00:00',
    'tags': [{'name': 'integration-test'}],
    'resources': [],
}


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestDataciteDraftRoundTrip:
    """Mint a draft DOI on DataCite, read it back, verify key fields, delete."""

    def test_mint_verify_delete(self):
        # -- config / skip logic --
        cfg, skip_reason = _datacite_config()
        if skip_reason:
            pytest.skip(skip_reason)

        prefix = cfg['ckanext.doi.prefix']
        publisher = cfg['ckanext.doi.publisher']
        test_mode = cfg.get('ckanext.doi.test_mode', 'true').lower() in (
            'true',
            '1',
            'yes',
        )

        # random DOI suffix (same pattern as DataciteClient.generate_doi)
        suffix = ''.join(
            random.choice(string.ascii_lowercase + string.digits) for _ in range(8)
        )
        doi = f'{prefix}/{suffix}'

        metadata_dict = None
        xml_dict = None
        xml_doc = None
        mds = None

        try:
            # -- build metadata through the real pipeline --
            config_patch = {
                'ckanext.doi.publisher': publisher,
                'ckan.site_url': cfg.get(
                    'ckan.site_url', 'https://integration-test.example.com'
                ),
            }
            with patch.dict(toolkit.config, config_patch):
                metadata_dict = build_metadata_dict(_TEST_PKG)
                xml_dict = build_xml_dict(metadata_dict)

            xml_dict['doi'] = doi
            datacite_compat.validator.validate(xml_dict)
            xml_doc = datacite_compat.tostring(xml_dict, verbose=True)

            # -- create MDS client and post metadata (creates draft DOI) --
            client_kw = dict(
                username=cfg['ckanext.doi.account_name'],
                password=cfg['ckanext.doi.account_password'],
                prefix=prefix,
                test_mode=test_mode,
            )
            if test_mode:
                client_kw['url'] = 'https://mds.test.datacite.org'
            mds = DataCiteMDSClient(**client_kw)

            log.info('Posting metadata for draft DOI %s (test_mode=%s)', doi, test_mode)
            mds.metadata_post(xml_doc)

            # -- fetch back and parse --
            fetched_xml = mds.metadata_get(doi)
            assert fetched_xml, f'metadata_get returned empty for {doi}'

            res = xmltodict.parse(fetched_xml).get('resource', {})

            # -- assertions --
            # Title
            title_node = res.get('titles', {}).get('title', '')
            titles = title_node if isinstance(title_node, list) else [title_node]
            assert any(
                'Integration Test Seismometer' in _xml_text(t) for t in titles
            ), f'Title mismatch: {titles}'

            # Publisher
            assert publisher.lower() in _xml_text(
                res.get('publisher', '')
            ).lower(), f'Publisher mismatch: {res.get("publisher")}'

            # Resource type
            rt = res.get('resourceType', {})
            assert (
                rt.get('@resourceTypeGeneral') == 'Instrument'
            ), f'resourceTypeGeneral mismatch: {rt}'

            # Coverage date
            date_nodes = res.get('dates', {}).get('date', [])
            if isinstance(date_nodes, dict):
                date_nodes = [date_nodes]
            coverage = [d for d in date_nodes if d.get('@dateType') == 'Coverage']
            assert coverage, f'No Coverage date found in {date_nodes}'
            assert '2025-01-01/2025-12-31' in _xml_text(
                coverage[0]
            ), f'Coverage value mismatch: {coverage}'

            log.info('All assertions passed for DOI %s', doi)

        except Exception:
            log.error('=== DataCite integration test failure debug ===')
            log.error('DOI attempted: %s', doi)
            if metadata_dict:
                log.error('metadata_dict: %s', metadata_dict)
            if xml_dict:
                log.error('xml_dict: %s', xml_dict)
            if xml_doc:
                doc = (
                    xml_doc.decode('utf-8', errors='replace')
                    if isinstance(xml_doc, bytes)
                    else xml_doc
                )
                log.error('Generated XML:\n%s', doc)
            raise

        finally:
            if mds is not None:
                try:
                    mds.metadata_delete(doi)
                    log.info('Cleaned up draft DOI: %s', doi)
                except DataCiteNotFoundError:
                    log.info('DOI %s not found on DataCite (already clean)', doi)
                except DataCiteError as cleanup_err:
                    log.warning(
                        'Cleanup failed for DOI %s -- manual deletion may be needed: %s',
                        doi,
                        cleanup_err,
                    )
