from gql import gql
from specklepy.logging.exceptions import SpeckleException, SpeckleInvalidUnitException
from specklepy.objects.units import Units, get_units_from_string


def get_commit_data(automate_context):
    automation_run_data = automate_context.automation_run_data
    # get referencedObject
    query = gql(
        """
        query Stream($project_id: String!, $model_id: String!, $version_id: String!) {
            project(id:$project_id) {
                model(id: $model_id) {
                    version(id: $version_id) {
                        referencedObject
                    }
                }
            }
        }
    """
    )
    client = automate_context.speckle_client
    params = {
        "project_id": automation_run_data.project_id,
        "model_id": automation_run_data.model_id,
        "version_id": automation_run_data.version_id,
    }
    project = client.httpclient.execute(query, params)
    ref_obj = project["project"]["model"]["version"]["referencedObject"]
    # get Project data
    query = gql(
        """
        query Stream($project_id: String!, $ref_id: String!) {
            stream(id: $project_id){
                object(id: $ref_id){
                data
                }
            }
        }
    """
    )
    params = {
        "project_id": automation_run_data.project_id,
        "ref_id": ref_obj,
    }
    project = client.httpclient.execute(query, params)
    return project["stream"]["object"]["data"]


def get_ref_obj_data(automate_context, ref_obj: str):
    automation_run_data = automate_context.automation_run_data
    client = automate_context.speckle_client
    # get Project data
    query = gql(
        """
        query Stream($project_id: String!, $ref_id: String!) {
            stream(id: $project_id){
                object(id: $ref_id){
                data
                }
            }
        }
    """
    )
    params = {
        "project_id": automation_run_data.project_id,
        "ref_id": ref_obj,
    }
    ref_obj = client.httpclient.execute(query, params)
    return ref_obj["stream"]["object"]["data"]


def query_version_info(automate_context, project):
    try:
        projInfo = project["info"]
    except KeyError as e:
        print(e)
        base = automate_context.receive_version()
        projInfo = base["info"]
        if not projInfo.speckle_type.endswith("Revit.ProjectInfo"):
            raise SpeckleException("Not a valid 'Revit.ProjectInfo' provided")
    return projInfo


def query_units_info(automate_context, project):
    try:
        display_object_units = traverse_to_first_display_value(
            automate_context, project
        )
        if display_object_units:
            return display_object_units
    except KeyError as e:
        print(f"Error: {e}")
        pass
    return Units.m


def traverse_to_first_display_value(automate_context, base_obj: dict):
    if "Revit.Parameter" in base_obj["speckle_type"]:
        return

    displayValue = None
    if "displayValue" in base_obj:
        displayValue = base_obj["displayValue"]
    elif "@displayValue" in base_obj:
        displayValue = base_obj["@displayValue"]

    if isinstance(displayValue, list):
        for el in displayValue:
            try:
                if el["speckle_type"] == "reference":
                    item = get_ref_obj_data(automate_context, el["referencedId"])
                    if isinstance(item, dict) and "units" in item:
                        units = get_units_from_string(item["units"])
                        return units
                elif "units" in el:
                    units = get_units_from_string(el["units"])
                    return units
            except SpeckleInvalidUnitException as e:
                pass

    if "elements" in base_obj and isinstance(base_obj["elements"], list):
        for el in base_obj["elements"]:
            if el["speckle_type"] == "reference":
                element = get_ref_obj_data(automate_context, el["referencedId"])
                units = traverse_to_first_display_value(automate_context, element)
                if isinstance(units, Units):
                    return units
