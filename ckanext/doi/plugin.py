#!/usr/bin/env python3
# encoding: utf-8
#
# This file is part of ckanext-doi
# Created by the Natural History Museum in London, UK

from datetime import datetime
from logging import getLogger

from ckan.plugins import (
    PluginImplementations,
    SingletonPlugin,
    implements,
    interfaces,
    toolkit,
)

from ckanext.doi import cli
from ckanext.doi.interfaces import IDoi
from ckanext.doi.lib.api import get_client
from ckanext.doi.lib.helpers import (
    get_site_title,
    get_site_url,
    package_get_year,
    doi_test_mode,
    doi_dev_mode,
)
from ckanext.doi.lib.metadata import build_metadata_dict, build_xml_dict
from ckanext.doi.model.crud import DOIQuery

log = getLogger(__name__)


def _pkg_log_summary(pkg_dict):
    pkg_dict = pkg_dict or {}
    return {
        'id': pkg_dict.get('id'),
        'name': pkg_dict.get('name'),
        'type': pkg_dict.get('type'),
        'identifier_source': pkg_dict.get('identifier_source'),
        'identifier_url': pkg_dict.get('identifier_url'),
        'doi_source': pkg_dict.get('doi_source'),
        'doi': pkg_dict.get('doi'),
    }


def _should_manage_doi(pkg_dict):
    """Return False when any IDoi implementation opts this package out."""
    implementations = list(PluginImplementations(IDoi))
    log.debug(
        'ckanext-doi _should_manage_doi pkg=%s implementations=%s',
        _pkg_log_summary(pkg_dict),
        [plugin.__class__.__name__ for plugin in implementations],
    )
    for plugin in implementations:
        should_manage_doi = getattr(plugin, 'should_manage_doi', None)
        if should_manage_doi is None:
            continue
        should_manage = should_manage_doi(pkg_dict)
        log.debug(
            'ckanext-doi _should_manage_doi plugin=%s result=%s pkg=%s',
            plugin.__class__.__name__,
            should_manage,
            _pkg_log_summary(pkg_dict),
        )
        if not should_manage:
            return False
    return True


def _package_show_dict(context, package_id):
    show_context = dict(context)
    show_context['ignore_auth'] = True
    show_context.pop('schema', None)
    return toolkit.get_action('package_show')(show_context, {'id': package_id})


class DOIPlugin(SingletonPlugin, toolkit.DefaultDatasetForm):
    """
    CKAN DOI Extension.
    """

    implements(interfaces.IConfigurer)
    implements(interfaces.IPackageController, inherit=True)
    implements(interfaces.ITemplateHelpers, inherit=True)
    implements(interfaces.IClick)

    ## IClick
    def get_commands(self):
        return cli.get_commands()

    ## IConfigurer
    def update_config(self, config):
        """
        Adds templates.
        """
        toolkit.add_template_directory(config, 'theme/templates')

    ## IPackageController
    def after_dataset_create(self, context, pkg_dict):
        """
        A new dataset has been created, so we need to create a new DOI.

        NB: This is called after creation of a dataset, before resources have been
        added, so state = draft.
        """
        if not _should_manage_doi(pkg_dict):
            log.debug(
                'ckanext-doi after_dataset_create skipped from hook pkg=%s',
                _pkg_log_summary(pkg_dict),
            )
            return

        try:
            pkg_show_dict = _package_show_dict(context, pkg_dict['id'])
        except Exception:
            log.exception(
                'ckanext-doi after_dataset_create could not load package_show '
                'for skip policy; falling back to hook pkg=%s',
                _pkg_log_summary(pkg_dict),
            )
        else:
            if not _should_manage_doi(pkg_show_dict):
                log.debug(
                    'ckanext-doi after_dataset_create skipped from package_show pkg=%s',
                    _pkg_log_summary(pkg_show_dict),
                )
                return

        log.debug(
            'ckanext-doi after_dataset_create managing DOI pkg=%s',
            _pkg_log_summary(pkg_dict),
        )
        DOIQuery.read_package(pkg_dict['id'], create_if_none=True)

    ## IPackageController
    def after_dataset_update(self, context, pkg_dict):
        """
        Dataset has been created/updated.

        Check status of the dataset to determine if we should publish DOI to datacite
        network.
        """
        if not _should_manage_doi(pkg_dict):
            log.debug(
                'ckanext-doi after_dataset_update skipped from hook pkg=%s',
                _pkg_log_summary(pkg_dict),
            )
            return pkg_dict

        # Is this active and public? If so we need to make sure we have an active DOI
        if pkg_dict.get('state', 'active') == 'active' and not pkg_dict.get(
            'private', False
        ):
            package_id = pkg_dict['id']

            try:
                # remove user-defined update schemas first (if needed)
                context.pop('schema', None)

                # Load the package_show version of the dict
                pkg_show_dict = toolkit.get_action('package_show')(
                    context, {'id': package_id}
                )

                # Load or create the local DOI (package may not have a DOI if extension was loaded
                # after package creation)
                doi = DOIQuery.read_package(package_id, create_if_none=True)

                metadata_dict = build_metadata_dict(pkg_show_dict)
                xml_dict = build_xml_dict(metadata_dict)

                client = get_client()

                if doi.published is None:
                    # Set issued date in DOI metadata knowing that it will be minted immediately
                    for d in xml_dict['dates']:
                        if d['dateType'] == 'Issued':
                            d['date'] = datetime.strftime(
                                datetime.now(), '%Y-%m-%d %H:%M:%S.%f'
                            )
                            break
                    # Metadata must validate and be created before minting. If it
                    # fails, the exception is caught below and mint_doi is not called.
                    client.set_metadata(doi.identifier, xml_dict)
                    client.mint_doi(doi.identifier, package_id)
                    toolkit.h.flash_success('DataCite DOI created')
                else:
                    same = client.check_for_update(doi.identifier, xml_dict)
                    if not same:
                        # Not the same, so we want to update the metadata
                        client.set_metadata(doi.identifier, xml_dict)
                        toolkit.h.flash_success('DataCite DOI metadata updated')
            except Exception as e:
                log.error(
                    'DataCite DOI processing failed for package %s: %s',
                    package_id,
                    e,
                    exc_info=True,
                )
                toolkit.h.flash_error(
                    'The dataset was saved, but its DataCite DOI metadata could '
                    f'not be published: {e}. Correct the metadata and save again.'
                )

        return pkg_dict

    # IPackageController
    def after_dataset_show(self, context, pkg_dict):
        """
        Add the DOI details to the pkg_dict so it can be displayed.
        """
        if not _should_manage_doi(pkg_dict):
            log.debug(
                'ckanext-doi after_dataset_show skipped pkg=%s',
                _pkg_log_summary(pkg_dict),
            )
            return

        log.debug(
            'ckanext-doi after_dataset_show managing DOI pkg=%s',
            _pkg_log_summary(pkg_dict),
        )
        doi = DOIQuery.read_package(pkg_dict['id'])
        if doi:
            pkg_dict['doi'] = doi.identifier
            pkg_dict['doi_status'] = True if doi.published else False
            pkg_dict['domain'] = get_site_url().replace('http://', '')
            pkg_dict['doi_date_published'] = (
                datetime.strftime(doi.published, '%Y-%m-%d %H:%M:%S.%f') if doi.published else None
            )
            pkg_dict['doi_publisher'] = toolkit.config.get('ckanext.doi.publisher')

    def after_create(self, *args, **kwargs):
        """
        CKAN 2.9 compat version of after_dataset_create.
        """
        return self.after_dataset_create(*args, **kwargs)

    def after_update(self, *args, **kwargs):
        """
        CKAN 2.9 compat version of after_dataset_update.
        """
        return self.after_dataset_update(*args, **kwargs)

    def after_show(self, *args, **kwargs):
        """
        CKAN 2.9 compat version of after_dataset_show.
        """
        return self.after_dataset_show(*args, **kwargs)

    # ITemplateHelpers
    def get_helpers(self):
        return {
            'package_get_year': package_get_year,
            'now': datetime.now,
            'get_site_title': get_site_title,
            'doi_test_mode': doi_test_mode,
            'doi_dev_mode': doi_dev_mode,
        }
