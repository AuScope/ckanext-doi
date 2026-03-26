from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from ckanext.doi.cli import doi


@pytest.fixture
def cli_runner():
    return CliRunner()


@pytest.fixture
def mock_inspector():
    return MagicMock()


@pytest.fixture
def mock_engine():
    return MagicMock(name='engine')


class TestInitDb:
    """Tests for the 'ckan doi initdb' CLI command."""

    def test_aborts_when_package_table_missing(
        self, cli_runner, mock_engine, mock_inspector
    ):
        mock_inspector.has_table.side_effect = lambda t: {'package': False, 'doi': False}[t]

        with patch('ckanext.doi.cli.model') as mock_model, \
             patch('ckanext.doi.cli.sa_inspect', return_value=mock_inspector):
            mock_model.meta.engine = mock_engine
            result = cli_runner.invoke(doi, ['initdb'])

        assert result.exit_code != 0
        assert 'Package table must exist' in result.output

    def test_reports_existing_doi_table(
        self, cli_runner, mock_engine, mock_inspector
    ):
        mock_inspector.has_table.side_effect = lambda t: {'package': True, 'doi': True}[t]

        with patch('ckanext.doi.cli.model') as mock_model, \
             patch('ckanext.doi.cli.sa_inspect', return_value=mock_inspector):
            mock_model.meta.engine = mock_engine
            result = cli_runner.invoke(doi, ['initdb'])

        assert result.exit_code == 0
        assert 'DOI table already exists' in result.output

    def test_creates_doi_table_when_missing(
        self, cli_runner, mock_engine, mock_inspector
    ):
        mock_inspector.has_table.side_effect = lambda t: {'package': True, 'doi': False}[t]

        with patch('ckanext.doi.cli.model') as mock_model, \
             patch('ckanext.doi.cli.sa_inspect', return_value=mock_inspector), \
             patch('ckanext.doi.cli.doi_model') as mock_doi_model:
            mock_model.meta.engine = mock_engine
            result = cli_runner.invoke(doi, ['initdb'])

        assert result.exit_code == 0
        assert 'DOI table created' in result.output
        mock_doi_model.doi_table.create.assert_called_once_with(bind=mock_engine)

    def test_does_not_create_table_when_already_exists(
        self, cli_runner, mock_engine, mock_inspector
    ):
        mock_inspector.has_table.side_effect = lambda t: {'package': True, 'doi': True}[t]

        with patch('ckanext.doi.cli.model') as mock_model, \
             patch('ckanext.doi.cli.sa_inspect', return_value=mock_inspector), \
             patch('ckanext.doi.cli.doi_model') as mock_doi_model:
            mock_model.meta.engine = mock_engine
            result = cli_runner.invoke(doi, ['initdb'])

        assert result.exit_code == 0
        mock_doi_model.doi_table.create.assert_not_called()

    def test_uses_engine_from_ckan_model(
        self, cli_runner, mock_engine, mock_inspector
    ):
        mock_inspector.has_table.return_value = True

        with patch('ckanext.doi.cli.model') as mock_model, \
             patch('ckanext.doi.cli.sa_inspect', return_value=mock_inspector) as mock_sa_inspect:
            mock_model.meta.engine = mock_engine
            cli_runner.invoke(doi, ['initdb'])

        mock_sa_inspect.assert_called_once_with(mock_engine)
