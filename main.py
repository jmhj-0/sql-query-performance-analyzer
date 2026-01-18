import argparse
import os
from pathlib import Path
from analyzer import analyze_query, benchmark_query, list_history, save_to_history
from web import create_app
from utils import setup_logging
from config import LOG_LEVEL


def main() -> None:
    setup_logging(LOG_LEVEL)
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
        app = create_app()
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
        import difflib
        diff = difflib.unified_diff(analysis1.split('\n'), analysis2.split('\n'), fromfile='Query1', tofile='Query2', lineterm='')
        print("\nDifferences:")
        print('\n'.join(diff))
        return

    queries = []
    if args.file:
        try:
            file_path = Path(args.file)
            content = file_path.read_text()
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
            import json
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