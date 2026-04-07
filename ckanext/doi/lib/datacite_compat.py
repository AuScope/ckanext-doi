#!/usr/bin/env python3
# encoding: utf-8
#
# DataCite schema 4.7 compatibility layer.
#
# The datacite Python library (as of v1.4.0) only ships schema45.
# This module extends its validator with DataCite 4.6/4.7 controlled-vocabulary
# additions and wraps tostring() to emit the correct xsi:schemaLocation for
# kernel-4.7.

import copy
import logging

from datacite import schema45

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Controlled-vocabulary values added in DataCite 4.6 and 4.7.
#
# Each entry uses a "signature" — a subset of values already present in the
# 4.5 enum — to locate the right enum list inside the JSON schema, plus the
# list of new values to append.
# ---------------------------------------------------------------------------
_EXTENSIONS = [
    # dateType — 'Coverage' added in 4.6
    {
        'name': 'dateType',
        'signature': {'Created', 'Updated', 'Issued', 'Valid', 'Withdrawn'},
        'add': ['Coverage'],
    },
    # resourceTypeGeneral — 'Award', 'Project' added in 4.6; 'Poster', 'Presentation' in 4.7
    {
        'name': 'resourceTypeGeneral',
        'signature': {'Dataset', 'Software', 'Instrument', 'Collection', 'Image'},
        'add': ['Award', 'Project', 'Poster', 'Presentation'],
    },
    # relatedIdentifierType — 'CSTR', 'RRID' added in 4.6; 'RAiD', 'SWHID' in 4.7
    {
        'name': 'relatedIdentifierType',
        'signature': {'DOI', 'URL', 'ISBN', 'ISSN', 'arXiv'},
        'add': ['CSTR', 'RRID', 'RAiD', 'SWHID'],
    },
    # contributorType — 'Translator' added in 4.6
    {
        'name': 'contributorType',
        'signature': {
            'ContactPerson',
            'DataCollector',
            'DataCurator',
            'Editor',
            'HostingInstitution',
        },
        'add': ['Translator'],
    },
    # relationType — 'HasTranslation', 'IsTranslationOf' added in 4.6; 'Other' in 4.7
    {
        'name': 'relationType',
        'signature': {
            'IsCitedBy',
            'Cites',
            'IsSupplementTo',
            'IsSupplementedBy',
            'References',
            'IsReferencedBy',
        },
        'add': ['HasTranslation', 'IsTranslationOf', 'Other'],
    },
]

# The schema45.tostring() hardcodes xsi:schemaLocation to kernel-4.5.
_SCHEMA_LOC_45 = 'http://schema.datacite.org/meta/kernel-4.5/metadata.xsd'
_SCHEMA_LOC_47 = 'http://schema.datacite.org/meta/kernel-4.7/metadata.xsd'


def _build_extended_validator():
    """Return a validator with 4.6/4.7 enum values patched in."""
    schema = copy.deepcopy(schema45.validator.schema)
    matched = set()

    def _walk(obj):
        if isinstance(obj, dict):
            enum_values = obj.get('enum')
            if isinstance(enum_values, list):
                vals = set(enum_values)
                for idx, ext in enumerate(_EXTENSIONS):
                    if ext['signature'].issubset(vals):
                        matched.add(idx)
                        for value in ext['add']:
                            if value not in enum_values:
                                enum_values.append(value)

            for value in obj.values():
                _walk(value)

        elif isinstance(obj, list):
            for item in obj:
                _walk(item)

    _walk(schema)

    unmatched = set(range(len(_EXTENSIONS))) - matched
    if unmatched:
        missing = ', '.join(_EXTENSIONS[i]['name'] for i in sorted(unmatched))
        raise RuntimeError(
            'datacite_compat: could not locate enum lists for extensions: {}'.format(
                missing
            )
        )

    validator_class = schema45.validator.__class__
    return validator_class(schema)


# Fail loudly — a silent fallback hides broken patches.
validator = _build_extended_validator()


def tostring(data, verbose=False, **kwargs):
    """Serialise *data* to DataCite kernel-4 XML with 4.7 schemaLocation.

    Args:
        data: DataCite metadata payload.
        verbose: When True, log the emitted XML.
        **kwargs: Passed through to schema45.tostring().
    """
    xml = schema45.tostring(data, **kwargs)

    is_bytes = isinstance(xml, bytes)
    xml_text = xml.decode('utf-8') if is_bytes else xml
    xml_text = xml_text.replace(_SCHEMA_LOC_45, _SCHEMA_LOC_47)

    if verbose:
        log.debug('datacite_compat.tostring produced XML:\n%s', xml_text)

    return xml_text.encode('utf-8') if is_bytes else xml_text