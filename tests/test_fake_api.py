#!/usr/bin/env python3
# encoding: utf-8
#
# This file is part of ckanext-doi
# Created by the Natural History Museum in London, UK

import pytest
from unittest.mock import patch, MagicMock

from ckanext.doi.lib.api import FakeDataciteClient, get_client, DataciteClient
from ckanext.doi.model.crud import DOIQuery
from ckanext.doi.lib import datacite_compat


@pytest.mark.ckan_config('ckanext.doi.prefix', '10.5555')
@pytest.mark.ckan_config('ckan.site_url', 'http://localhost:5000')
class TestFakeDataciteClient:
    """Test the FakeDataciteClient class for dev mode."""

    def test_init(self):
        """Test that FakeDataciteClient initializes correctly."""
        client = FakeDataciteClient()
        assert client.prefix == '10.5555'
        assert isinstance(client._metadata_store, dict)
        assert isinstance(client._doi_store, dict)
        assert len(client._metadata_store) == 0
        assert len(client._doi_store) == 0

    def test_get_prefix_from_config(self):
        """Test that get_prefix retrieves the configured prefix."""
        prefix = FakeDataciteClient.get_prefix()
        assert prefix == '10.5555'

    @pytest.mark.ckan_config('ckanext.doi.prefix', None)
    def test_get_prefix_default_when_none(self):
        """Test that get_prefix uses default when config is None."""
        prefix = FakeDataciteClient.get_prefix()
        assert prefix == '10.5555'

    @pytest.mark.ckan_config('ckanext.doi.prefix', '10.5072')
    def test_get_prefix_deprecated_warning(self):
        """Test that deprecated prefix triggers warning and uses fake prefix."""
        prefix = FakeDataciteClient.get_prefix()
        assert prefix == '10.5555'

    def test_generate_doi_unique(self):
        """Test that generate_doi creates a unique DOI."""
        client = FakeDataciteClient()
        
        with patch('ckanext.doi.model.crud.DOIQuery.read_doi', return_value=None):
            doi = client.generate_doi()
            
            assert doi.startswith('10.5555/')
            assert len(doi.split('/')[-1]) == 8
            assert doi not in client._doi_store

    def test_generate_doi_avoids_duplicates(self):
        """Test that generate_doi avoids creating duplicate DOIs."""
        client = FakeDataciteClient()
        
        # Generate first DOI
        with patch('ckanext.doi.model.crud.DOIQuery.read_doi', return_value=None):
            doi1 = client.generate_doi()
            client._doi_store[doi1] = 'http://localhost:5000/dataset/test'
            
            # Generate second DOI - should be different
            doi2 = client.generate_doi()
            
            assert doi1 != doi2
            assert doi2 not in client._doi_store

    def test_generate_doi_retries_on_collision(self):
        """Test that generate_doi retries when DOI already exists."""
        client = FakeDataciteClient()
        
        # Simulate collision on first attempt
        mock_read = MagicMock(side_effect=[
            MagicMock(identifier='10.5555/abc12345'),  # First attempt - collision
            None,  # Second attempt - success
        ])
        
        with patch('ckanext.doi.model.crud.DOIQuery.read_doi', mock_read):
            doi = client.generate_doi()
            
            assert doi.startswith('10.5555/')
            assert len(doi.split('/')[-1]) == 8

    def test_generate_doi_raises_after_max_attempts(self):
        """Test that generate_doi raises exception after max retry attempts."""
        client = FakeDataciteClient()
        
        # Simulate collision on all attempts
        with patch('ckanext.doi.model.crud.DOIQuery.read_doi', return_value=MagicMock()):
            with pytest.raises(Exception, match='Failed to generate a fake DOI'):
                client.generate_doi()

    def test_mint_doi(self):
        """Test that mint_doi stores DOI without making API calls."""
        client = FakeDataciteClient()
        doi = '10.5555/testdoi1'
        package_id = 'test-package-123'
        
        with patch('ckanext.doi.model.crud.DOIQuery.read_doi', return_value=None):
            with patch('ckanext.doi.model.crud.DOIQuery.read_package', return_value=None):
                with patch('ckanext.doi.model.crud.DOIQuery.create') as mock_create:
                    with patch('ckanext.doi.model.crud.DOIQuery.update_doi') as mock_update:
                        client.mint_doi(doi, package_id)
                        
                        # Check DOI was stored in memory
                        assert doi in client._doi_store
                        assert client._doi_store[doi] == 'http://localhost:5000/dataset/test-package-123'
                        
                        # Check database operations were called
                        mock_create.assert_called_once()
                        mock_update.assert_called_once()

    def test_mint_doi_with_trailing_slash(self):
        """Test mint_doi handles site URL with trailing slash correctly."""
        client = FakeDataciteClient()
        doi = '10.5555/testdoi2'
        package_id = 'test-package-456'
        
        with patch('ckan.plugins.toolkit.config.get') as mock_config:
            mock_config.side_effect = lambda key, default=None: {
                'ckanext.doi.prefix': '10.5555',
                'ckan.site_url': 'http://localhost:5000/',
            }.get(key, default)
            
            with patch('ckanext.doi.model.crud.DOIQuery.read_doi', return_value=None):
                with patch('ckanext.doi.model.crud.DOIQuery.read_package', return_value=None):
                    with patch('ckanext.doi.model.crud.DOIQuery.create'):
                        with patch('ckanext.doi.model.crud.DOIQuery.update_doi'):
                            client.mint_doi(doi, package_id)
                            
                            # URL should not have double slash
                            assert client._doi_store[doi] == 'http://localhost:5000/dataset/test-package-456'

    def test_set_metadata(self):
        """Test that set_metadata stores metadata without making API calls."""
        client = FakeDataciteClient()
        doi = '10.5555/testdoi3'
        xml_dict = {
            'types': {'resourceTypeGeneral': 'Dataset'},
            'titles': [{'title': 'Test Dataset'}],
            'publisher': {'name': 'Test Publisher'},
            'publicationYear': '2024',
            'creators': [{'name': 'Test Creator'}],
        }
        
        client.set_metadata(doi, xml_dict)
        
        assert doi in client._metadata_store
        assert client._metadata_store[doi] is not None
        
        # Verify DOI was added to xml_dict
        assert xml_dict['doi'] == doi

    def test_get_metadata_exists(self):
        """Test get_metadata retrieves stored metadata."""
        client = FakeDataciteClient()
        doi = '10.5555/testdoi4'
        xml_dict = {
            'types': {'resourceTypeGeneral': 'Dataset'},
            'titles': [{'title': 'Test Dataset'}],
            'publisher': {'name': 'Test Publisher'},
            'publicationYear': '2024',
            'creators': [{'name': 'Test Creator'}],
            'doi': doi,
        }
        
        # Store metadata first
        client.set_metadata(doi, xml_dict)
        
        # Retrieve it
        metadata = client.get_metadata(doi)
        
        assert metadata is not None
        assert 'Test Dataset' in metadata

    def test_get_metadata_not_exists(self):
        """Test get_metadata returns None for non-existent DOI."""
        client = FakeDataciteClient()
        doi = '10.5555/nonexistent'
        
        metadata = client.get_metadata(doi)
        
        assert metadata is None

    def test_check_for_update_no_existing_metadata(self):
        """Test check_for_update returns False when no metadata exists."""
        client = FakeDataciteClient()
        doi = '10.5555/testdoi5'
        xml_dict = {
            'types': {'resourceTypeGeneral': 'Dataset'},
            'titles': [{'title': 'Test Dataset'}],
            'publisher': 'Test Publisher',
            'publicationYear': '2024',
            'creators': [{'name': 'Test Creator'}],
            'dates': [{'date': '2024-01-01', 'dateType': 'Issued'}],
        }
        
        result = client.check_for_update(doi, xml_dict)
        
        assert result is False

    def test_check_for_update_same_metadata(self):
        """Test check_for_update returns True when metadata is unchanged."""
        client = FakeDataciteClient()
        doi = '10.5555/testdoi6'
        xml_dict = {
            'types': {'resourceTypeGeneral': 'Dataset'},
            'titles': [{'title': 'Test Dataset'}],
            'publisher': {'name': 'Test Publisher'},
            'publicationYear': '2024',
            'creators': [{'name': 'Test Creator'}],
            'dates': [{'date': '2024-01-01', 'dateType': 'Issued'}],
        }
        
        # Store initial metadata
        client.set_metadata(doi, xml_dict.copy())
        
        # Check for update with same metadata
        result = client.check_for_update(doi, xml_dict)
        
        assert result is True

    def test_check_for_update_different_metadata(self):
        """Test check_for_update returns False when metadata differs."""
        client = FakeDataciteClient()
        doi = '10.5555/testdoi7'
        xml_dict_old = {
            'types': {'resourceTypeGeneral': 'Dataset'},
            'titles': [{'title': 'Old Title'}],
            'publisher': {'name': 'Test Publisher'},
            'publicationYear': '2024',
            'creators': [{'name': 'Test Creator'}],
            'dates': [{'date': '2024-01-01', 'dateType': 'Issued'}],
        }
        xml_dict_new = {
            'types': {'resourceTypeGeneral': 'Dataset'},
            'titles': [{'title': 'New Title'}],
            'publisher': {'name': 'Test Publisher'},
            'publicationYear': '2024',
            'creators': [{'name': 'Test Creator'}],
            'dates': [{'date': '2024-01-01', 'dateType': 'Issued'}],
        }
        
        # Store old metadata
        client.set_metadata(doi, xml_dict_old)
        
        # Check for update with different metadata
        result = client.check_for_update(doi, xml_dict_new)
        
        assert result is False
@pytest.mark.ckan_config('ckanext.doi.prefix', '10.5555')
class TestGetClientFactory:
    """Test the get_client factory function."""

    @pytest.mark.ckan_config('ckanext.doi.dev_mode', 'True')
    def test_get_client_returns_fake_in_dev_mode(self):
        """Test that get_client returns FakeDataciteClient when dev mode is enabled."""
        client = get_client()
        
        assert isinstance(client, FakeDataciteClient)
        assert not isinstance(client, DataciteClient)

    @pytest.mark.ckan_config('ckanext.doi.dev_mode', 'False')
    @pytest.mark.ckan_config('ckanext.doi.account_name', 'test_user')
    @pytest.mark.ckan_config('ckanext.doi.account_password', 'test_pass')
    def test_get_client_returns_real_when_not_dev_mode(self):
        """Test that get_client returns DataciteClient when dev mode is disabled."""
        client = get_client()
        
        assert isinstance(client, DataciteClient)
        assert not isinstance(client, FakeDataciteClient)

    @pytest.mark.ckan_config('ckanext.doi.dev_mode', None)
    @pytest.mark.ckan_config('ckanext.doi.account_name', 'test_user')
    @pytest.mark.ckan_config('ckanext.doi.account_password', 'test_pass')
    def test_get_client_defaults_to_real_when_no_config(self):
        """Test that get_client defaults to DataciteClient when dev_mode is not configured."""
        client = get_client()
        
        assert isinstance(client, DataciteClient)


@pytest.mark.ckan_config('ckanext.doi.prefix', '10.5555')
@pytest.mark.ckan_config('ckan.site_url', 'http://localhost:5000')
class TestFakeClientIntegration:
    """Integration tests for the fake client with the full workflow."""

    def test_full_doi_workflow(self):
        """Test the complete fake DOI workflow: generate, mint, set metadata."""
        client = FakeDataciteClient()
        
        # Step 1: Generate a DOI
        with patch('ckanext.doi.model.crud.DOIQuery.read_doi', return_value=None):
            doi = client.generate_doi()
            assert doi.startswith('10.5555/')
        
        # Step 2: Mint the DOI
        package_id = 'integration-test-package'
        with patch('ckanext.doi.model.crud.DOIQuery.read_doi', return_value=None):
            with patch('ckanext.doi.model.crud.DOIQuery.read_package', return_value=None):
                with patch('ckanext.doi.model.crud.DOIQuery.create'):
                    with patch('ckanext.doi.model.crud.DOIQuery.update_doi'):
                        client.mint_doi(doi, package_id)
        
        assert doi in client._doi_store
        
        # Step 3: Set metadata
        xml_dict = {
            'types': {'resourceTypeGeneral': 'Dataset'},
            'titles': [{'title': 'Integration Test Dataset'}],
            'publisher': {'name': 'Test Publisher'},
            'publicationYear': '2024',
            'creators': [{'name': 'Test Creator'}],
            'dates': [{'date': '2024-01-01', 'dateType': 'Issued'}],
        }
        client.set_metadata(doi, xml_dict)
        
        assert doi in client._metadata_store
        
        # Step 4: Retrieve metadata
        metadata = client.get_metadata(doi)
        assert metadata is not None
        
        # Step 5: Check for updates
        same = client.check_for_update(doi, xml_dict)
        assert same is True
