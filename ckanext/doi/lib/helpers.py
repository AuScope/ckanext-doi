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
_COVERAGE_DATE_RE = re.compile(r"^\d{4}(-\d{2}){0,2}$")
_COVERAGE_RANGE_RE = re.compile(
    r"^(?P<start>\d{4}(-\d{2}){0,2})?/(?P<end>\d{4}(-\d{2}){0,2})?$"
)



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


import re
from datetime import datetime

from dateutil import parser

_PARTIAL_DATE_RE = re.compile(r"^\d{4}(-\d{2})?$")
_COVERAGE_DATE_RE = re.compile(r"^\d{4}(-\d{2}){0,2}$")
_COVERAGE_RANGE_RE = re.compile(
    r"^(?P<start>\d{4}(-\d{2}){0,2})?/(?P<end>\d{4}(-\d{2}){0,2})?$"
)


def _validate_partial_or_full_iso_date(value: str) -> str:
    """
    Validate YYYY, YYYY-MM, or YYYY-MM-DD and return the original value.

    Raises ValueError if invalid.
    """
    if not _COVERAGE_DATE_RE.match(value):
        raise ValueError(
            "Invalid date format '{}'. Expected YYYY, YYYY-MM, or YYYY-MM-DD.".format(value)
        )

    if len(value) == 4:
        datetime.strptime(value, "%Y")
    elif len(value) == 7:
        datetime.strptime(value, "%Y-%m")
    elif len(value) == 10:
        datetime.strptime(value, "%Y-%m-%d")
    else:
        raise ValueError(
            "Invalid date format '{}'. Expected YYYY, YYYY-MM, or YYYY-MM-DD.".format(value)
        )

    return value


def _validate_coverage_date(value: str) -> str:
    """
    Validate a Coverage date in RKMS-ISO8601-like form supported by DataCite:
    - YYYY
    - YYYY-MM
    - YYYY-MM-DD
    - start/end
    - start/
    - /end

    Returns the original value if valid.
    Raises ValueError if invalid.
    """
    value = value.strip()

    if "/" not in value:
        return _validate_partial_or_full_iso_date(value)

    match = _COVERAGE_RANGE_RE.match(value)
    if not match:
        raise ValueError(
            "Invalid coverage date range '{}'. Expected forms like "
            "YYYY/YYYY, YYYY-MM/YYYY-MM, YYYY-MM-DD/YYYY-MM-DD, YYYY/, or /YYYY-MM-DD.".format(value)
        )

    start = match.group("start")
    end = match.group("end")

    if not start and not end:
        raise ValueError("Coverage date range '/' is invalid: start and end cannot both be empty.")

    if start:
        _validate_partial_or_full_iso_date(start)
    if end:
        _validate_partial_or_full_iso_date(end)

    return value


def date_or_none(date_object_or_string, date_type=None):
    """
    Try and convert the given object into a datetime; if not possible, return None.

    For most date types:
    - datetime objects are returned as-is
    - partial ISO 8601 strings (YYYY or YYYY-MM) are returned as-is
    - full dates are parsed to datetime

    For date_type='Coverage':
    - accept YYYY, YYYY-MM, YYYY-MM-DD
    - accept RKMS-style ranges: start/end, start/, /end
    - return the original string unchanged to preserve granularity and range syntax
    """
    if isinstance(date_object_or_string, datetime):
        return date_object_or_string

    if not isinstance(date_object_or_string, str):
        return None

    stripped = date_object_or_string.strip()
    if not stripped:
        return None

    if isinstance(date_type, str) and date_type.strip().lower() == "coverage":
        return _validate_coverage_date(stripped)

    if _PARTIAL_DATE_RE.match(stripped):
        return stripped

    return parser.parse(stripped)


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
