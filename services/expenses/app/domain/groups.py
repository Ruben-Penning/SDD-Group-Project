"""Rules for groups and members. Pure functions: no database or HTTP imports."""

MAX_NAME_LENGTH = 100


class InvalidGroupError(ValueError):
    """A group or member that breaks a business rule (the API turns it into a 400)."""


def clean_name(name: str, what: str) -> str:
    """Trim the name and check it is not empty or too long. `what` is "group" or "member"."""
    name = name.strip()
    if not name:
        raise InvalidGroupError(f"{what} name must not be empty")
    if len(name) > MAX_NAME_LENGTH:
        raise InvalidGroupError(f"{what} name must be at most {MAX_NAME_LENGTH} characters")
    return name


def check_member_name_is_new(name: str, existing_names: list[str]) -> None:
    """Names are unique within a group, ignoring case ("Ana" and "ana" are the same person).

    Checked here so SQLite (tests) and SQL Server (case-insensitive) behave the same.
    """
    if name.casefold() in {existing.casefold() for existing in existing_names}:
        raise InvalidGroupError(f"a member named {name!r} already exists in this group")
