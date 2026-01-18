import sqlite3
import time
from pathlib import Path
from typing import List, Optional
import sqlparse
from .config import HISTORY_DB_PATH
from .exceptions import InvalidSQLQueryError, BenchmarkError
from .utils import parse_version, logger


def init_history_db() -> None:
    """Initialize the history database."""
    conn = sqlite3.connect(HISTORY_DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        query TEXT,
        analysis TEXT,
        benchmark TEXT,
        timestamp TEXT,
        dialect TEXT,
        version TEXT
    )''')
    conn.commit()
    conn.close()


def save_to_history(query: str, analysis: str, benchmark: str,
                   dialect: str, version: str) -> None:
    """Save query analysis to history."""
    init_history_db()
    conn = sqlite3.connect(HISTORY_DB_PATH)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO history (query, analysis, benchmark, timestamp, dialect, version) VALUES (?, ?, ?, ?, ?, ?)',
                   (query, analysis, benchmark, time.strftime('%Y-%m-%d %H:%M:%S'), dialect, version))
    conn.commit()
    conn.close()


def list_history(limit: int = 10) -> str:
    """List recent query history."""
    if not HISTORY_DB_PATH.exists():
        return "No history available."
    conn = sqlite3.connect(HISTORY_DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT id, query, timestamp FROM history ORDER BY id DESC LIMIT ?', (limit,))
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        return "No history available."
    result = "Recent Query History:\n"
    for row in rows:
        result += f"ID {row[0]}: {row[1][:50]}... at {row[2]}\n"
    return result


def calculate_complexity_score(query: str) -> str:
    """Calculate a complexity score for the query (1-10)."""
    score = 0
    query_upper = query.upper()

    # Joins: +1 per JOIN
    score += query_upper.count('JOIN')

    # Subqueries: +2 per SELECT in parentheses (rough)
    if 'SELECT' in query_upper and '(' in query and ')' in query:
        score += 2

    # GROUP BY: +1
    if 'GROUP BY' in query_upper:
        score += 1

    # ORDER BY: +1
    if 'ORDER BY' in query_upper:
        score += 1

    # DISTINCT: +1
    if 'DISTINCT' in query_upper:
        score += 1

    # Functions: +0.5 per function
    functions = ['UPPER(', 'LOWER(', 'SUBSTR(', 'DATE(', 'YEAR(', 'COUNT(', 'SUM(', 'AVG(']
    for func in functions:
        score += 0.5 * query_upper.count(func)

    # Length: +0.1 per 50 chars
    score += len(query) / 500.0

    # Cap at 10
    score = min(10, score)

    # Determine level
    if score <= 3:
        level = "Low"
    elif score <= 6:
        level = "Medium"
    else:
        level = "High"

    return f"Complexity Score: {score:.1f}/10 ({level})"


def analyze_query(query: str, dialect: str = 'mysql', version: str = 'latest') -> str:
    """Parse and analyze the SQL query/script for performance optimizations."""
    parsed = sqlparse.parse(query)
    if not parsed:
        raise InvalidSQLQueryError("Invalid SQL query.")

    all_suggestions: List[str] = []
    statement_count = len(parsed)

    # Overall complexity for the script
    all_suggestions.append(f"Script contains {statement_count} statement(s).")
    all_suggestions.append(calculate_complexity_score(query))

    for i, stmt in enumerate(parsed, 1):
        if not str(stmt).strip():
            continue
        suggestions: List[str] = []
        query_upper = str(stmt).upper()

        # Statement type
        if 'SELECT' in query_upper:
            stmt_type = "SELECT"
        elif 'INSERT' in query_upper:
            stmt_type = "INSERT"
        elif 'UPDATE' in query_upper:
            stmt_type = "UPDATE"
        elif 'DELETE' in query_upper:
            stmt_type = "DELETE"
        elif 'CREATE' in query_upper:
            stmt_type = "CREATE"
        else:
            stmt_type = "Other"
        suggestions.append(f"Statement {i}: {stmt_type}")

        # Basic analysis: check for SELECT without WHERE
        if 'SELECT' in query_upper and 'WHERE' not in query_upper:
            suggestions.append("Warning: SELECT query without WHERE clause may perform full table scan.")

        # Check for JOINs
        if 'JOIN' in query_upper:
            if 'ON' in query_upper:
                suggestions.append("Consider adding indexes on JOIN keys.")
            else:
                suggestions.append("JOIN without ON clause detected.")

        # Check for subqueries
        if 'SELECT' in query_upper and '(' in str(stmt) and ')' in str(stmt):
            suggestions.append("Subqueries detected.")

        # Check for CTEs
        if 'WITH' in query_upper:
            suggestions.append("CTEs detected.")

        # Check for window functions
        if 'OVER (' in query_upper:
            suggestions.append("Window functions detected.")

        # Check for LIKE with leading wildcard
        if 'LIKE' in query_upper and ("'%" in str(stmt) or "\"%" in str(stmt)):
            suggestions.append("LIKE with leading '%' cannot use indexes efficiently.")

        # Check for ORDER BY without LIMIT/TOP
        if 'ORDER BY' in query_upper:
            if dialect == 'sqlserver':
                if 'TOP' not in query_upper:
                    suggestions.append("ORDER BY without TOP may be slow.")
            else:
                if 'LIMIT' not in query_upper and 'FETCH' not in query_upper:
                    suggestions.append("ORDER BY without LIMIT/FETCH may be slow.")

        # Check for DISTINCT without WHERE
        if 'DISTINCT' in query_upper and 'WHERE' not in query_upper:
            suggestions.append("DISTINCT without WHERE may scan the entire table.")

        # Check for UNION without ALL
        if 'UNION' in query_upper and 'ALL' not in query_upper:
            suggestions.append("UNION removes duplicates, which can be slow.")

        # Check for functions on columns in WHERE
        where_part = str(stmt).upper().split('WHERE')[-1] if 'WHERE' in query_upper else ""
        if any(func in where_part for func in ['UPPER(', 'LOWER(', 'SUBSTR(', 'DATE(', 'YEAR(']):
            msg = "Functions on columns in WHERE clause may prevent index usage."
            if dialect == 'mysql' and parse_version(version) >= 5.7:
                msg += " Consider generated columns."
            elif dialect == 'sqlserver':
                msg += " Consider computed columns."
            elif dialect == 'postgresql':
                msg += " Consider expression indexes."
            elif dialect == 'oracle':
                msg += " Consider function-based indexes."
            suggestions.append(msg)

        # Check for IN with many values
        if 'IN (' in query_upper and str(stmt).count(',') > 10:
            suggestions.append("Large IN lists can be slow.")

        # Dialect-specific checks
        if dialect == 'postgresql':
            if 'ILIKE' in query_upper:
                suggestions.append("ILIKE is case-insensitive.")
            if 'ARRAY' in query_upper:
                suggestions.append("Array operations detected.")
        elif dialect == 'sqlserver':
            if 'MERGE' in query_upper:
                suggestions.append("MERGE statement detected.")
        elif dialect == 'oracle':
            if 'CONNECT BY' in query_upper:
                suggestions.append("Hierarchical query detected.")
        elif dialect == 'mysql':
            if 'STRAIGHT_JOIN' in query_upper:
                suggestions.append("STRAIGHT_JOIN forces join order.")

        # Security checks
        if '+' in str(stmt) and ('WHERE' in query_upper or 'SET' in query_upper):
            suggestions.append("Potential SQL injection risk.")
        if 'UNION SELECT' in query_upper and any(char.isdigit() for char in str(stmt).split('UNION SELECT')[1][:10]):
            suggestions.append("Potential SQL injection.")
        if "'" in str(stmt) and 'WHERE' in query_upper and '?' not in str(stmt) and ':' not in str(stmt):
            suggestions.append("Consider parameterized queries.")

        if len(suggestions) == 1:  # Only statement type
            suggestions.append("No obvious issues detected.")

        all_suggestions.extend(suggestions)

    if len(all_suggestions) == 2:  # Only count and complexity
        all_suggestions.append("No obvious issues detected.")

    return "\n".join(all_suggestions)


def benchmark_query(query: str) -> str:
    """Benchmark the query against a test SQLite database."""
    conn = sqlite3.connect(':memory:')
    cursor = conn.cursor()

    # Create sample table
    cursor.execute('''CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, age INTEGER)''')

    # Insert sample data
    for i in range(1000):
        cursor.execute("INSERT INTO users (name, age) VALUES (?, ?)", (f'User{i}', i % 100))
    conn.commit()

    # Time the query
    start = time.time()
    try:
        cursor.execute(query)
        results = cursor.fetchall()
        end = time.time()
        return f"Benchmark: Query executed in {end - start:.4f} seconds. Rows returned: {len(results)}"
    except Exception as e:
        logger.error(f"Benchmark error: {e}")
        raise BenchmarkError(f"Benchmark error: {e}")
    finally:
        conn.close()