from copy import deepcopy
from datetime import datetime

import click
from ckan import model
from ckan.model import Session
from ckan.plugins import toolkit
from sqlalchemy import inspect as sa_inspect

from ckanext.doi.lib import datacite_compat
from ckanext.doi.lib.api import DataciteClient, get_client
from ckanext.doi.lib.metadata import build_metadata_dict, build_xml_dict
from ckanext.doi.model import doi as doi_model
from ckanext.doi.model.crud import DOIQuery
from ckanext.doi.model.doi import DOI


def get_commands():
    return [doi]


@click.group()
def doi():
    pass


def _set_issued_date(xml_dict):
    """Set the Issued date immediately before metadata is minted."""
    for date_entry in xml_dict.get('dates', []):
        if date_entry.get('dateType') == 'Issued':
            date_entry['date'] = datetime.strftime(
                datetime.now(), '%Y-%m-%d %H:%M:%S.%f'
            )
            break


def _validate_metadata(identifier, xml_dict):
    """Validate and serialize metadata without modifying or posting it."""
    validation_dict = deepcopy(xml_dict)
    validation_dict['doi'] = identifier
    datacite_compat.validator.validate(validation_dict)
    datacite_compat.tostring(validation_dict)


@doi.command(name='initdb')
def init_db():
    engine = model.meta.engine
    inspector = sa_inspect(engine)

    if not inspector.has_table('package'):
        click.secho(
            'Package table must exist before initialising the DOI table', fg='red'
        )
        raise click.Abort()

    if inspector.has_table('doi'):
        click.secho('DOI table already exists', fg='green')
    else:
        doi_model.doi_table.create(bind=engine)
        click.secho('DOI table created', fg='green')


@doi.command(name='delete-dois')
def delete_dois():
    """
    Delete all DOIs from the database.
    """
    to_delete = Session.query(DOI).filter(
        DOI.identifier.like(f'%{DataciteClient.get_prefix()}%')
    )
    doi_count = to_delete.count()
    if doi_count == 0:
        click.secho('Nothing to delete', fg='green')
        return
    if click.confirm(f'Delete {doi_count} DOIs from the database?', abort=True):
        to_delete.delete(synchronize_session=False)
        Session.commit()
        click.secho(f'Deleted {doi_count} DOIs from the database')


@doi.command(name='update-doi')
@click.option(
    '-p', '--package_id', 'package_ids', multiple=True, help='Package id(s) to update'
)
@click.option(
    '--mint-unpublished',
    is_flag=True,
    help='Publish metadata and mint local DOI records not yet registered at DataCite.',
)
@click.option(
    '--dry-run',
    is_flag=True,
    help='Build, validate, and compare metadata without posting or minting.',
)
def update_doi(package_ids, mint_unpublished, dry_run):
    """
    Update either all DOIs in the system or the ones associated with the given packages.
    """
    if not package_ids:
        dois_to_update = Session.query(DOI).all()
    else:
        dois_to_update = list(filter(None, map(DOIQuery.read_package, package_ids)))

    if len(dois_to_update) == 0:
        click.secho('No DOIs found to update', fg='green')
        return

    updated = 0
    skipped = 0
    failed = 0

    for record in dois_to_update:
        title = record.package_id
        try:
            pkg_dict = toolkit.get_action('package_show')(
                {}, {'id': record.package_id}
            )
            title = pkg_dict.get('title') or record.package_id

            if record.published is None and not mint_unpublished:
                click.secho(
                    f'"{title}" does not have a published DOI; ignoring. '
                    'Use --mint-unpublished to register it.',
                    fg='yellow',
                )
                skipped += 1
                continue
            if pkg_dict.get('state', 'active') != 'active' or pkg_dict.get(
                'private', False
            ):
                click.secho(
                    f'"{title}" is inactive or private; ignoring', fg='yellow'
                )
                skipped += 1
                continue

            metadata_dict = build_metadata_dict(pkg_dict)
            xml_dict = build_xml_dict(metadata_dict)

            if record.published is None:
                _set_issued_date(xml_dict)

            if dry_run:
                _validate_metadata(record.identifier, xml_dict)

            if record.published is None:
                if dry_run:
                    click.secho(
                        f'Would publish metadata and mint DOI for "{title}"',
                        fg='cyan',
                    )
                else:
                    client = get_client()
                    client.set_metadata(record.identifier, xml_dict)
                    client.mint_doi(record.identifier, record.package_id)
                    click.secho(
                        f'Published metadata and minted DOI for "{title}"',
                        fg='green',
                    )
                updated += 1
                continue

            client = get_client()
            same = client.check_for_update(record.identifier, xml_dict)
            if same:
                click.secho(f'"{title}" is already up to date', fg='green')
                skipped += 1
            elif dry_run:
                click.secho(f'Would update "{title}"', fg='cyan')
                updated += 1
            else:
                client.set_metadata(record.identifier, xml_dict)
                click.secho(f'Updated "{title}"', fg='green')
                updated += 1
        except Exception as e:
            failed += 1
            click.secho(
                f'Error while processing "{title}" '
                f'(DOI {record.identifier}): {e}',
                fg='red',
            )

    click.secho(
        f'Summary: updated={updated}, skipped={skipped}, failed={failed}',
        fg='cyan' if dry_run else None,
    )
