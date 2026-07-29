from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch

from click.testing import CliRunner

from ckanext.doi.cli import doi


def _record(package_id, published):
    return SimpleNamespace(
        package_id=package_id,
        identifier=f'10.1234/{package_id}',
        published=published,
    )


def _package(package_id):
    return {
        'id': package_id,
        'title': package_id,
        'state': 'active',
        'private': False,
    }


def test_update_doi_skips_unpublished_by_default():
    record = _record('unpublished', None)

    with patch('ckanext.doi.cli.Session') as session, patch(
        'ckanext.doi.cli.toolkit.get_action'
    ) as get_action, patch('ckanext.doi.cli.get_client') as get_client:
        session.query.return_value.all.return_value = [record]
        get_action.return_value.return_value = _package(record.package_id)

        result = CliRunner().invoke(doi, ['update-doi'])

    assert result.exit_code == 0
    assert 'Use --mint-unpublished' in result.output
    assert 'updated=0, skipped=1, failed=0' in result.output
    get_client.assert_not_called()


def test_update_doi_mints_unpublished_after_metadata():
    record = _record('unpublished', None)
    client = MagicMock()
    xml_dict = {'dates': [{'dateType': 'Issued', 'date': None}]}

    with patch('ckanext.doi.cli.Session') as session, patch(
        'ckanext.doi.cli.toolkit.get_action'
    ) as get_action, patch(
        'ckanext.doi.cli.build_metadata_dict', return_value={}
    ), patch(
        'ckanext.doi.cli.build_xml_dict', return_value=xml_dict
    ), patch(
        'ckanext.doi.cli.get_client', return_value=client
    ):
        session.query.return_value.all.return_value = [record]
        get_action.return_value.return_value = _package(record.package_id)

        result = CliRunner().invoke(doi, ['update-doi', '--mint-unpublished'])

    assert result.exit_code == 0
    assert client.method_calls == [
        call.set_metadata(record.identifier, xml_dict),
        call.mint_doi(record.identifier, record.package_id),
    ]
    assert xml_dict['dates'][0]['date']
    assert 'updated=1, skipped=0, failed=0' in result.output


def test_update_doi_dry_run_validates_without_posting():
    record = _record('unpublished', None)
    xml_dict = {'dates': [{'dateType': 'Issued', 'date': None}]}

    with patch('ckanext.doi.cli.Session') as session, patch(
        'ckanext.doi.cli.toolkit.get_action'
    ) as get_action, patch(
        'ckanext.doi.cli.build_metadata_dict', return_value={}
    ), patch(
        'ckanext.doi.cli.build_xml_dict', return_value=xml_dict
    ), patch(
        'ckanext.doi.cli._validate_metadata'
    ) as validate_metadata, patch(
        'ckanext.doi.cli.get_client'
    ) as get_client:
        session.query.return_value.all.return_value = [record]
        get_action.return_value.return_value = _package(record.package_id)

        result = CliRunner().invoke(
            doi, ['update-doi', '--mint-unpublished', '--dry-run']
        )

    assert result.exit_code == 0
    validate_metadata.assert_called_once_with(record.identifier, xml_dict)
    assert xml_dict['dates'][0]['date']
    get_client.assert_not_called()
    assert 'Would publish metadata and mint DOI' in result.output
    assert 'updated=1, skipped=0, failed=0' in result.output


def test_update_doi_continues_after_per_record_failure():
    failed_record = _record('broken', datetime.now())
    good_record = _record('current', datetime.now())
    client = MagicMock()
    client.check_for_update.return_value = True

    with patch('ckanext.doi.cli.Session') as session, patch(
        'ckanext.doi.cli.toolkit.get_action'
    ) as get_action, patch(
        'ckanext.doi.cli.build_metadata_dict',
        side_effect=[ValueError('invalid metadata'), {}],
    ), patch(
        'ckanext.doi.cli.build_xml_dict', return_value={}
    ), patch(
        'ckanext.doi.cli.get_client', return_value=client
    ):
        session.query.return_value.all.return_value = [failed_record, good_record]
        get_action.return_value.side_effect = lambda _, data: _package(data['id'])

        result = CliRunner().invoke(doi, ['update-doi'])

    assert result.exit_code == 0
    assert 'invalid metadata' in result.output
    assert '"current" is already up to date' in result.output
    assert 'updated=0, skipped=1, failed=1' in result.output
