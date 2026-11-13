import pytest

from app.domain.groups import InvalidGroupError, check_member_name_is_new, clean_name


def test_clean_name_trims_spaces():
    assert clean_name("  Lisbon trip  ", "group") == "Lisbon trip"


@pytest.mark.parametrize("name", ["", "   "])
def test_empty_name_is_rejected(name):
    with pytest.raises(InvalidGroupError, match="group name must not be empty"):
        clean_name(name, "group")


def test_too_long_name_is_rejected():
    with pytest.raises(InvalidGroupError, match="at most 100"):
        clean_name("x" * 101, "member")


def test_100_characters_is_allowed():
    assert clean_name("x" * 100, "member") == "x" * 100


def test_new_member_name_passes():
    check_member_name_is_new("Cleo", ["Ana", "Ben"])


@pytest.mark.parametrize("name", ["Ana", "ana", "ANA"])
def test_duplicate_member_name_is_rejected_ignoring_case(name):
    with pytest.raises(InvalidGroupError, match="already exists"):
        check_member_name_is_new(name, ["Ana", "Ben"])
