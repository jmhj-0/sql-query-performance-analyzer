import pytest
from sql_query_performance_analyzer.analyzer import analyze_query, calculate_complexity_score
from sql_query_performance_analyzer.exceptions import InvalidSQLQueryError


def test_calculate_complexity_score():
    query = "SELECT * FROM users WHERE id = 1"
    score = calculate_complexity_score(query)
    assert "Complexity Score" in score


def test_analyze_query_valid():
    query = "SELECT * FROM users"
    result = analyze_query(query)
    assert "Script contains 1 statement(s)" in result
    assert "SELECT" in result


def test_analyze_query_invalid():
    with pytest.raises(InvalidSQLQueryError):
        analyze_query("INVALID QUERY")


def test_analyze_query_multiple_statements():
    query = "SELECT * FROM users; UPDATE users SET name = 'test' WHERE id = 1;"
    result = analyze_query(query)
    assert "Script contains 2 statement(s)" in result
    assert "Statement 1: SELECT" in result
    assert "Statement 2: UPDATE" in result