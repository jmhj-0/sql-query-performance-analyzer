from setuptools import setup, find_packages

setup(
    name="sql-query-performance-analyzer",
    version="1.0.0",
    packages=['SQLQueryPerformanceAnalyzer'],
    install_requires=[
        "sqlparse==0.4.4",
        "flask==2.3.3",
        "pytest==7.4.0",
        "python-dotenv==1.0.0",
    ],
    entry_points={
        'console_scripts': [
            'sql-analyzer = SQLQueryPerformanceAnalyzer.main:main',
        ],
    },
)