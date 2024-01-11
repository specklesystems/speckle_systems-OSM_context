"""This module contains the business logic of the function.

use the automation_context module to wrap your function in an Autamate context helper
"""

import numpy as np
from pydantic import Field
from speckle_automate import (
    AutomateBase,
    AutomationContext,
    execute_automate_function,
)
from specklepy.objects.other import Collection
from specklepy.objects.units import Units

from utils.utils_osm import get_base_plane, get_buildings, get_nature, get_roads
from utils.utils_other import RESULT_BRANCH
from utils.utils_png import create_image_from_bbox
from utils.utils_server import get_commit_data, query_units_info, query_version_info


class FunctionInputs(AutomateBase):
    """These are function author defined values.

    Automate will make sure to supply them matching the types specified here.
    Please use the pydantic model schema to define your inputs:
    https://docs.pydantic.dev/latest/usage/models/
    """

    radius_in_meters: float = Field(
        title="Radius in meters",
        ge=50,
        le=1000,
        description=(
            "Radius from the Model location," " derived from Revit model lat, lon."
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
    """This is an example Speckle Automate function.

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
        projInfo = query_version_info(automate_context, project)
        lon = np.rad2deg(projInfo["longitude"])
        lat = np.rad2deg(projInfo["latitude"])
        try:
            angle_rad = projInfo["locations"][0]["trueNorth"]
        except:
            angle_rad = 0

        # get units conversion factor
        project_units = query_units_info(automate_context, project)

        # get OSM buildings and roads in given area
        base_plane = get_base_plane(
            lat, lon, function_inputs.radius_in_meters, project_units
        )
        building_base_objects = get_buildings(
            lat, lon, function_inputs.radius_in_meters, angle_rad, project_units
        )
        roads_lines, roads_meshes = get_roads(
            lat, lon, function_inputs.radius_in_meters, angle_rad, project_units
        )
        nature_base_objects = get_nature(
            lat, lon, function_inputs.radius_in_meters, angle_rad, project_units
        )

        # create layers for buildings and roads
        building_layer = Collection(
            elements=building_base_objects,
            units=project_units,
            latitude=lat,
            longitude=lon,
            trueNorth=angle_rad,
            name="Context: Buildings",
            collectionType="BuildingsMeshesLayer",
            sourceData="© OpenStreetMap",
            sourceUrl="https://www.openstreetmap.org/",
        )
        r"""
        roads_line_layer = Collection(
            elements=roads_lines,
            units="m",
            latitude=lat,
            longitude=lon,
            trueNorth=angle_rad,
            name="Context: Roads (Polylines)",
            collectionType="RoadPolyinesLayer",
            sourceData="© OpenStreetMap",
            sourceUrl="https://www.openstreetmap.org/",
        )
        """
        roads_mesh_layer = Collection(
            elements=roads_meshes,
            units=project_units,
            latitude=lat,
            longitude=lon,
            trueNorth=angle_rad,
            name="Context: Roads (Meshes)",
            collectionType="RoadMeshesLayer",
            sourceData="© OpenStreetMap",
            sourceUrl="https://www.openstreetmap.org/",
        )
        nature_layer = Collection(
            elements=nature_base_objects,
            units=project_units,
            latitude=lat,
            longitude=lon,
            trueNorth=angle_rad,
            name="Context: Nature",
            collectionType="NatureMeshesLayer",
            sourceData="© OpenStreetMap",
            sourceUrl="https://www.openstreetmap.org/",
        )

        # add layers to a commit Collection object
        commit_obj = Collection(
            elements=[base_plane, building_layer, roads_mesh_layer, nature_layer],
            units=project_units,
            latitude=lat,
            longitude=lon,
            trueNorth=angle_rad,
            name="Context",
            collectionType="ContextLayer",
            sourceData="© OpenStreetMap",
            sourceUrl="https://www.openstreetmap.org/",
        )

        # create a commit
        new_model_id, new_version_id = automate_context.create_new_version_in_project(
            commit_obj, RESULT_BRANCH, "Context from Automate"
        )
        automate_context.set_context_view([f"{new_model_id}@{new_version_id}"], True)

        if function_inputs.generate_image is True:
            # create and add a basemap png file
            path = create_image_from_bbox(lat, lon, function_inputs.radius_in_meters)
            automate_context.store_file_result(path)

        # automate_context.set_context_view(
        #    resource_ids=[automate_context.automation_run_data.model_id, new_model_id]
        # )
        automate_context.mark_run_success("Created 3D context")
    except Exception as ex:
        automate_context.mark_run_failed(f"Failed to create 3d context cause: {ex}")


def automate_function_without_inputs(automate_context: AutomationContext) -> None:
    """A function example without inputs.

    If your function does not need any input variables,
     besides what the automation context provides,
     the inputs argument can be omitted.
    """
    pass


# make sure to call the function with the executor
if __name__ == "__main__":
    # NOTE: always pass in the automate function by its reference, do not invoke it!

    # pass in the function reference with the inputs schema to the executor
    execute_automate_function(automate_function, FunctionInputs)

    # if the function has no arguments, the executor can handle it like so
    # execute_automate_function(automate_function_without_inputs)
