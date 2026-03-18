# !/usr/bin/env python
# encoding: utf-8
#
# This file is part of ckanext-doi
# Created by the Natural History Museum in London, UK

import re
from datetime import datetime

import dateutil.parser as parser
from ckan.plugins import toolkit
from ckantools.config import get_debug, get_setting

# Matches partial ISO 8601 dates: YYYY or YYYY-MM (but NOT YYYY-MM-DD)
_PARTIAL_DATE_RE = re.compile(r'^\d{4}(-\d{2})?$')


def package_get_year(pkg_dict):
    """
    Helper function to return the package year published.

    :param pkg_dict: return:
    """
    if not isinstance(pkg_dict['metadata_created'], datetime):
        pkg_dict['metadata_created'] = parser.parse(pkg_dict['metadata_created'])

    return pkg_dict['metadata_created'].year


def get_site_title():
    """
    Helper function to return the config site title, if it exists.

    :returns: str site title
    """
    return toolkit.config.get('ckanext.doi.site_title')


def get_site_url():
    """
    Get the site URL.

    Try and use ckanext.doi.site_url but if that's not set use ckan.site_url.
    """
    site_url = toolkit.config.get(
        'ckanext.doi.site_url', toolkit.config.get('ckan.site_url', '')
    )
    return site_url.rstrip('/')


def date_or_none(date_object_or_string):
    """
    Try and convert the given object into a datetime; if not possible, return None.

    Partial ISO 8601 date strings (YYYY or YYYY-MM) are returned as-is to preserve
    their granularity — dateutil.parser.parse would otherwise fill the missing day or
    month with today's values, producing a misleadingly precise result.

    :param date_object_or_string: a datetime or date string
    :return: datetime, str (for partial dates), or None
    """
    if isinstance(date_object_or_string, datetime):
        return date_object_or_string
    elif isinstance(date_object_or_string, str):
        stripped = date_object_or_string.strip()
        if _PARTIAL_DATE_RE.match(stripped):
            return stripped
        return parser.parse(stripped)
    else:
        return None


def doi_test_mode():
    """
    Determines whether we're running in test mode.

    :return: bool
    """
    return toolkit.asbool(get_setting('ckanext.doi.test_mode', default=get_debug()))


def doi_dev_mode():
    """
    Determines whether we're running in dev mode (fake DOI minting for localhost).

    :return: bool
    """
    return toolkit.asbool(get_setting('ckanext.doi.dev_mode', default=False))
