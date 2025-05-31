"""
Setup script for the Cascade News Analyzer package.
"""

from setuptools import setup, find_packages

setup(
    name="cascade-news-analyzer",
    version="0.1.0",
    author="",
    author_email="",
    description="A sophisticated news interpretation and analysis system",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/cascade-news-analyzer",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.9",
    install_requires=[
        "fastapi>=0.95.0,<0.96.0",
        "uvicorn>=0.22.0,<0.23.0",
        "pydantic>=1.9.0,<2.0.0",
        "sqlalchemy>=2.0.0",
        "alembic>=1.11.0",
        "psycopg2-binary>=2.9.0",
        "python-dotenv>=1.0.0",
        "pandas>=2.0.0",
        "numpy>=1.24.0",
        "scikit-learn>=1.2.0",
        "torch>=2.0.0",
        "transformers>=4.30.0",
        "spacy>=3.6.0",
        "nltk>=3.8.0",
        "sentence-transformers>=2.2.0",
        "pinecone-client>=2.2.0",
        "weaviate-client>=3.25.0",
        "tweepy>=4.14.0",
        "newsapi-python>=0.2.7",
        "beautifulsoup4>=4.12.0",
        "prometheus-client>=0.17.0",
        "python-json-logger>=2.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.3.0",
            "pytest-cov>=4.1.0",
            "black>=23.3.0",
            "isort>=5.12.0",
            "flake8>=6.0.0",
            "mypy>=1.3.0",
            "sphinx>=6.2.0",
            "sphinx-rtd-theme>=1.2.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "cascade=cascade.cli:main",
        ],
    },
)

