"""Unit tests for utils_other."""
from utils.utils_other import (
    cut_off_non_numeric_string,
    split_list_by_repeated_elements,
)


def test_cut_off_non_numeric_string():
    """Unit test for cut_off_non_numeric_string."""
    result = cut_off_non_numeric_string("1234/[^\d.-]/g, ''x x 1234")

    symbols = r"/[^\d.-]/g, ''"
    assert isinstance(result, str)
    assert len(result) == 4
    for s in symbols:
        assert s not in result


def test_split_list_by_repeated_elements_no_values():
    """Unit test for split_list_by_repeated_elements."""
    values = []
    lists = [[1, 2, 3], ["a", "b"]]
    result = split_list_by_repeated_elements(values, lists)
    assert result == lists


def test_split_list_by_repeated_elements():
    """Unit test for split_list_by_repeated_elements."""
    values = [4, 5, 6, 6, 7, 8]
    lists = [[1, 2, 3], ["a", "b"]]
    result = split_list_by_repeated_elements(values, lists)
    assert len(result) == 4
    assert [4, 5, 6] in result and [6, 7, 8] in result
