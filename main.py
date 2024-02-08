"""This module contains the business logic of the function.

use the automation_context module to wrap your function
in an Autamate context helper
"""

from pydantic import Field
from speckle_automate import AutomateBase, AutomationContext, execute_automate_function
from specklepy.objects.other import Collection

from utils.utils_osm import get_base_plane, get_buildings, get_nature, get_roads
from utils.utils_other import OSM_COPYRIGHT, OSM_URL, RESULT_BRANCH
from utils.utils_png import create_image_from_bbox
from utils.utils_server import get_commit_data, query_version_info


class FunctionInputs(AutomateBase):
    """These are function author defined values.

    Automate will make sure to supply them matching the types specified here.
    Please use the pydantic model schema to define your inputs:
    https://docs.pydantic.dev/latest/usage/models/
    """

    radius_meters: float = Field(
        title="Radius in meters",
        ge=50,
        le=1000,
        description=(
            "Radius from the Model location, derived from Revit model lat, lon."
        ),
    )
    generate_image: bool = Field(
        title="Generate a 2d map",
        description=(
            "Enable or disable generation of 2d map, in addition to the 3d model"
        ),
    )


def automate_function(
    automate_context: AutomationContext,
    function_inputs: FunctionInputs,
) -> None:
    """Speckle Automate function generating 2D and 3D Open Street Map context.

    Args:
        automate_context: A context helper object, that carries relevant information
            about the runtime context of this function.
            It gives access to the Speckle project data, that triggered this run.
            It also has conveniece methods attach result data to the Speckle model.
        function_inputs: An instance object matching the defined schema.
    """
    # the context provides a conveniet way, to receive the triggering version
    try:
        project = get_commit_data(automate_context)
        proj_info = query_version_info(automate_context, project)
        coords = proj_info["coords"]
        project_units = proj_info["project_units"]

        # get OSM context from the given area
        inputs_query = [
            coords,
            function_inputs.radius_meters,
            proj_info["angle_rad"],
            project_units,
        ]
        base_plane = get_base_plane(*inputs_query)
        building_base_objects = get_buildings(*inputs_query)
        roads_lines, roads_meshes = get_roads(*inputs_query)
        nature_base_objects = get_nature(*inputs_query)

        # create layers for buildings and roads
        inputs_base = {
            "units": project_units,
            "latitude": coords[0],
            "longitude": coords[1],
            "trueNorth": proj_info["angle_rad"],
            "sourceData": OSM_COPYRIGHT,
            "sourceUrl": OSM_URL,
        }
        building_layer = Collection(
            elements=building_base_objects,
            name="Context: Buildings",
            collectionType="BuildingsMeshesLayer",
            **inputs_base,
        )
        roads_mesh_layer = Collection(
            elements=roads_meshes,
            name="Context: Roads (Meshes)",
            collectionType="RoadMeshesLayer",
            **inputs_base,
        )
        nature_layer = Collection(
            elements=nature_base_objects,
            name="Context: Nature",
            collectionType="NatureMeshesLayer",
            **inputs_base,
        )

        # add layers to a commit Collection object
        commit_obj = Collection(
            elements=[
                base_plane,
                building_layer,
                roads_mesh_layer,
                nature_layer,
            ],
            name="Context",
            collectionType="ContextLayer",
            **inputs_base,
        )

        # create a commit
        (
            new_model_id,
            new_version_id,
        ) = automate_context.create_new_version_in_project(
            commit_obj,
            RESULT_BRANCH,
            "Context from Automate",
        )
        # set Automate context view
        automate_context.set_context_view(
            [f"{new_model_id}@{new_version_id}"],
            include_source_model_version=True,
        )

        # create and add a basemap png file (if toggled)
        if function_inputs.generate_image is True:
            path = create_image_from_bbox(
                coords,
                function_inputs.radius_meters,
            )
            automate_context.store_file_result(path)

        automate_context.mark_run_success("Created 3D context")
    except Exception as ex:
        automate_context.mark_run_failed(f"Failed to create 3d context cause: {ex}")


# make sure to call the function with the executor
if __name__ == "__main__":
    # NOTE: always pass in the automate function by its reference, do not invoke it!

    # pass in the function reference with the inputs schema to the executor
    execute_automate_function(automate_function, FunctionInputs)
