from unittest.mock import MagicMock, call, patch

import pytest
from datacite.errors import DataCiteNotFoundError

from ckan.tests import factories
from ckan.tests.helpers import call_action
from ckanext.doi import plugin as doi_plugin
from ckanext.doi.model.crud import DOIQuery


@pytest.mark.filterwarnings("ignore::sqlalchemy.exc.SADeprecationWarning")
@pytest.mark.ckan_config("ckan.plugins", "doi")
@pytest.mark.ckan_config("ckanext.doi.prefix", "testing")
@pytest.mark.usefixtures("with_doi_table", "with_plugins")
class TestDOIPlugin:
    def test_should_manage_doi_defaults_to_true(self):
        assert doi_plugin._should_manage_doi({}) is True

    def test_after_dataset_create(self):
        # as well as testing the after_dataset_create functionality works on some level,
        # this test is also here to confirm that after_dataset_create is called
        # correctly whether you are on CKAN 2.9 or CKAN 2.10.

        with patch("ckanext.doi.lib.api.DataCiteMDSClient") as mock_client_class:
            # mock the datacite API to make it look like the DOI generated is new
            mock_client = MagicMock(
                metadata_get=MagicMock(side_effect=DataCiteNotFoundError())
            )
            mock_client_class.return_value = mock_client

            # create a new dataset
            dataset = factories.Dataset()

        # check that a DOI is created in the database for this new dataset
        assert DOIQuery.read_package(dataset["id"], create_if_none=False)

    def test_after_dataset_create_can_skip_doi_management(self):
        with patch("ckanext.doi.plugin._should_manage_doi", return_value=False):
            with patch("ckanext.doi.lib.api.DataCiteMDSClient") as mock_client_class:
                dataset = factories.Dataset()

        assert DOIQuery.read_package(dataset["id"], create_if_none=False) is None
        assert not mock_client_class.called

    def test_after_dataset_create_rechecks_package_show_before_creating_doi(self):
        plugin = doi_plugin.DOIPlugin()

        with patch(
            "ckanext.doi.plugin._should_manage_doi",
            side_effect=[True, False],
        ) as should_manage:
            with patch("ckanext.doi.plugin.toolkit.get_action") as get_action:
                get_action.return_value.return_value = {
                    "id": "pkg-1",
                    "identifier_source": "external",
                    "identifier_url": "https://doi.org/10.1234/external",
                }
                with patch("ckanext.doi.plugin.DOIQuery.read_package") as read_package:
                    plugin.after_dataset_create({}, {"id": "pkg-1"})

        assert should_manage.call_count == 2
        get_action.assert_called_once_with("package_show")
        read_package.assert_not_called()

    @pytest.mark.ckan_config("ckanext.doi.publisher", "argh!")
    def test_after_dataset_update_can_skip_datacite_calls(self):
        with patch("ckanext.doi.plugin._should_manage_doi", return_value=False):
            with patch("ckanext.doi.lib.api.DataCiteMDSClient") as mock_client_class:
                mock_client = MagicMock(
                    metadata_get=MagicMock(side_effect=DataCiteNotFoundError())
                )
                mock_client_class.return_value = mock_client

                dataset = factories.Dataset(title="test", author="Author, Test")
                call_action("package_patch", id=dataset["id"], title="different")

        assert DOIQuery.read_package(dataset["id"], create_if_none=False) is None
        assert not mock_client.metadata_post.called
        assert not mock_client.doi_post.called

    def test_after_dataset_update_rechecks_complete_package_before_managing_doi(self):
        plugin = doi_plugin.DOIPlugin()
        hook_package = {
            "id": "pkg-1",
            "state": "active",
            "private": False,
        }
        complete_package = {
            **hook_package,
            "identifier_source": "external",
            "identifier_url": "https://doi.org/10.1234/external",
        }

        with patch(
            "ckanext.doi.plugin._should_manage_doi",
            side_effect=[True, False],
        ) as should_manage, patch(
            "ckanext.doi.plugin._package_show_dict",
            return_value=complete_package,
        ) as package_show, patch(
            "ckanext.doi.plugin.DOIQuery.read_package"
        ) as read_package, patch(
            "ckanext.doi.plugin.get_client"
        ) as get_client:
            result = plugin.after_dataset_update({}, hook_package)

        assert result is hook_package
        assert should_manage.call_args_list == [
            call(hook_package),
            call(complete_package),
        ]
        package_show.assert_called_once_with({}, "pkg-1")
        read_package.assert_not_called()
        get_client.assert_not_called()

    def test_after_dataset_show_skip_does_not_override_package_doi(self):
        plugin = doi_plugin.DOIPlugin()
        package = {"id": "pkg-1", "doi": "10.1234/external"}

        with patch(
            "ckanext.doi.plugin._should_manage_doi", return_value=False
        ), patch("ckanext.doi.plugin.DOIQuery.read_package") as read_package:
            plugin.after_dataset_show({}, package)

        assert package["doi"] == "10.1234/external"
        assert "doi_status" not in package
        read_package.assert_not_called()

    @pytest.mark.ckan_config("ckanext.doi.publisher", "argh!")
    def test_after_dataset_update(self):
        # as well as testing the after_dataset_update functionality works on some level,
        # this test is also here to confirm that after_dataset_update is called
        # correctly whether you are on CKAN 2.9 or CKAN 2.10.

        # the udpate function has flashes in it which we don't care about
        with patch("ckan.plugins.toolkit.h.flash_success"):
            with patch("ckanext.doi.lib.api.DataCiteMDSClient") as mock_client_class:
                # mock the datacite API to make it look like the DOI generated is new
                mock_client = MagicMock(
                    metadata_get=MagicMock(side_effect=DataCiteNotFoundError())
                )
                mock_client_class.return_value = mock_client

                # create a new dataset
                dataset = factories.Dataset(title="test", author="Author, Test")

                # reset our mock
                mock_client.reset()

                # update the dataset's title, this should trigger after_dataset_update
                call_action("package_patch", id=dataset["id"], title="different")

                # check that attempts have been made to mint the DOI
                assert mock_client.metadata_post.called
                assert mock_client.doi_post.called

    @pytest.mark.ckan_config("ckanext.doi.publisher", "argh!")
    def test_datacite_failure_does_not_abort_save_or_mint(self):
        with patch("ckan.plugins.toolkit.h.flash_success"), patch(
            "ckan.plugins.toolkit.h.flash_error"
        ) as flash_error, patch(
            "ckanext.doi.lib.api.DataCiteMDSClient"
        ) as mock_client_class:
            mock_client = MagicMock(
                metadata_get=MagicMock(side_effect=DataCiteNotFoundError())
            )
            mock_client_class.return_value = mock_client

            dataset = factories.Dataset(title="test", author="Author, Test")
            mock_client.reset_mock()
            mock_client.metadata_post.side_effect = RuntimeError(
                "metadata validation failed"
            )

            updated = call_action(
                "package_patch", id=dataset["id"], title="saved despite DOI error"
            )

        assert updated["title"] == "saved despite DOI error"
        assert mock_client.metadata_post.called
        assert not mock_client.doi_post.called
        flash_error.assert_called_once()
        assert "dataset was saved" in flash_error.call_args.args[0]
        assert DOIQuery.read_package(dataset["id"]).published is None

    @pytest.mark.ckan_config("ckanext.doi.publisher", "argh!")
    @pytest.mark.ckan_config("ckanext.doi.site_url", "http://dois.are.great.org")
    def test_after_dataset_show(self):
        # as well as testing the after_dataset_show functionality works on some level,
        # this test is also here to confirm that after_dataset_show is called correctly
        # whether you are on CKAN 2.9 or CKAN 2.10.

        with patch("ckanext.doi.lib.api.DataCiteMDSClient") as mock_client_class:
            # mock the datacite API to make it look like the DOI generated is new
            mock_client = MagicMock(
                metadata_get=MagicMock(side_effect=DataCiteNotFoundError())
            )
            mock_client_class.return_value = mock_client

            # create a new dataset
            dataset = factories.Dataset()

        doi = DOIQuery.read_package(dataset["id"], create_if_none=False)
        package = call_action("package_show", id=dataset["id"])
        assert package["doi"] == doi.identifier
        assert package["doi_status"] is False
        assert package["domain"] == "dois.are.great.org"
        assert package["doi_date_published"] is None
        assert package["doi_publisher"] == "argh!"
