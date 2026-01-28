#!/usr/bin/env python3
# encoding: utf-8
#
# This file is part of ckanext-doi
# Created by the Natural History Museum in London, UK

import logging
import ast
import datetime

from ckan.lib.helpers import lang as ckan_lang
from ckan.model import Package
from ckan.plugins import PluginImplementations, toolkit

from ckanext.doi.interfaces import IDoi
from ckanext.doi.lib.errors import DOIMetadataException
from ckanext.doi.lib.helpers import date_or_none, get_site_url, package_get_year

log = logging.getLogger(__name__)


def build_metadata_dict(pkg_dict):
    """
    Build/extract a basic dict of metadata that can then be passed to build_xml_dict.

    This function implements PIDINST-based mapping for instrument registries,
    with fallback support for traditional dataset metadata.

    PIDINST Mapping (per DataCite schema 4.5):
    - creators: from 'manufacturer' field (instrument manufacturers/developers)
    - contributors: from 'owner' field (HostingInstitution - responsible organizations)
    - alternateIdentifiers: from 'alternate_identifier_obj' field
    - relatedIdentifiers: from 'related_identifier_obj' field
    - types.resourceTypeGeneral: "Instrument" (DataCite 4.5+)
    
    Reference: https://datacite-metadata-schema.readthedocs.io/en/4.5/mappings/pidinst/

    Legacy Dataset Mapping (fallback for backwards compatibility):
    - creators/contributors: from 'author' field
    - relatedIdentifiers: from 'related_resource' field
    - types.resourceTypeGeneral: "Dataset"

    Configuration:
    - ckanext.doi.datacite_schema_version: DataCite schema version (default: 4.5)
    - ckanext.doi.resource_type: resourceTypeGeneral (default: Instrument)
    - ckanext.doi.publisher: required publisher name

    :param pkg_dict: dict of package details
    """
    metadata_dict = {}

    # collect errors instead of throwing them immediately; some data may not be correctly handled
    # by this base method but will be handled correctly by plugins that implement IDoi
    errors = {}

    # required fields first (identifier will be added later)
    required = {
        'creators': [],
        'titles': [],
        'publisher': None,
        'publicationYear': None,
        'resourceType': None,
    }

    def _add_required(key, get_func):
        try:
            required[key] = get_func()
        except Exception as e:
            errors[key] = e

    # CREATORS
    # For PIDINST instrument schema, map 'manufacturer' field as creators (instrument developers/producers)
    # Per DataCite PIDINST mapping: https://datacite-metadata-schema.readthedocs.io/en/4.5/mappings/pidinst/
    try:
        creators_list = []
        manufacturer_list = pkg_dict.get('manufacturer', [])
        if isinstance(manufacturer_list, str):
            manufacturer_list = ast.literal_eval(manufacturer_list)
        if isinstance(manufacturer_list, list):
            for mfr_dict in manufacturer_list:
                creator = {
                    'name': mfr_dict.get('manufacturer_name', ''),
                    'nameType': 'Organizational',
                }
                # Add manufacturer identifier if present
                if mfr_dict.get('manufacturer_identifier'):
                    creator['nameIdentifiers'] = [{
                        'nameIdentifier': mfr_dict['manufacturer_identifier'],
                        'nameIdentifierScheme': mfr_dict.get('manufacturer_identifier_type', 'Other'),
                    }]
                creators_list.append(creator)
        # Fallback: if no owners, try legacy 'author' field for backwards compatibility
        if not creators_list:
            author_value = pkg_dict.get('author')
            if author_value:
                # Handle simple string author (legacy format)
                if isinstance(author_value, str):
                    # Check if it looks like a list string representation
                    if author_value.strip().startswith('['):
                        try:
                            auth_list = ast.literal_eval(author_value)
                        except (ValueError, SyntaxError):
                            # If parsing fails, treat as simple string
                            auth_list = None
                    else:
                        # Simple string like "Author, Test"
                        auth_list = None
                    
                    # If we couldn't parse it as a list, use it as a simple name
                    if auth_list is None:
                        creators_list.append({
                            'name': author_value,
                            'nameType': 'Personal',
                        })
                    else:
                        # Parsed successfully as list
                        for auth_dict in auth_list:
                            creators_list.append({
                                'name': auth_dict.get('author_name', ''),
                                'nameType': auth_dict.get('author_name_type', 'Personal'),
                                'affiliation': [{
                                    'name': auth_dict.get('author_affiliation', ''),
                                    'affiliationIdentifier': auth_dict.get('author_affiliation_identifier', ''),
                                    'affiliationIdentifierScheme': auth_dict.get('author_affiliation_identifier_type', ''),
                                }] if auth_dict.get('author_affiliation') else [],
                                'nameIdentifiers': [{
                                    'nameIdentifier': auth_dict.get('author_identifier', ''),
                                    'nameIdentifierScheme': auth_dict.get('author_identifier_type', ''),
                                }] if auth_dict.get('author_identifier') else [],
                            })
                elif isinstance(author_value, list):
                    # Already a list
                    for auth_dict in author_value:
                        creators_list.append({
                            'name': auth_dict.get('author_name', ''),
                            'nameType': auth_dict.get('author_name_type', 'Personal'),
                            'affiliation': [{
                                'name': auth_dict.get('author_affiliation', ''),
                                'affiliationIdentifier': auth_dict.get('author_affiliation_identifier', ''),
                                'affiliationIdentifierScheme': auth_dict.get('author_affiliation_identifier_type', ''),
                            }] if auth_dict.get('author_affiliation') else [],
                            'nameIdentifiers': [{
                                'nameIdentifier': auth_dict.get('author_identifier', ''),
                                'nameIdentifierScheme': auth_dict.get('author_identifier_type', ''),
                            }] if auth_dict.get('author_identifier') else [],
                        })
        required['creators'] = creators_list
    except Exception as e:
        errors['creators'] = e

    # TITLES
    _add_required('titles', lambda: [{'title': pkg_dict.get('title')}])

    # PUBLISHER
    _add_required('publisher', lambda: toolkit.config.get('ckanext.doi.publisher'))

    # PUBLICATION YEAR - set to the original date when the DOI was minted
    doi_date_published = pkg_dict.get('doi_date_published')
    if doi_date_published is None or not doi_date_published[:4].isdecimal():
        _add_required('publicationYear', lambda: datetime.datetime.now().year)
    else:
        # 'doi_date_published' format is 'YYYY-MM-DD'
        _add_required('publicationYear', lambda: doi_date_published[:4])

    # TYPE
    _add_required('resourceType', lambda: pkg_dict.get('type'))

    # now the optional fields
    optional = {
        'subjects': [],
        'contributors': [],
        'dates': [],
        'language': '',
        'alternateIdentifiers': [],
        'relatedIdentifiers': [],
        'sizes': [],
        'formats': [],
        'version': '',
        'rightsList': [],
        'descriptions': [],
        'geoLocations': [],
        'fundingReferences': [],
    }

    # SUBJECTS
    # use the tag list
    try:
        tags = pkg_dict.get('tag_string', '').split(',')
        tags += [
            tag['name'] if isinstance(tag, dict) else tag
            for tag in pkg_dict.get('tags', [])
        ]
        optional['subjects'] = [
            {'subject': tag} for tag in sorted({t for t in tags if t != ''})
        ]
    except Exception as e:
        errors['subjects'] = e

    # CONTRIBUTORS
    # For PIDINST instrument schema, map 'owner' field as contributors with role 'HostingInstitution'
    # Per DataCite PIDINST mapping: https://datacite-metadata-schema.readthedocs.io/en/4.5/mappings/pidinst/
    try:
        contributors_list = []
        owner_list = pkg_dict.get('owner', [])
        if isinstance(owner_list, str):
            owner_list = ast.literal_eval(owner_list)
        if isinstance(owner_list, list):
            for owner_dict in owner_list:
                contributor = {
                    'name': owner_dict.get('owner_name', ''),
                    'contributorType': 'HostingInstitution',
                    'nameType': 'Organizational',
                }
                # Add owner identifier if present
                if owner_dict.get('owner_identifier'):
                    contributor['nameIdentifiers'] = [{
                        'nameIdentifier': owner_dict['owner_identifier'],
                        'nameIdentifierScheme': owner_dict.get('owner_identifier_type', 'Other'),
                    }]
                contributors_list.append(contributor)
        # Fallback: legacy author field as ContactPerson for backwards compatibility
        if not contributors_list:
            author_value = pkg_dict.get('author')
            if author_value:
                # Handle simple string author (legacy format)
                if isinstance(author_value, str):
                    # Check if it looks like a list string representation
                    if author_value.strip().startswith('['):
                        try:
                            auth_list = ast.literal_eval(author_value)
                        except (ValueError, SyntaxError):
                            # If parsing fails, treat as simple string
                            auth_list = None
                    else:
                        # Simple string like "Author, Test"
                        auth_list = None
                    
                    # If we couldn't parse it as a list, use it as a simple name
                    if auth_list is None:
                        contributors_list.append({
                            'name': author_value,
                            'contributorType': 'ContactPerson',
                            'nameType': 'Personal',
                        })
                    else:
                        # Parsed successfully as list
                        for auth_dict in auth_list:
                            contributors_list.append({
                                'name': auth_dict.get('author_name', ''),
                                'contributorType': 'ContactPerson',
                                'nameType': auth_dict.get('author_name_type', 'Personal'),
                                'affiliation': [{
                                    'name': auth_dict.get('author_affiliation', ''),
                                    'affiliationIdentifier': auth_dict.get('author_affiliation_identifier', ''),
                                    'affiliationIdentifierScheme': auth_dict.get('author_affiliation_identifier_type', ''),
                                }] if auth_dict.get('author_affiliation') else [],
                                'nameIdentifiers': [{
                                    'nameIdentifier': auth_dict.get('author_identifier', ''),
                                    'nameIdentifierScheme': auth_dict.get('author_identifier_type', ''),
                                }] if auth_dict.get('author_identifier') else [],
                            })
                elif isinstance(author_value, list):
                    # Already a list
                    for auth_dict in author_value:
                        contributors_list.append({
                            'name': auth_dict.get('author_name', ''),
                            'contributorType': 'ContactPerson',
                            'nameType': auth_dict.get('author_name_type', 'Personal'),
                            'affiliation': [{
                                'name': auth_dict.get('author_affiliation', ''),
                                'affiliationIdentifier': auth_dict.get('author_affiliation_identifier', ''),
                                'affiliationIdentifierScheme': auth_dict.get('author_affiliation_identifier_type', ''),
                            }] if auth_dict.get('author_affiliation') else [],
                            'nameIdentifiers': [{
                                'nameIdentifier': auth_dict.get('author_identifier', ''),
                                'nameIdentifierScheme': auth_dict.get('author_identifier_type', ''),
                            }] if auth_dict.get('author_identifier') else [],
                        })
        optional['contributors'] = contributors_list
    except Exception as e:
        errors['contributors'] = e

    # DATES
    # created, updated, and doi publish date
    date_errors = {}
    try:
        optional['dates'].append(
            {
                'dateType': 'Created',
                'date': date_or_none(pkg_dict.get('metadata_created')),
            }
        )
    except Exception as e:
        date_errors['created'] = e
    try:
        optional['dates'].append(
            {
                'dateType': 'Updated',
                'date': date_or_none(pkg_dict.get('metadata_modified')),
            }
        )
    except Exception as e:
        date_errors['updated'] = e
    if 'doi_date_published' in pkg_dict:
        try:
            optional['dates'].append(
                {
                    'dateType': 'Issued',
                    'date': date_or_none(pkg_dict.get('doi_date_published')),
                }
            )
        except Exception as e:
            date_errors['doi_date_published'] = e
    
    # Add PIDINST date field (Commissioned/DeCommissioned)
    # Per DataCite PIDINST mapping: use dateType "Other" with dateInformation
    date_list = pkg_dict.get('date', [])
    if isinstance(date_list, str):
        try:
            date_list = ast.literal_eval(date_list)
        except (ValueError, SyntaxError):
            date_list = []
    if isinstance(date_list, list):
        for date_dict in date_list:
            date_value = date_dict.get('date_value')
            date_type = date_dict.get('date_type', '')
            
            if date_value:
                try:
                    optional['dates'].append({
                        'dateType': 'Other',
                        'date': date_or_none(date_value),
                        'dateInformation': date_type  # "Commissioned" or "DeCommissioned"
                    })
                except Exception as e:
                    date_errors[f'pidinst_date_{date_type}'] = e

    # LANGUAGE
    # use language set in CKAN
    try:
        optional['language'] = ckan_lang()
    except Exception as e:
        errors['language'] = e

    # ALTERNATE IDENTIFIERS
    # add permalink back to this site, plus PIDINST alternate_identifier_obj if present
    try:
        alternate_ids = []
        permalink = f'{get_site_url()}/dataset/{pkg_dict["id"]}'
        alternate_ids.append(
            {'alternateIdentifierType': 'URL', 'alternateIdentifier': permalink}
        )
        # Add PIDINST alternate identifiers if present
        alt_id_list = pkg_dict.get('alternate_identifier_obj', [])
        if isinstance(alt_id_list, str):
            alt_id_list = ast.literal_eval(alt_id_list)
        if isinstance(alt_id_list, list):
            for alt_dict in alt_id_list:
                if alt_dict.get('alternate_identifier'):
                    alternate_ids.append({
                        'alternateIdentifier': alt_dict['alternate_identifier'],
                        'alternateIdentifierType': alt_dict.get('alternate_identifier_type', 'Other'),
                    })
        optional['alternateIdentifiers'] = alternate_ids
    except Exception as e:
        errors['alternateIdentifiers'] = e

    # RELATED IDENTIFIERS
    # For PIDINST schema, use related_identifier_obj field
    try:
        related_ids = []
        rel_list = pkg_dict.get('related_identifier_obj', [])
        if isinstance(rel_list, str):
            rel_list = ast.literal_eval(rel_list)
        if isinstance(rel_list, list):
            for rel in rel_list:
                if rel.get('related_identifier'):
                    related_ids.append({
                        'relatedIdentifier': rel['related_identifier'],
                        'relatedIdentifierType': rel.get('related_identifier_type', 'URL'),
                        'relationType': rel.get('relation_type', 'References'),
                    })
        # Fallback: legacy related_resource field
        if not related_ids:
            rel_list = pkg_dict.get('related_resource', [])
            if isinstance(rel_list, str):
                rel_list = ast.literal_eval(rel_list)
            if isinstance(rel_list, list):
                for rel in rel_list:
                    if rel.get('related_resource_url'):
                        related_ids.append({
                            'relatedIdentifier': rel['related_resource_url'],
                            'relatedIdentifierType': 'URL',
                            'relationType': rel.get('relation_type', 'References'),
                        })
        optional['relatedIdentifiers'] = related_ids
    except Exception as e:
        errors['relatedIdentifiers'] = e


    # SIZES
    # sum up given sizes from resources in the package and convert from bytes to kilobytes
    try:
        resource_sizes = [
            r.get('size') or 0 for r in pkg_dict.get('resources', []) or []
        ]
        total_size = [f'{int(sum(resource_sizes) / 1024)} kb']
        optional['sizes'] = total_size
    except Exception as e:
        errors['sizes'] = e

    # FORMATS
    # list unique formats from package resources
    try:
        formats = list(
            set(
                filter(
                    None, [r.get('format') for r in pkg_dict.get('resources', []) or []]
                )
            )
        )
        optional['formats'] = formats
    except Exception as e:
        errors['formats'] = e

    # VERSION
    # doesn't matter if there's no version, it'll get filtered out later
    optional['version'] = pkg_dict.get('version')

    # RIGHTS
    # use the package license and get details from CKAN's license register
    license_id = pkg_dict.get('license_id')
    if license_id is None:
        license_id = pkg_dict.get('license', '')
    try:
        if license_id == 'cc-by-4.0-international':
            optional['rightsList'] = [ {'rightsUri': 'https://spdx.org/licenses/CC-BY-4.0.html',
                                        'rightsIdentifier': 'CC-BY-4.0',
                                        'rightsIdentifierScheme': 'SPDX'} ]
        elif license_id != '' and license_id is not None:
            license_register = Package.get_license_register()
            license = license_register.get(license_id)
            if license is not None:
                optional['rightsList'] = [
                    {'rightsUri': license.url, 'rightsIdentifier': license.id}
                ]
        else:
            optional['rightsList'] = [ {'rights': license_id } ]

    except Exception as e:
        errors['rightsList'] = e

    # DESCRIPTIONS
    # use package description
    descriptions = [
        {'descriptionType': 'Abstract', 'description': pkg_dict.get('description', '')}
    ]
    
    # Collect all TechnicalInfo descriptions (PIDINST mapping)
    tech_info_parts = []
    
    # Add MODEL as TechnicalInfo description
    model_list = pkg_dict.get('model', [])
    if isinstance(model_list, str):
        try:
            model_list = ast.literal_eval(model_list)
        except (ValueError, SyntaxError):
            model_list = []
    if isinstance(model_list, list) and len(model_list) > 0:
        model_items = []
        for model_dict in model_list:
            model_name = model_dict.get('model_name', '')
            model_id = model_dict.get('model_identifier', '')
            model_id_type = model_dict.get('model_identifier_type', '')
            
            if model_name:
                model_text = f"Model: {model_name}"
                if model_id:
                    model_text += f" ({model_id_type}: {model_id})" if model_id_type else f" (ID: {model_id})"
                model_items.append(model_text)
        
        if model_items:
            tech_info_parts.append('; '.join(model_items))
    
    # Add INSTRUMENT_TYPE as TechnicalInfo description
    instrument_type_list = pkg_dict.get('instrument_type', [])
    if isinstance(instrument_type_list, str):
        try:
            instrument_type_list = ast.literal_eval(instrument_type_list)
        except (ValueError, SyntaxError):
            instrument_type_list = []
    if isinstance(instrument_type_list, list) and len(instrument_type_list) > 0:
        type_items = []
        for type_dict in instrument_type_list:
            type_name = type_dict.get('instrument_type_name', '')
            type_id = type_dict.get('instrument_type_identifier', '')
            type_id_type = type_dict.get('instrument_type_identifier_type', '')
            
            if type_name:
                type_text = f"Instrument Type: {type_name}"
                if type_id:
                    type_text += f" ({type_id_type}: {type_id})" if type_id_type else f" (ID: {type_id})"
                type_items.append(type_text)
        
        if type_items:
            tech_info_parts.append('; '.join(type_items))
    
    # Add MEASURED_VARIABLE as TechnicalInfo description
    measured_variable = pkg_dict.get('measured_variable', '')
    if measured_variable:
        # Handle both string and list formats
        if isinstance(measured_variable, str):
            variables = [v.strip() for v in measured_variable.split(',') if v.strip()]
        elif isinstance(measured_variable, list):
            variables = [v if isinstance(v, str) else v.get('name', '') for v in measured_variable if v]
        else:
            variables = []
        
        if variables:
            tech_info_parts.append(f"Measured Variables: {', '.join(variables)}")
    
    # Combine all TechnicalInfo parts into a single description
    if tech_info_parts:
        descriptions.append({
            'descriptionType': 'TechnicalInfo',
            'description': ' | '.join(tech_info_parts)
        })
    
    optional['descriptions'] = descriptions

    # GEOLOCATIONS
    location_choice = pkg_dict.get('location_choice', None)
    if location_choice is not None:
        if location_choice == 'point':
            optional['geoLocations'] = []
            try:
                for feat in pkg_dict["location_data"]["features"]:
                    if feat["geometry"]["type"] == 'Point':
                        coords = feat["geometry"]["coordinates"]
                        # Using float() to catch anything that is not a float
                        optional['geoLocations'].append({ 'geoLocationPoint': { 'pointLongitude': str(float(coords[0])),
                                                                     'pointLatitude': str(float(coords[1])) }, })
            except (ValueError, KeyError, IndexError) as e:
                errors['geoLocations'] = e

        elif location_choice == 'area':
            optional['geoLocations'] = []
            try:
                for feat in pkg_dict["location_data"]["features"]:
                    if feat["geometry"]["type"] == 'Polygon':
                        coord_list = feat["geometry"]["coordinates"][0]
                        # Using float() to catch anything that is not a float
                        optional['geoLocations'].append({ 'geoLocationBox': {
                                                                'westBoundLongitude' : str(float(coord_list[0][0])),
                                                                'eastBoundLongitude' : str(float(coord_list[2][0])),
                                                                'southBoundLatitude' : str(float(coord_list[0][1])),
                                                                'northBoundLatitude' : str(float(coord_list[1][1])) }, })
            except (ValueError, KeyError, IndexError) as e:
                errors['geoLocations'] = e

    # FUNDING
    # For PIDINST schema, use 'funder' field if present
    if pkg_dict.get('funder', '') != '':
        try:
            funder_list = ast.literal_eval(pkg_dict.get('funder'))
            optional['fundingReferences'] = []
            for funder in funder_list:
                id_type = funder.get('funder_identifier_type', 'Other')
                # DataCite 4.5 supports Wikidata and other identifier types
                funding_ref = {'funderName': funder.get('funder_name', '')}
                if funder.get('funder_identifier'):
                    funding_ref['funderIdentifier'] = funder['funder_identifier']
                    funding_ref['funderIdentifierType'] = id_type
                optional['fundingReferences'].append(funding_ref)
        except Exception as e:
            errors['fundingReferences'] = e

    metadata_dict.update(required)
    metadata_dict.update(optional)

    for plugin in PluginImplementations(IDoi):
        # implementations should remove relevant errors from the errors dict if they successfully
        # handle an item
        metadata_dict, errors = plugin.build_metadata_dict(
            pkg_dict, metadata_dict, errors
        )

    for k in required:
        if metadata_dict.get(k) is None and errors.get(k) is None:
            errors[k] = DOIMetadataException('Required field cannot be None')

    required_errors = {k: e for k, e in errors.items() if k in required}
    if len(required_errors) > 0:
        error_msg = (
            f'Could not extract metadata for the following required keys: '
            f'{", ".join(required_errors)}'
        )
        log.exception(error_msg)
        for k, e in required_errors.items():
            log.exception(f'{k}: {e}')
        raise DOIMetadataException(error_msg)

    optional_errors = {k: e for k, e in errors.items() if k in optional}
    if len(required_errors) > 0:
        error_msg = (
            f'Could not extract metadata for the following optional keys: '
            f'{", ".join(optional_errors)}'
        )
        log.debug(error_msg)
        for k, e in optional_errors.items():
            log.debug(f'{k}: {e}')

    return metadata_dict


def build_xml_dict(metadata_dict):
    """
    Builds a dictionary that can be passed directly to datacite.schema45.tostring() to
    generate xml. Previously named metadata_to_xml but renamed as it's not actually
    producing any xml, it's just formatting the metadata so a separate function can then
    generate the xml.

    :param metadata_dict: a dict of metadata generated from build_metadata_dict
    :return: dict that can be passed directly to datacite.schema45.tostring()
    """
    # Determine resource type based on CKAN plugins and dataset type
    # For PIDINST instrument registry, use "Instrument" (DataCite 4.5+)
    if "igsn_theme" in toolkit.config.get('ckan.plugins'):
        # For Sample Repository resource type is "PhysicalObject"
        resource_type_general = "PhysicalObject"
        resource_type = "PhysicalObject"
    else:
        # Check if this is an instrument dataset (PIDINST schema)
        # Default to "Instrument" for instrument registries, fallback to "Dataset"
        resource_type = metadata_dict.get('resourceType', 'Instrument')
        # Use config to determine if we're an instrument registry
        is_instrument = toolkit.config.get('ckanext.doi.resource_type', 'Instrument') == 'Instrument'
        resource_type_general = "Instrument" if is_instrument else "Dataset"

    # Get schema version from config (default 4.5)
    schema_version = toolkit.config.get('ckanext.doi.datacite_schema_version', '4.5')
    schema_url = f'http://datacite.org/schema/kernel-{schema_version.replace(".", "")[0]}'

    # DataCite 4.5+ requires publisher to be an object with 'name' property
    publisher_value = metadata_dict.get('publisher')
    if isinstance(publisher_value, str):
        publisher_value = {'name': publisher_value}
    elif publisher_value is None:
        publisher_value = {'name': ''}

    # required fields first (DOI will be added later)
    xml_dict = {
        'creators': [],
        'titles': metadata_dict.get('titles', []),
        'publisher': publisher_value,
        'publicationYear': str(metadata_dict.get('publicationYear')),
        'types': {
            'resourceType': resource_type,
            'resourceTypeGeneral': resource_type_general,
        },
        'schemaVersion': schema_url,
    }

    xml_dict['creators'] = metadata_dict.get('creators', [])

    optional = [
        'subjects',
        'contributors',
        'dates',
        'language',
        'alternateIdentifiers',
        'relatedIdentifiers',
        'sizes',
        'formats',
        'version',
        'rightsList',
        'descriptions',
        'geoLocations',
        'fundingReferences',
    ]

    for k in optional:
        v = metadata_dict.get(k)
        try:
            has_value = v is not None and len(v) > 0
        except:
            has_value = False
        if not has_value:
            continue
        if k == 'dates':
            item = []
            for date_entry in v:
                date_entry_copy = {k: v for k, v in date_entry.items()}
                date_entry_copy['date'] = str(date_entry_copy['date'])
                item.append(date_entry_copy)
            xml_dict[k] = item
        else:
            xml_dict[k] = v

    for plugin in PluginImplementations(IDoi):
        xml_dict = plugin.build_xml_dict(metadata_dict, xml_dict)

    return xml_dict
