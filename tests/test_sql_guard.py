import pytest

from db_lens_mcp.domain.sql_guard import SqlGuard
from db_lens_mcp.errors import SafetyError


class Select:
    def __init__(self, referenced_tables=None):
        self.referenced_tables = referenced_tables or []


class With:
    def __init__(self, inner):
        self.this = inner
        self.referenced_tables = inner.referenced_tables


class Insert:
    pass


def parser_for(expression):
    def parse(sql):
        return expression

    return parse


def test_accepts_single_select_and_extracts_tables() -> None:
    guard = SqlGuard(parser=parser_for(Select(["orders"])))

    result = guard.validate_select("select * from orders")

    assert result.sql == "select * from orders"
    assert result.referenced_tables == ["orders"]
    assert result.has_placeholders is False


def test_accepts_with_select() -> None:
    guard = SqlGuard(parser=parser_for(With(Select(["orders"]))))

    result = guard.validate_select("with recent as (select * from orders) select * from recent")

    assert result.referenced_tables == ["orders"]


def test_rejects_non_select() -> None:
    guard = SqlGuard(parser=parser_for(Insert()))

    with pytest.raises(SafetyError, match="Only single SELECT"):
        guard.validate_select("insert into orders(id) values(1)")


def test_rejects_user_supplied_explain() -> None:
    guard = SqlGuard(parser=parser_for(Insert()))

    with pytest.raises(SafetyError, match="Only single SELECT"):
        guard.validate_select("explain select * from orders")


def test_rejects_multi_statement() -> None:
    guard = SqlGuard(parser=parser_for(Select(["orders"])))

    with pytest.raises(SafetyError, match="Only single SELECT"):
        guard.validate_select("select * from orders; drop table orders")


def test_allows_single_trailing_semicolon() -> None:
    guard = SqlGuard(parser=parser_for(Select(["orders"])))

    result = guard.validate_select("select * from orders;")

    assert result.referenced_tables == ["orders"]


def test_rejects_empty_sql() -> None:
    guard = SqlGuard(parser=parser_for(Select(["orders"])))

    with pytest.raises(SafetyError, match="must not be empty"):
        guard.validate_select(" ")


def test_tracks_placeholders_and_params() -> None:
    guard = SqlGuard(parser=parser_for(Select(["orders"])))

    result = guard.validate_select("select * from orders where user_id = ?", params=[123])

    assert result.has_placeholders is True
    assert result.params == [123]
