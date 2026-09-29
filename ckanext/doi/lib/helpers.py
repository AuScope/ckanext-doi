# !/usr/bin/env python
# encoding: utf-8
#
# This file is part of ckanext-doi
# Created by the Natural History Museum in London, UK

from datetime import datetime

import dateutil.parser as parser
from ckan.plugins import toolkit
from ckantools.config import get_debug, get_setting


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

    :param date_object_or_string: a datetime or date string
    :return: datetime or None
    """
    if isinstance(date_object_or_string, datetime):
        return date_object_or_string
    elif isinstance(date_object_or_string, str):
        return parser.parse(date_object_or_string)
    else:
        return None


def flash_success_safe(message, context=None):
    """
    Flash a success message only when it is safe to do so.

    ``toolkit.h.flash_success`` writes to the Flask session, which requires an
    active HTTP request context. When ``after_dataset_update`` runs inside a
    background job (e.g. an RQ worker), there is no request context and calling
    ``flash_success`` raises ``RuntimeError: Working outside of request
    context``.

    This helper skips the flash when either:

    * the caller explicitly opts out by setting a truthy ``context['defer_flash']``
      or ``context['no_flash']`` (useful for background jobs that know they have
      no request context), or
    * there is no active Flask request context (a robust fallback so callers
      that forget the flag still don't crash).

    :param message: the message to flash on success
    :param context: the CKAN action context dict (optional)
    """
    context = context or {}
    if context.get('defer_flash') or context.get('no_flash'):
        # log.debug("flash_success_safe: caller opted out of flashing; skipping")
        return

    # Robust fallback: only flash when there is an active request context.
    try:
        from flask import has_request_context
    except ImportError:
        has_request_context = None

    if has_request_context is not None and not has_request_context():
        # log.debug(
        #    "flash_success_safe: no active request context; skipping flash"
        # )
        return

    toolkit.h.flash_success(message)


def doi_test_mode():
    """
    Determines whether we're running in test mode.

    :return: bool
    """
    return toolkit.asbool(get_setting('ckanext.doi.test_mode', default=get_debug()))
