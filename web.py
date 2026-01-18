from flask import Flask, request, jsonify
from .analyzer import analyze_query, benchmark_query
from .config import SECRET_KEY, DEBUG
from .utils import logger


def create_app() -> Flask:
    """Application factory for Flask app."""
    app = Flask(__name__)
    app.config['SECRET_KEY'] = SECRET_KEY
    app.config['DEBUG'] = DEBUG

    @app.route('/')
    def index() -> str:
        html = """
        <html>
        <head>
        <title>SQL Query Analyzer</title>
        <style>
        body {{
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
        }}
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(20px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        h1 {{
            color: #8b5cf6;
            text-align: center;
            margin-bottom: 30px;
            font-size: 2.5em;
            text-shadow: 0 0 10px rgba(139, 92, 246, 0.5);
            animation: glow 2s ease-in-out infinite alternate;
        }}
        @keyframes glow {{
            from {{ text-shadow: 0 0 10px rgba(139, 92, 246, 0.5); }}
            to {{ text-shadow: 0 0 20px rgba(139, 92, 246, 0.8); }}
        }}
        form {{
            background: rgba(255, 255, 255, 0.1);
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 8px 32px rgba(139, 92, 246, 0.3);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.2);
            max-width: 600px;
            width: 100%;
            animation: slideUp 0.8s ease-out;
        }}
        @keyframes slideUp {{
            from {{ transform: translateY(30px); opacity: 0; }}
            to {{ transform: translateY(0); opacity: 1; }}
        }}
        label {{
            display: block;
            margin-top: 15px;
            margin-bottom: 5px;
            color: #e0e7ff;
            font-weight: 500;
        }}
        textarea, select, input[type="text"] {{
            width: 100%;
            padding: 12px;
            border: 2px solid #8b5cf6;
            border-radius: 8px;
            background: rgba(255, 255, 255, 0.1);
            color: #ffffff;
            font-size: 16px;
            transition: all 0.3s ease;
            box-sizing: border-box;
        }}
        textarea:focus, select:focus, input[type="text"]:focus {{
            border-color: #a78bfa;
            box-shadow: 0 0 10px rgba(139, 92, 246, 0.5);
            outline: none;
        }}
        input[type="checkbox"] {{
            margin-right: 10px;
            transform: scale(1.2);
            accent-color: #8b5cf6;
        }}
        input[type="submit"] {{
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
        }}
        input[type="submit"]:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(139, 92, 246, 0.6);
            background: linear-gradient(45deg, #a78bfa, #c4b5fd);
        }}
        input[type="submit"]:active {{
            transform: translateY(0);
        }}
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

        try:
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
        except Exception as e:
            logger.error(f"Analysis error: {e}")
            if request.is_json:
                return jsonify({'error': str(e)}), 500
            else:
                return f"Error: {e}", 500

    return app