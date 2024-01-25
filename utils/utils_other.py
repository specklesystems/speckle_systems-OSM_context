from copy import copy

RESULT_BRANCH = "OSM context"
COLOR_ROAD = (255 << 24) + (30 << 16) + (30 << 8) + 30  # argb
COLOR_BLD = (255 << 24) + (230 << 16) + (230 << 8) + 230  # argb
COLOR_GREEN = (255 << 24) + (25 << 16) + (50 << 8) + 13  # argb
COLOR_TREE_BASE = (255 << 24) + (18 << 16) + (30 << 8) + 8  # argb
COLOR_TREE_BASE_BROWN = (255 << 24) + (15 << 16) + (10 << 8) + 2  # argb
COLOR_BASE = color = (255 << 24) + (80 << 16) + (80 << 8) + 80
COLOR_VISIBILITY = (255 << 24) + (255 << 16) + (10 << 8) + 10  # argb


def cut_off_non_numeric_string(text: str) -> str:
    """Clean string from non-numeric symbols."""
    symbols = r"/[^\d.-]/g, ''"
    text_part = text
    for s in symbols:
        text_part = text_part.split(s)[0]

    new_text = ""
    for t in text_part:
        if t in "0123456789.":
            new_text += t

    return new_text


def split_list_by_repeated_elements(vals: list, lsts: list[list]) -> list[list]:
    """Split values into separate lists by the repeated value."""
    if len(vals) > 1:
        lsts.append([])
    else:
        return lsts

    for i, v in enumerate(vals):
        if v not in lsts[len(lsts) - 1]:
            lsts[len(lsts) - 1].append(v)
        else:
            if len(lsts[len(lsts) - 1]) <= 1:
                lsts.pop(len(lsts) - 1)
            vals = copy(vals[i:])
            lsts = split_list_by_repeated_elements(vals, lsts)
    return lsts
