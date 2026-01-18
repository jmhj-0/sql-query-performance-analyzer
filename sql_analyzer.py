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
    <head>
    <title>SQL Query Analyzer</title>
    <style>
    body {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        background: linear-gradient(135deg, #1a1a2e, #16213e);
        color: #ffffff;
        margin: 0;
        padding: 20px;
        min-height: 100vh;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        animation: fadeIn 1s ease-in;
    }
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    h1 {
        color: #8b5cf6;
        text-align: center;
        margin-bottom: 30px;
        font-size: 2.5em;
        text-shadow: 0 0 10px rgba(139, 92, 246, 0.5);
        animation: glow 2s ease-in-out infinite alternate;
    }
    @keyframes glow {
        from { text-shadow: 0 0 10px rgba(139, 92, 246, 0.5); }
        to { text-shadow: 0 0 20px rgba(139, 92, 246, 0.8); }
    }
    form {
        background: rgba(255, 255, 255, 0.1);
        padding: 30px;
        border-radius: 15px;
        box-shadow: 0 8px 32px rgba(139, 92, 246, 0.3);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.2);
        max-width: 600px;
        width: 100%;
        animation: slideUp 0.8s ease-out;
    }
    @keyframes slideUp {
        from { transform: translateY(30px); opacity: 0; }
        to { transform: translateY(0); opacity: 1; }
    }
    label {
        display: block;
        margin-top: 15px;
        margin-bottom: 5px;
        color: #e0e7ff;
        font-weight: 500;
    }
    textarea, select, input[type="text"] {
        width: 100%;
        padding: 12px;
        border: 2px solid #8b5cf6;
        border-radius: 8px;
        background: rgba(255, 255, 255, 0.1);
        color: #ffffff;
        font-size: 16px;
        transition: all 0.3s ease;
        box-sizing: border-box;
    }
    textarea:focus, select:focus, input[type="text"]:focus {
        border-color: #a78bfa;
        box-shadow: 0 0 10px rgba(139, 92, 246, 0.5);
        outline: none;
    }
    input[type="checkbox"] {
        margin-right: 10px;
        transform: scale(1.2);
        accent-color: #8b5cf6;
    }
    input[type="submit"] {
        background: linear-gradient(45deg, #8b5cf6, #a78bfa);
        color: white;
        border: none;
        padding: 15px 30px;
        border-radius: 25px;
        cursor: pointer;
        font-size: 18px;
        font-weight: bold;
        margin-top: 20px;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(139, 92, 246, 0.4);
    }
    input[type="submit"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(139, 92, 246, 0.6);
        background: linear-gradient(45deg, #a78bfa, #c4b5fd);
    }
    input[type="submit"]:active {
        transform: translateY(0);
    }
    </style>
    </head>
    <body>
    <h1>SQL Query Performance Analyzer</h1>
    <form method="post" action="/analyze">
    <label>Query:</label><br>
    <textarea name="query" rows="5" cols="50" placeholder="Enter your SQL query here..."></textarea><br>
    <label>Dialect:</label>
    <select name="dialect">
    <option value="mysql">MySQL</option>
    <option value="postgresql">PostgreSQL</option>
    <option value="sqlite">SQLite</option>
    <option value="sqlserver">SQL Server (T-SQL)</option>
    <option value="oracle">Oracle (PL-SQL)</option>
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
        bench_html = ""
        if benchmark:
            bench = benchmark_query(query)
            bench_html = f"<h2>Benchmark</h2><p>{bench}</p>"
        analysis_list = "".join(f"<li>{line}</li>" for line in analysis.split('\n'))
        html = f"""
        <html>
        <head>
        <title>Analysis Result</title>
        <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1a1a2e, #16213e);
            color: #ffffff;
            margin: 0;
            padding: 20px;
            min-height: 100vh;
            animation: fadeIn 1s ease-in;
        }}
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(20px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        h1, h2 {{
            color: #8b5cf6;
            text-shadow: 0 0 10px rgba(139, 92, 246, 0.5);
        }}
        h1 {{
            text-align: center;
            font-size: 2.5em;
            animation: glow 2s ease-in-out infinite alternate;
        }}
        @keyframes glow {{
            from {{ text-shadow: 0 0 10px rgba(139, 92, 246, 0.5); }}
            to {{ text-shadow: 0 0 20px rgba(139, 92, 246, 0.8); }}
        }}
        .container {{
            max-width: 800px;
            margin: 0 auto;
            background: rgba(255, 255, 255, 0.1);
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 8px 32px rgba(139, 92, 246, 0.3);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.2);
            animation: slideUp 0.8s ease-out;
        }}
        @keyframes slideUp {{
            from {{ transform: translateY(30px); opacity: 0; }}
            to {{ transform: translateY(0); opacity: 1; }}
        }}
        p {{
            margin: 10px 0;
            color: #e0e7ff;
        }}
        ul {{
            list-style-type: none;
            padding: 0;
        }}
        li {{
            background: rgba(139, 92, 246, 0.1);
            margin: 10px 0;
            padding: 15px;
            border-radius: 8px;
            border-left: 4px solid #8b5cf6;
            transition: all 0.3s ease;
        }}
        li:hover {{
            background: rgba(139, 92, 246, 0.2);
            transform: translateX(5px);
        }}
        a {{
            display: inline-block;
            background: linear-gradient(45deg, #8b5cf6, #a78bfa);
            color: white;
            text-decoration: none;
            padding: 12px 24px;
            border-radius: 25px;
            margin-top: 20px;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(139, 92, 246, 0.4);
        }}
        a:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(139, 92, 246, 0.6);
            background: linear-gradient(45deg, #a78bfa, #c4b5fd);
        }}
        </style>
        </head>
        <body>
        <div class="container">
        <h1>Analysis Result</h1>
        <p><strong>Query:</strong> {query}</p>
        <p><strong>Dialect:</strong> {dialect}</p>
        <p><strong>Version:</strong> {version}</p>
        <h2>Analysis</h2>
        <ul>
        {analysis_list}
        </ul>
        {bench_html}
        <a href="/">Analyze another query</a>
        </div>
        </body>
        </html>
        """
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
    Parse and analyze the SQL query/script for performance optimizations.
    Handles multiple statements in longer scripts.
    """
    parsed = sqlparse.parse(query)
    if not parsed:
        return "Invalid SQL query."

    all_suggestions = []
    statement_count = len(parsed)

    # Overall complexity for the script
    all_suggestions.append(f"Script contains {statement_count} statement(s).")
    all_suggestions.append(calculate_complexity_score(query))

    for i, stmt in enumerate(parsed, 1):
        if not str(stmt).strip():
            continue
        suggestions = []
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

        # Basic analysis: check for SELECT without WHERE (full table scan)
        if 'SELECT' in query_upper and 'WHERE' not in query_upper:
            suggestions.append("Warning: SELECT query without WHERE clause may perform full table scan. Consider adding filters or indexes.")

        # Check for JOINs and suggest indexes on join keys
        if 'JOIN' in query_upper:
            if 'ON' in query_upper:
                suggestions.append("Consider adding indexes on JOIN keys (columns in ON clauses) to improve join performance.")
            else:
                suggestions.append("JOIN without ON clause detected; ensure proper join conditions.")

        # Check for subqueries
        if 'SELECT' in query_upper and '(' in str(stmt) and ')' in str(stmt):
            suggestions.append("Subqueries detected. Consider rewriting as JOINs if possible for better performance.")

        # Check for CTEs (Common Table Expressions)
        if 'WITH' in query_upper:
            suggestions.append("CTEs (WITH clauses) detected. Ensure they are optimized; recursive CTEs can be expensive.")

        # Check for window functions
        if 'OVER (' in query_upper:
            suggestions.append("Window functions detected. Ensure proper indexing on PARTITION BY and ORDER BY columns.")

        # Check for LIKE with leading wildcard
        if 'LIKE' in query_upper and ("'%" in str(stmt) or "\"%" in str(stmt)):
            suggestions.append("LIKE with leading '%' cannot use indexes efficiently. Consider full-text search.")

        # Check for ORDER BY without LIMIT/TOP
        if 'ORDER BY' in query_upper:
            if dialect == 'sqlserver':
                if 'TOP' not in query_upper:
                    suggestions.append("ORDER BY without TOP may be slow on large tables. Consider adding TOP or indexing.")
            else:
                if 'LIMIT' not in query_upper and 'FETCH' not in query_upper:
                    suggestions.append("ORDER BY without LIMIT/FETCH may be slow on large tables. Consider adding LIMIT or indexing.")

        # Check for DISTINCT without WHERE
        if 'DISTINCT' in query_upper and 'WHERE' not in query_upper:
            suggestions.append("DISTINCT without WHERE may scan the entire table. Ensure it's necessary.")

        # Check for UNION without ALL
        if 'UNION' in query_upper and 'ALL' not in query_upper:
            suggestions.append("UNION removes duplicates, which can be slow. Use UNION ALL if duplicates are acceptable.")

        # Check for functions on columns in WHERE
        where_part = str(stmt).upper().split('WHERE')[-1] if 'WHERE' in query_upper else ""
        if any(func in where_part for func in ['UPPER(', 'LOWER(', 'SUBSTR(', 'DATE(', 'YEAR(']):
            msg = "Functions on columns in WHERE clause may prevent index usage."
            if dialect == 'mysql' and parse_version(version) >= 5.7:
                msg += " Consider generated columns for indexing."
            elif dialect == 'sqlserver':
                msg += " Consider computed columns."
            elif dialect == 'postgresql':
                msg += " Consider expression indexes."
            elif dialect == 'oracle':
                msg += " Consider function-based indexes."
            suggestions.append(msg)

        # Check for IN with many values
        if 'IN (' in query_upper and str(stmt).count(',') > 10:
            suggestions.append("Large IN lists can be slow. Consider JOIN or temporary tables.")

        # Dialect-specific checks
        if dialect == 'postgresql':
            if 'ILIKE' in query_upper:
                suggestions.append("ILIKE is case-insensitive; ensure proper indexing or use text search.")
            if 'ARRAY' in query_upper:
                suggestions.append("Array operations detected; ensure GIN indexes for array columns.")
        elif dialect == 'sqlserver':
            if 'MERGE' in query_upper:
                suggestions.append("MERGE statement detected; ensure proper indexing on join keys.")
        elif dialect == 'oracle':
            if 'CONNECT BY' in query_upper:
                suggestions.append("Hierarchical query detected; ensure proper indexing for performance.")
        elif dialect == 'mysql':
            if 'STRAIGHT_JOIN' in query_upper:
                suggestions.append("STRAIGHT_JOIN forces join order; use only if optimizer is incorrect.")

        # Security checks
        if '+' in str(stmt) and ('WHERE' in query_upper or 'SET' in query_upper):
            suggestions.append("Potential SQL injection risk: String concatenation in WHERE/SET clauses.")
        if 'UNION SELECT' in query_upper and any(char.isdigit() for char in str(stmt).split('UNION SELECT')[1][:10]):
            suggestions.append("Potential SQL injection: Suspicious UNION SELECT.")
        if "'" in str(stmt) and 'WHERE' in query_upper and '?' not in str(stmt) and ':' not in str(stmt):
            suggestions.append("Consider parameterized queries to prevent SQL injection.")

        if len(suggestions) == 1:  # Only statement type
            suggestions.append("No obvious issues detected in this statement.")

        all_suggestions.extend(suggestions)

    if len(all_suggestions) == 2:  # Only count and complexity
        all_suggestions.append("No obvious performance issues detected in the script.")

    return "\n".join(all_suggestions)

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
    parser.add_argument('--dialect', choices=['mysql', 'postgresql', 'sqlite', 'sqlserver', 'oracle'], default='mysql', help='SQL dialect (default: mysql)')
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