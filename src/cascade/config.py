"""
Configuration module for Cascade News Analyzer.

This module handles loading and managing configuration settings from
environment variables, config files, and default values.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base directories
BASE_DIR = Path(__file__).parent.parent.parent.absolute()
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"
LOGS_DIR = BASE_DIR / "logs"

# Create directories if they don't exist
DATA_DIR.mkdir(exist_ok=True)
MODELS_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# API Keys and credentials
TWITTER_API_KEY = os.getenv("TWITTER_API_KEY", "")
TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET", "")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN", "")
TWITTER_ACCESS_SECRET = os.getenv("TWITTER_ACCESS_SECRET", "")

NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")

# Vector database configuration
VECTOR_DB_TYPE = os.getenv("VECTOR_DB_TYPE", "pinecone")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY", "")
PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT", "")
WEAVIATE_URL = os.getenv("WEAVIATE_URL", "")
WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY", "")

# Database configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL", f"sqlite:///{DATA_DIR}/cascade.db"
)

# Model configuration
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
NLP_MODEL = os.getenv("NLP_MODEL", "en_core_web_md")

# API configuration
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
API_DEBUG = os.getenv("API_DEBUG", "False").lower() == "true"

# Logging configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")


def get_config() -> Dict[str, Any]:
    """
    Get the full configuration as a dictionary.
    
    Returns:
        Dict[str, Any]: Configuration dictionary
    """
    return {k: v for k, v in globals().items() if k.isupper()}


def get_config_value(key: str, default: Optional[Any] = None) -> Any:
    """
    Get a specific configuration value.
    
    Args:
        key (str): Configuration key
        default (Optional[Any], optional): Default value if key is not found. Defaults to None.
    
    Returns:
        Any: Configuration value
    """
    return globals().get(key, default)

