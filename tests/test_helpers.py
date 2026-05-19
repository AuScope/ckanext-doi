#!/usr/bin/env python3
# encoding: utf-8
#
# This file is part of ckanext-doi
# Created by the Natural History Museum in London, UK

import pytest

from ckanext.doi.lib.helpers import get_package_landing_url


PACKAGE_ID = '919379ef-ea08-4a5f-b370-7845e24117b4'


class TestGetPackageLandingUrl:
    """Tests for the get_package_landing_url helper."""

    @pytest.mark.ckan_config('ckan.site_url', 'https://data.example.org')
    def test_default_prefix_produces_dataset_route(self):
        url = get_package_landing_url(PACKAGE_ID)
        assert url == f'https://data.example.org/dataset/{PACKAGE_ID}'

    @pytest.mark.ckan_config('ckan.site_url', 'https://data.example.org')
    @pytest.mark.ckan_config('ckanext.doi.package_url_prefix', 'instrument')
    def test_custom_prefix_produces_instrument_route(self):
        url = get_package_landing_url(PACKAGE_ID)
        assert url == f'https://data.example.org/instrument/{PACKAGE_ID}'

    @pytest.mark.ckan_config('ckan.site_url', 'https://data.example.org/')
    def test_trailing_slash_on_site_url_is_stripped(self):
        url = get_package_landing_url(PACKAGE_ID)
        assert '//' not in url.replace('https://', '')
        assert url == f'https://data.example.org/dataset/{PACKAGE_ID}'

    @pytest.mark.ckan_config('ckan.site_url', 'https://data.example.org')
    @pytest.mark.ckan_config('ckanext.doi.package_url_prefix', '/instrument/')
    def test_prefix_with_leading_and_trailing_slashes_is_cleaned(self):
        url = get_package_landing_url(PACKAGE_ID)
        assert '//' not in url.replace('https://', '')
        assert url == f'https://data.example.org/instrument/{PACKAGE_ID}'

    @pytest.mark.ckan_config('ckan.site_url', 'https://data.example.org')
    @pytest.mark.ckan_config('ckanext.doi.package_url_prefix', 'instrument/')
    def test_prefix_with_trailing_slash_is_cleaned(self):
        url = get_package_landing_url(PACKAGE_ID)
        assert url == f'https://data.example.org/instrument/{PACKAGE_ID}'

    @pytest.mark.ckan_config('ckan.site_url', 'https://data.example.org')
    @pytest.mark.ckan_config('ckanext.doi.package_url_prefix', '/instrument')
    def test_prefix_with_leading_slash_is_cleaned(self):
        url = get_package_landing_url(PACKAGE_ID)
        assert url == f'https://data.example.org/instrument/{PACKAGE_ID}'

    @pytest.mark.ckan_config('ckan.site_url', 'https://data.example.org')
    @pytest.mark.ckan_config('ckanext.doi.package_url_prefix', 'dataset')
    def test_explicit_default_prefix_matches_implicit_default(self):
        url = get_package_landing_url(PACKAGE_ID)
        assert url == f'https://data.example.org/dataset/{PACKAGE_ID}'
