import sqlparse
import argparse
import sqlite3
import time
import os
import difflib
import json
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/')
def index():
    html = """
    <html>
    <head><title>SQL Query Analyzer</title></head>
    <body>
    <h1>SQL Query Performance Analyzer</h1>
    <form method="post" action="/analyze">
    <label>Query:</label><br>
    <textarea name="query" rows="5" cols="50"></textarea><br>
    <label>Dialect:</label>
    <select name="dialect">
    <option value="mysql">MySQL</option>
    <option value="postgresql">PostgreSQL</option>
    <option value="sqlite">SQLite</option>
    <option value="sqlserver">SQL Server</option>
    </select><br>
    <label>Version:</label>
    <input type="text" name="version" value="latest"><br>
    <label>Benchmark:</label>
    <input type="checkbox" name="benchmark"><br>
    <input type="submit" value="Analyze">
    </form>
    </body>
    </html>
    """
    return html

@app.route('/analyze', methods=['POST'])
def analyze_endpoint():
    if request.is_json:
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({'error': 'Query is required'}), 400
        query = data['query']
        dialect = data.get('dialect', 'mysql')
        version = data.get('version', 'latest')
        benchmark = data.get('benchmark', False)
    else:
        query = request.form.get('query')
        dialect = request.form.get('dialect', 'mysql')
        version = request.form.get('version', 'latest')
        benchmark = 'benchmark' in request.form

    if not query:
        if request.is_json:
            return jsonify({'error': 'Query is required'}), 400
        else:
            return "Query is required", 400

    analysis = analyze_query(query, dialect, version)
    if request.is_json:
        result = {'analysis': analysis.split('\n')}
        if benchmark:
            bench = benchmark_query(query)
            result['benchmark'] = bench
        return jsonify(result)
    else:
        # Return HTML
        html = f"""
        <html>
        <head><title>Analysis Result</title></head>
        <body>
        <h1>Analysis Result</h1>
        <p><strong>Query:</strong> {query}</p>
        <p><strong>Dialect:</strong> {dialect}</p>
        <p><strong>Version:</strong> {version}</p>
        <h2>Analysis</h2>
        <ul>
        """
        for line in analysis.split('\n'):
            html += f"<li>{line}</li>"
        html += "</ul>"
        if benchmark:
            bench = benchmark_query(query)
            html += f"<h2>Benchmark</h2><p>{bench}</p>"
        html += '<a href="/">Analyze another query</a></body></html>'
        return html

def parse_version(v):
    if v == 'latest':
        return float('inf')
    try:
        return float(v)
    except ValueError:
        # Assume major.minor, take major
        return float(v.split('.')[0])

def init_history_db():
    db_path = 'history.db'
    conn = sqlite3.connect(db_path)
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

def save_to_history(query, analysis, benchmark, dialect, version):
    init_history_db()
    conn = sqlite3.connect('history.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO history (query, analysis, benchmark, timestamp, dialect, version) VALUES (?, ?, ?, ?, ?, ?)',
                   (query, analysis, benchmark, time.strftime('%Y-%m-%d %H:%M:%S'), dialect, version))
    conn.commit()
    conn.close()

def list_history(limit=10):
    if not os.path.exists('history.db'):
        return "No history available."
    conn = sqlite3.connect('history.db')
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

def calculate_complexity_score(query):
    """
    Calculate a complexity score for the query (1-10).
    """
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

def analyze_query(query, dialect='mysql', version='latest'):
    """
    Parse and analyze the SQL query for performance optimizations.
    """
    parsed = sqlparse.parse(query)
    if not parsed:
        return "Invalid SQL query."

    # Get the first statement
    stmt = parsed[0]

    suggestions = []

    # Add complexity score
    suggestions.append(calculate_complexity_score(query))

    # Basic analysis: check for SELECT without WHERE (full table scan)
    query_upper = str(stmt).upper()
    if 'SELECT' in query_upper and 'WHERE' not in query_upper:
        suggestions.append("Warning: SELECT query without WHERE clause may perform full table scan. Consider adding filters or indexes. Explanation: Without a WHERE clause, the database must examine every row in the table, leading to poor performance on large datasets.")

    # Check for JOINs and suggest indexes on join keys
    if 'JOIN' in query_upper:
        # Simple check: look for ON clauses
        if 'ON' in query_upper:
            suggestions.append("Consider adding indexes on JOIN keys (columns in ON clauses) to improve join performance. Explanation: JOINs without indexes on the joined columns require full table scans, significantly slowing down the query.")

    # Check for subqueries
    if 'SELECT' in query_upper and '(' in str(stmt) and ')' in str(stmt):
        suggestions.append("Subqueries detected. Consider rewriting as JOINs if possible for better performance. Explanation: Subqueries may execute multiple times or hinder the optimizer; JOINs often allow better query planning.")

    # Check for LIKE with leading wildcard
    if 'LIKE' in query_upper and ("'%" in str(stmt) or "\"%" in str(stmt)):
        suggestions.append("LIKE with leading '%' cannot use indexes efficiently. Consider full-text search or restructuring.")

    # Check for ORDER BY without LIMIT/TOP
    if 'ORDER BY' in query_upper:
        if dialect == 'sqlserver':
            if 'TOP' not in query_upper:
                suggestions.append("ORDER BY without TOP may be slow on large tables. Consider adding TOP or indexing the ORDER BY columns. Explanation: Sorting large datasets without limits requires processing all rows, consuming excessive memory and time.")
        else:
            if 'LIMIT' not in query_upper:
                suggestions.append("ORDER BY without LIMIT may be slow on large tables. Consider adding LIMIT or indexing the ORDER BY columns. Explanation: Sorting large datasets without limits requires processing all rows, consuming excessive memory and time.")

    # Check for DISTINCT without WHERE
    if 'DISTINCT' in query_upper and 'WHERE' not in query_upper:
        suggestions.append("DISTINCT without WHERE may scan the entire table. Ensure it's necessary.")

    # Check for UNION without ALL
    if 'UNION' in query_upper and 'ALL' not in query_upper:
        suggestions.append("UNION removes duplicates, which can be slow. Use UNION ALL if duplicates are acceptable.")

    # Check for functions on columns in WHERE (potential index misuse)
    where_part = str(stmt).upper().split('WHERE')[-1] if 'WHERE' in query_upper else ""
    if any(func in where_part for func in ['UPPER(', 'LOWER(', 'SUBSTR(', 'DATE(', 'YEAR(']):
        msg = "Functions on columns in WHERE clause may prevent index usage."
        if dialect == 'mysql' and parse_version(version) >= 5.7:
            msg += " Consider generated columns for indexing (MySQL 5.7+)."
        elif dialect == 'sqlserver':
            msg += " Consider computed columns or persisted computed columns for indexing."
        else:
            msg += " Consider restructuring the query."
        suggestions.append(msg)

    # Check for IN with many values
    if 'IN (' in query_upper and str(stmt).count(',') > 10:  # rough check
        suggestions.append("Large IN lists can be slow. Consider JOIN or temporary tables.")

    # Security checks
    # Check for potential SQL injection via string concatenation
    if '+' in str(stmt) and ('WHERE' in query_upper or 'SET' in query_upper):
        suggestions.append("Potential SQL injection risk: String concatenation in WHERE/SET clauses. Use parameterized queries.")

    # Check for suspicious UNION patterns
    if 'UNION SELECT' in query_upper and any(char.isdigit() for char in str(stmt).split('UNION SELECT')[1][:10]):
        suggestions.append("Potential SQL injection: Suspicious UNION SELECT with numbers. Ensure input is sanitized.")

    # General parameterized query reminder
    if "'" in str(stmt) and 'WHERE' in query_upper and '?' not in str(stmt) and ':' not in str(stmt):
        suggestions.append("Consider using parameterized queries to prevent SQL injection. Avoid embedding user input directly in SQL strings.")

    # Placeholder for more advanced analysis
    if len(suggestions) == 1:  # Only complexity score
        suggestions.append("No obvious performance issues detected.")

    return "\n".join(suggestions)

def benchmark_query(query):
    """
    Benchmark the query against a test SQLite database.
    """
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
        return f"Benchmark error: {e}"
    finally:
        conn.close()

def main():
    parser = argparse.ArgumentParser(description='SQL Query Performance Analyzer')
    parser.add_argument('query', nargs='?', help='SQL query to analyze')
    parser.add_argument('--file', help='File containing SQL queries to analyze (one per line or separated by ;)')
    parser.add_argument('--dialect', choices=['mysql', 'postgresql', 'sqlite', 'sqlserver'], default='mysql', help='SQL dialect (default: mysql)')
    parser.add_argument('--version', default='latest', help='Database version (e.g., 8.0, 2019) (default: latest)')
    parser.add_argument('--benchmark', action='store_true', help='Benchmark the query against a test database')
    parser.add_argument('--list-history', action='store_true', help='List recent query history')
    parser.add_argument('--compare', nargs=2, metavar=('QUERY1', 'QUERY2'), help='Compare two queries side by side')
    parser.add_argument('--export', choices=['json', 'html'], help='Export analysis report in specified format')
    parser.add_argument('--serve', action='store_true', help='Start the REST API server')
    args = parser.parse_args()

    if args.serve:
        port = int(os.environ.get('PORT', 5000))
        print(f"Starting REST API server on http://0.0.0.0:{port}")
        app.run(host='0.0.0.0', port=port, debug=False)
        return

    if args.list_history:
        print(list_history())
        return

    if args.compare:
        query1, query2 = args.compare
        analysis1 = analyze_query(query1, args.dialect, args.version)
        analysis2 = analyze_query(query2, args.dialect, args.version)
        print("Query 1 Analysis:")
        print(analysis1)
        print("\nQuery 2 Analysis:")
        print(analysis2)
        diff = difflib.unified_diff(analysis1.split('\n'), analysis2.split('\n'), fromfile='Query1', tofile='Query2', lineterm='')
        print("\nDifferences:")
        print('\n'.join(diff))
        return

    queries = []
    if args.file:
        try:
            with open(args.file, 'r') as f:
                content = f.read()
                # Split by ; or \n
                queries = [q.strip() for q in content.replace('\n', ';').split(';') if q.strip()]
        except FileNotFoundError:
            print(f"File {args.file} not found.")
            return
    elif args.query:
        queries = [args.query]
    else:
        parser.error("Query, --file, or --compare is required unless --list-history is used")

    if len(queries) == 1:
        # Single query
        analysis = analyze_query(queries[0], args.dialect, args.version)

        bench_result = ""
        if args.benchmark:
            bench = benchmark_query(queries[0])
            bench_result = bench

        if args.export == 'json':
            report = {
                "query": queries[0],
                "dialect": args.dialect,
                "version": args.version,
                "analysis": analysis.split('\n'),
                "benchmark": bench_result
            }
            print(json.dumps(report, indent=2))
        elif args.export == 'html':
            html = f"""<html>
<head><title>SQL Analysis Report</title></head>
<body>
<h1>SQL Query Analysis Report</h1>
<p><strong>Query:</strong> {queries[0]}</p>
<p><strong>Dialect:</strong> {args.dialect}</p>
<p><strong>Version:</strong> {args.version}</p>
<h2>Analysis</h2>
<ul>"""
            for line in analysis.split('\n'):
                html += f"<li>{line}</li>"
            html += "</ul>"
            if bench_result:
                html += f"<h2>Benchmark</h2><p>{bench_result}</p>"
            html += "</body></html>"
            print(html)
        else:
            print("Analysis:")
            print(analysis)
            if args.benchmark:
                print("\n" + bench_result)

        # Save to history
        save_to_history(queries[0], analysis, bench_result, args.dialect, args.version)
    else:
        # Batch analysis
        print("Batch Analysis:")
        for i, query in enumerate(queries, 1):
            print(f"\nQuery {i}: {query}")
            analysis = analyze_query(query, args.dialect, args.version)
            print(analysis)

            bench_result = ""
            if args.benchmark:
                bench = benchmark_query(query)
                print(bench)
                bench_result = bench

            # Save to history
            save_to_history(query, analysis, bench_result, args.dialect, args.version)

if __name__ == "__main__":
    main()