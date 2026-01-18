class SQLAnalysisError(Exception):
    """Base exception for SQL analysis errors."""
    pass


class InvalidSQLQueryError(SQLAnalysisError):
    """Raised when the SQL query is invalid."""
    pass


class BenchmarkError(SQLAnalysisError):
    """Raised when benchmarking fails."""
    pass