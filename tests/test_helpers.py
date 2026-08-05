import re

from cmdfilter.helpers import format_table_to_str, is_re_match_of_str


def test_is_re_match_of_str_requires_all_groups_to_be_strings() -> None:
    assert is_re_match_of_str(re.match(r"(ab)(cd)", "abcd")) is True
    assert is_re_match_of_str(re.match(r"(ab)?(cd)", "cd")) is False
    assert is_re_match_of_str(None) is False


def test_format_table_to_str_builds_header_separator_from_first_row() -> None:
    rendered = format_table_to_str([["id", "name"], [1, "box"]], header=True)

    assert rendered == "id  name  \n--  ----  \n1   box   \n"
