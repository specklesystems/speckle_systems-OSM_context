"""Utils for the Automate function."""
from copy import copy

RESULT_BRANCH = "OSM context"
COLOR_ROAD = (255 << 24) + (30 << 16) + (30 << 8) + 30  # argb # noqa: WPS432, WPS221
COLOR_BLD = (255 << 24) + (230 << 16) + (230 << 8) + 230  # argb# noqa: E731
COLOR_GREEN = (255 << 24) + (25 << 16) + (50 << 8) + 13  # argb# noqa: E731
COLOR_TREE_BASE = (255 << 24) + (18 << 16) + (30 << 8) + 8  # argb# noqa: E731
COLOR_TREE_BASE_BROWN = (255 << 24) + (15 << 16) + (10 << 8) + 2  # argb# noqa: E731
COLOR_BASE = color = (255 << 24) + (80 << 16) + (80 << 8) + 80# noqa: E731
COLOR_VISIBILITY = (255 << 24) + (255 << 16) + (10 << 8) + 10  # argb# noqa: E731
OSM_URL = "https://www.openstreetmap.org/"
OSM_COPYRIGHT = "© OpenStreetMap"


def cut_off_non_numeric_string(text: str) -> str:
    """Clean string from trailing non-numeric symbols.

    Args:
        text: original text.

    Returns:
        Text cleared of trailing symbols.
    """
    symbols = r"/[^\d.-]/g, ''"
    text_part = text
    for symb in symbols:
        text_part = text_part.split(symb)[0]

    new_text = ""
    for part in text_part:
        if part in "0123456789.":
            new_text += part

    return new_text


def split_list_by_repeated_elements(
    original_list: list,
    lsts: list[list],
) -> list[list]:
    """Split values into separate lists by the repeated value.

    Args:
        original_list: list of values to split.
        lsts: existing lists to add to.

    Returns:
        Lists separated by repeated values.
    """
    if len(original_list) > 1:
        lsts.append([])
    else:
        return lsts

    for i, list_item in enumerate(original_list):  # noqa: WPS111 because....
        if list_item not in lsts[-1]:
            lsts[-1].append(list_item)
        else:
            if len(lsts[-1]) <= 1:
                lsts.pop(len(lsts) - 1)

            # modeify original list
            original_list = copy(original_list[i:])
            lsts = split_list_by_repeated_elements(original_list, lsts)
    return lsts
