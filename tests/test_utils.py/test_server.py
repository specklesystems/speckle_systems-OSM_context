import os
import secrets
import string

import pytest
from gql import gql
from speckle_automate import AutomationContext, AutomationRunData
from specklepy.api import operations
from specklepy.api.client import SpeckleClient
from specklepy.logging.exceptions import SpeckleException
from specklepy.objects.base import Base
from specklepy.objects.units import Units
from specklepy.transports.server import ServerTransport

from utils.utils_server import (
    get_commit_data,
    get_ref_obj_data,
    get_units_from_first_display_value,
    query_units_info,
    query_version_info,
)


def crypto_random_string(length: int) -> str:
    """Generate a semi crypto random string of a given length."""
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def register_new_automation(
    project_id: str,
    model_id: str,
    speckle_client: SpeckleClient,
    automation_id: str,
    automation_name: str,
    automation_revision_id: str,
):
    """Register a new automation in the speckle server."""
    query = gql(
        """
        mutation CreateAutomation(
            $projectId: String! 
            $modelId: String! 
            $automationName: String!
            $automationId: String! 
            $automationRevisionId: String!
        ) {
                automationMutations {
                    create(
                        input: {
                            projectId: $projectId
                            modelId: $modelId
                            automationName: $automationName 
                            automationId: $automationId
                            automationRevisionId: $automationRevisionId
                        }
                    )
                }
            }
        """
    )
    params = {
        "projectId": project_id,
        "modelId": model_id,
        "automationName": automation_name,
        "automationId": automation_id,
        "automationRevisionId": automation_revision_id,
    }
    speckle_client.httpclient.execute(query, params)


@pytest.fixture()
def speckle_token() -> str:
    """Provide a speckle token for the test suite."""
    env_var = "SPECKLE_TOKEN"
    token = os.getenv(env_var)
    if not token:
        raise ValueError(f"Cannot run tests without a {env_var} environment variable")
    return token


@pytest.fixture()
def speckle_server_url() -> str:
    """Provide a speckle server url for the test suite, default to localhost."""
    return os.getenv("SPECKLE_SERVER_URL", "http://127.0.0.1:3000")


@pytest.fixture()
def test_client(speckle_server_url: str, speckle_token: str) -> SpeckleClient:
    """Initialize a SpeckleClient for testing."""
    test_client = SpeckleClient(
        speckle_server_url, speckle_server_url.startswith("https")
    )
    test_client.authenticate_with_token(speckle_token)
    return test_client


@pytest.fixture()
def test_object() -> Base:
    """Create a Base model for testing."""
    root_object = Base()
    root_object.foo = "bar"
    return root_object


@pytest.fixture()
def automation_run_data(
    test_object: Base, test_client: SpeckleClient, speckle_server_url: str
) -> AutomationRunData:
    """Set up an automation context for testing."""
    project_id = "4ea6a03993"
    branch_name = "main"

    model_id: str = "9ae1ffbcf8"
    version_id: str = "4110e33baa"

    automation_name = crypto_random_string(10)
    automation_id = crypto_random_string(10)
    automation_revision_id = crypto_random_string(10)

    register_new_automation(
        project_id,
        model_id,
        test_client,
        automation_id,
        automation_name,
        automation_revision_id,
    )

    automation_run_id = crypto_random_string(10)
    function_id = crypto_random_string(10)
    # function_revision = crypto_random_string(10)
    return AutomationRunData(
        project_id=project_id,
        model_id=model_id,
        branch_name=branch_name,
        version_id=version_id,
        speckle_server_url=speckle_server_url,
        automation_id=automation_id,
        automation_revision_id=automation_revision_id,
        automation_run_id=automation_run_id,
        function_id=function_id,
        function_name=crypto_random_string(10),
        function_logo=None,
    )


@pytest.fixture()
def automation_context(
    automation_run_data: AutomationRunData, speckle_token: str
) -> AutomationContext:
    automation_context = AutomationContext.initialize(
        automation_run_data, speckle_token
    )
    return automation_context


def test_get_commit_data(automation_context: AutomationContext):
    result = get_commit_data(automation_context)
    assert isinstance(result, dict)


def test_get_ref_obj_data(automation_context: AutomationContext):
    result = get_ref_obj_data(automation_context, "0d2ddd825a8f822c787f5817f922e0f0")
    assert isinstance(result, dict)


def test_get_ref_obj_data_none(automation_context: AutomationContext):
    try:
        get_ref_obj_data(automation_context, "")
        assert False
    except SpeckleException:
        assert True


def test_query_version_info_with_empty_project(automation_context: AutomationContext):
    result = query_version_info(automation_context, {})

    assert isinstance(result["coords"], list) and len(result["coords"]) == 2
    assert isinstance(result["angle_rad"], float)
    assert isinstance(result["project_units"], Units)


def test_query_version_info_with_wrong_proj_info(automation_context: AutomationContext):
    try:
        query_version_info(automation_context, {"info": Base()})
        assert False
    except SpeckleException:
        assert True


def test_query_units_info_fake_project(automation_context: AutomationContext):
    result = query_units_info(automation_context, {"info": Base()})
    assert result == Units.m


def test_query_units_info(automation_context: AutomationContext):
    project = get_commit_data(automation_context)
    result = query_units_info(automation_context, project)
    assert result == Units.mm


def test_get_units_from_first_display_value(automation_context: AutomationContext):
    project = get_commit_data(automation_context)
    result = get_units_from_first_display_value(automation_context, project)
    assert result == Units.mm
