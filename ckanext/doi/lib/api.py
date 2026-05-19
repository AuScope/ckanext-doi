#!/usr/bin/env python3
# encoding: utf-8
#
# This file is part of ckanext-doi
# Created by the Natural History Museum in London, UK

import string

import logging
import random
import xmltodict
from ckan.plugins import toolkit
from ckanext.doi.model.crud import DOIQuery
from datacite import DataCiteMDSClient
from datacite.errors import DataCiteError, DataCiteNotFoundError

from ckanext.doi.lib import datacite_compat
from datetime import datetime as dt

from ckanext.doi.lib.helpers import doi_test_mode, doi_dev_mode, get_package_landing_url

log = logging.getLogger(__name__)

DEPRECATED_TEST_PREFIX = '10.5072'


class DataciteClient:
    test_url = 'https://mds.test.datacite.org'

    def __init__(self):
        self.username = toolkit.config.get('ckanext.doi.account_name')
        self.password = toolkit.config.get('ckanext.doi.account_password')
        self._test_mode = None
        self.prefix = self.get_prefix()
        client_config = {
            'username': self.username,
            'password': self.password,
            'prefix': self.prefix,
            'test_mode': self.test_mode,
        }
        if self.test_mode:
            # temporary fix because datacite 1.0.1 isn't updated for the test prefix deprecation
            client_config['url'] = self.test_url
        self.client = DataCiteMDSClient(**client_config)

    @property
    def test_mode(self):
        """
        Whether to run in test mode.

        Defaults to true.
        :return: test mode enabled as boolean (true=enabled)
        """
        if self._test_mode is None:
            self._test_mode = doi_test_mode()
        return self._test_mode

    @classmethod
    def get_prefix(cls):
        """
        Get the prefix to use for DOIs.

        :return: config prefix setting
        """
        prefix = toolkit.config.get('ckanext.doi.prefix')
        if prefix is None:
            raise TypeError('You must set the ckanext.doi.prefix config value')
        if prefix == DEPRECATED_TEST_PREFIX:
            raise ValueError(
                f'The test prefix {DEPRECATED_TEST_PREFIX} has been retired; use a '
                f'prefix defined in your datacite test account'
            )
        return prefix

    def generate_doi(self):
        """
        Generate a new DOI which isn't currently in use.

        The database is checked for previous
        usage, as is Datacite itself. Use whatever value is retuned from this function quickly to
        avoid double use as this function uses no locking.
        :return: the full, unique DOI
        """
        # the list of valid characters is larger than just lowercase and the digits but we don't
        # need that many options and URLs with just alphanumeric characters in them are nicer. We
        # just use lowercase characters to avoid any issues with case being ignored
        valid_characters = string.ascii_lowercase + string.digits

        attempts = 5

        while attempts > 0:
            # generate a random 8 character identifier
            identifier = ''.join(random.choice(valid_characters) for _ in range(8))
            # form the doi using the prefix
            doi = f'{self.prefix}/{identifier}'

            if DOIQuery.read_doi(doi) is None:
                try:
                    self.client.metadata_get(doi)
                except DataCiteNotFoundError:
                    return doi
                except DataCiteError as e:
                    log.warning(
                        f'Error whilst checking new DOIs with DataCite. DOI: {doi}, '
                        f'error: {e}'
                    )
            attempts -= 1
        raise Exception('Failed to generate a DOI')

    def mint_doi(self, doi, package_id):
        """
        Mints the given DOI on datacite. Does not add metadata, just creates the DOI.

        :param doi: the doi (full, prefix and suffix)
        :param package_id: the id of the package this doi is for
        """

        # create the URL the DOI will point to, i.e. the package page
        permalink = get_package_landing_url(package_id)
        # mint the DOI
        self.client.doi_post(doi, permalink)
        if DOIQuery.read_doi(doi) is None and DOIQuery.read_package(package_id) is None:
            DOIQuery.create(doi, package_id)
        elif DOIQuery.read_doi(doi) is None:
            # in case this was previously attempted but no DOI was added
            DOIQuery.update_package(package_id, identifier=doi)
        DOIQuery.update_doi(doi, published=dt.now())

    def set_metadata(self, doi, xml_dict):
        """
        Update or create the metadata for a given DOI on datacite.

        :param doi: the DOI to update the metadata for
        :param xml_dict: the metadata as an xml dict (generated from build_xml_dict)
        :return:
        """
        xml_dict['doi'] = doi

        # Validate against the (extended) DataCite 4.7 JSON schema
        if doi.startswith('10.'):
            datacite_compat.validator.validate(xml_dict)

        xml_doc = datacite_compat.tostring(xml_dict)

        if toolkit.config.get('ckanext.doi.verbose_xml', 'false').lower() in (
            'true',
            '1',
            'yes',
        ):
            log.info('DataCite XML for %s:\n%s', doi, xml_doc)

        # create the metadata on datacite
        self.client.metadata_post(xml_doc)

    def get_metadata(self, doi):
        """
        Retrieve metadata for a given DOI on datacite.

        :param doi: the DOI for which to retrieve the stored metadata
        :return:
        """
        try:
            metadata = self.client.metadata_get(doi)
        except DataCiteNotFoundError:
            metadata = None
        return metadata

    def deactivate_doi(self, doi):
        """Move a Findable DOI to Registered state.

        Deletes metadata on DataCite so the DOI stops appearing in search/discovery
        but continues to resolve.  Safe to call if the DOI is already inactive.
        """
        try:
            self.client.metadata_delete(doi)
        except DataCiteNotFoundError:
            pass
        except DataCiteError as e:
            log.warning('DataCite deactivate failed for %s: %s', doi, e)

    def check_for_update(self, doi, xml_dict):
        """
        Compare generated xml_dict against the one already posted on datacite.

        :param doi: the DOI of the package
        :param xml_dict: the xml_dict generated by build_xml_dict
        :return: True if the two are the same, False if not
        """
        posted_xml = self.get_metadata(doi)
        if posted_xml is None or posted_xml.strip() == '':
            return False
        posted_xml_dict = dict(xmltodict.parse(posted_xml).get('resource', {}))
        new_xml_dict = dict(xmltodict.parse(datacite_compat.tostring(xml_dict))['resource'])
        if 'identifier' in posted_xml_dict:
            del posted_xml_dict['identifier']
        has_dates = 'dates' in posted_xml_dict and 'date' in posted_xml_dict['dates']
        if has_dates:
            posted_xml_dict['dates']['date'] = [
                d
                for d in posted_xml_dict['dates']['date']
                if d['@dateType'] != 'Updated'
            ]
            new_xml_dict['dates']['date'] = [
                d for d in new_xml_dict['dates']['date'] if d['@dateType'] != 'Updated'
            ]
            return posted_xml_dict == new_xml_dict
        else:
            # if the original doesn't have any dates, it's definitely different
            return False


class FakeDataciteClient:
    """
    Fake DataCite client for development purposes.
    
    This client simulates DOI minting operations without making actual API calls to DataCite.
    Useful for local development where localhost URLs are rejected by DataCite test repository.
    """

    def __init__(self):
        """Initialize the fake client with a fake prefix."""
        self.prefix = self.get_prefix()
        self._metadata_store = {}  # In-memory store for fake metadata
        self._doi_store = {}  # In-memory store for fake DOI URLs
        log.info('FakeDataciteClient initialized for dev mode')

    @classmethod
    def get_prefix(cls):
        """
        Get the prefix to use for DOIs.

        :return: config prefix setting
        """
        prefix = toolkit.config.get('ckanext.doi.prefix')
        if prefix is None:
            # Use a fake prefix for dev mode
            return '10.5555'
        if prefix == DEPRECATED_TEST_PREFIX:
            log.warning(
                f'The test prefix {DEPRECATED_TEST_PREFIX} has been retired; using fake prefix 10.5555'
            )
            return '10.5555'
        return prefix

    def generate_doi(self):
        """
        Generate a new fake DOI which isn't currently in use.

        The database is checked for previous usage.
        :return: the full, unique DOI
        """
        valid_characters = string.ascii_lowercase + string.digits
        attempts = 5

        while attempts > 0:
            # generate a random 8 character identifier
            identifier = ''.join(random.choice(valid_characters) for _ in range(8))
            # form the doi using the prefix
            doi = f'{self.prefix}/{identifier}'

            # Check if DOI exists in database or fake store
            if DOIQuery.read_doi(doi) is None and doi not in self._doi_store:
                log.info(f'Generated fake DOI: {doi}')
                return doi

            attempts -= 1
        raise Exception('Failed to generate a fake DOI')

    def mint_doi(self, doi, package_id):
        """
        Fake mints the given DOI. Does not make real API calls.

        :param doi: the doi (full, prefix and suffix)
        :param package_id: the id of the package this doi is for
        """
        # create the URL the DOI will point to, i.e. the package page
        permalink = get_package_landing_url(package_id)

        # Store the DOI->URL mapping in memory (fake minting)
        self._doi_store[doi] = permalink
        log.info(f'Fake minted DOI: {doi} -> {permalink}')
        
        # Update database records
        if DOIQuery.read_doi(doi) is None and DOIQuery.read_package(package_id) is None:
            DOIQuery.create(doi, package_id)
        elif DOIQuery.read_doi(doi) is None:
            # in case this was previously attempted but no DOI was added
            DOIQuery.update_package(package_id, identifier=doi)
        DOIQuery.update_doi(doi, published=dt.now())

    def set_metadata(self, doi, xml_dict):
        """
        Fake update or create the metadata for a given DOI.

        :param doi: the DOI to update the metadata for
        :param xml_dict: the metadata as an xml dict (generated from build_xml_dict)
        :return:
        """
        # Store metadata in memory instead of posting to DataCite
        xml_dict['doi'] = doi
        
        # Validate the schema if it's a real DOI pattern
        if doi.startswith('10.'):
            try:
                datacite_compat.validator.validate(xml_dict)
                log.info(f'Fake metadata validated for DOI: {doi}')
            except Exception as e:
                log.warning(f'Validation failed for fake DOI {doi}: {e}')
        
        # Store the metadata
        xml_doc = datacite_compat.tostring(xml_dict)
        self._metadata_store[doi] = xml_doc
        log.info(f'Fake metadata stored for DOI: {doi}')

    def get_metadata(self, doi):
        """
        Retrieve fake metadata for a given DOI.

        :param doi: the DOI for which to retrieve the stored metadata
        :return:
        """
        metadata = self._metadata_store.get(doi)
        if metadata:
            log.info(f'Retrieved fake metadata for DOI: {doi}')
        else:
            log.info(f'No fake metadata found for DOI: {doi}')
        return metadata

    def check_for_update(self, doi, xml_dict):
        """
        Compare generated xml_dict against the fake stored metadata.

        :param doi: the DOI of the package
        :param xml_dict: the xml_dict generated by build_xml_dict
        :return: True if the two are the same, False if not
        """
        posted_xml = self.get_metadata(doi)
        if posted_xml is None or posted_xml.strip() == '':
            return False
        
        posted_xml_dict = dict(xmltodict.parse(posted_xml).get('resource', {}))
        new_xml_dict = dict(xmltodict.parse(datacite_compat.tostring(xml_dict))['resource'])
        
        # Remove identifiers from both as they may differ
        if 'identifier' in posted_xml_dict:
            del posted_xml_dict['identifier']
        if 'identifier' in new_xml_dict:
            del new_xml_dict['identifier']
        
        # Handle dates - normalize and filter out 'Updated' dates
        has_dates = 'dates' in posted_xml_dict and 'date' in posted_xml_dict['dates']
        has_new_dates = 'dates' in new_xml_dict and 'date' in new_xml_dict['dates']
        
        if has_dates:
            # xmltodict returns a dict for single elements, list for multiple
            # Normalize to list
            posted_dates = posted_xml_dict['dates']['date']
            if isinstance(posted_dates, dict):
                posted_dates = [posted_dates]
            
            posted_xml_dict['dates']['date'] = [
                d
                for d in posted_dates
                if d.get('@dateType') != 'Updated'
            ]
        
        if has_new_dates:
            new_dates = new_xml_dict['dates']['date']
            if isinstance(new_dates, dict):
                new_dates = [new_dates]
            
            new_xml_dict['dates']['date'] = [
                d for d in new_dates if d.get('@dateType') != 'Updated'
            ]
        
        return posted_xml_dict == new_xml_dict


def get_client():
    """
    Factory function to get the appropriate DataCite client.
    
    Returns FakeDataciteClient if dev mode is enabled, otherwise returns DataciteClient.
    
    :return: DataciteClient or FakeDataciteClient instance
    """
    if doi_dev_mode():
        log.info('Using FakeDataciteClient for dev mode')
        return FakeDataciteClient()
    else:
        return DataciteClient()
