"""
Command-line interface for Cascade News Analyzer.

This module provides command-line functionality for running the Cascade
News Analyzer system and performing various tasks.
"""

import argparse
import logging
import sys
from pathlib import Path
import json
from typing import Dict, Any, List, Optional

from .data.news_aggregator import NewsAggregator
from .data.document_processor import DocumentProcessor
from .models.entity_profiler import EntityProfiler
from .data.vector_store import VectorStore
from .config import get_config, LOG_LEVEL

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


def collect_news(args):
    """
    Collect news from sources based on query.
    
    Args:
        args: Command-line arguments
    """
    news_aggregator = NewsAggregator()
    results = news_aggregator.collect_news(args.query, sources=args.sources.split(',') if args.sources else None)
    
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved {len(results)} news items to {args.output}")
    else:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    
    logger.info(f"Collected {len(results)} news items for query: {args.query}")


def process_document(args):
    """
    Process a document file.
    
    Args:
        args: Command-line arguments
    """
    document_processor = DocumentProcessor()
    result = document_processor.process_file(args.file)
    
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved processed document to {args.output}")
    else:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    logger.info(f"Processed document: {args.file}")


def update_entity_profile(args):
    """
    Update entity profile from a document.
    
    Args:
        args: Command-line arguments
    """
    entity_profiler = EntityProfiler()
    
    # Load document from file
    with open(args.file, 'r', encoding='utf-8') as f:
        document = json.load(f)
    
    # Process document to update entity profiles
    updated_entities = entity_profiler.process_document(document)
    
    logger.info(f"Updated {len(updated_entities)} entity profiles from document: {args.file}")
    
    if args.entity:
        # Get profile for specific entity
        profile = entity_profiler.get_entity_profile(args.entity)
        if profile:
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    json.dump(profile, f, indent=2, ensure_ascii=False)
                logger.info(f"Saved entity profile for {args.entity} to {args.output}")
            else:
                print(json.dumps(profile, indent=2, ensure_ascii=False))
        else:
            logger.error(f"Entity profile not found for: {args.entity}")


def search_vectors(args):
    """
    Search vector store with a query.
    
    Args:
        args: Command-line arguments
    """
    vector_store = VectorStore(namespace=args.namespace)
    results = vector_store.search(args.query, top_k=args.limit)
    
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved {len(results)} search results to {args.output}")
    else:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    
    logger.info(f"Found {len(results)} results for query: {args.query}")


def add_to_vector_store(args):
    """
    Add a document to the vector store.
    
    Args:
        args: Command-line arguments
    """
    vector_store = VectorStore(namespace=args.namespace)
    
    # Load document from file
    with open(args.file, 'r', encoding='utf-8') as f:
        document = json.load(f)
    
    # Extract content and metadata
    content = ""
    metadata = {}
    
    if isinstance(document, dict):
        if 'text' in document:
            content = document['text']
        elif 'content' in document:
            content = document['content']
        elif 'title' in document and 'description' in document:
            content = f"{document['title']}. {document['description']}"
        
        # Use the rest as metadata
        metadata = {k: v for k, v in document.items() if k not in ['text', 'content']}
    
    if not content:
        logger.error("No content found in document")
        return
    
    # Add to vector store
    item_id = vector_store.add_item(content, metadata, id=args.id)
    
    if item_id:
        logger.info(f"Added document to vector store with ID: {item_id}")
    else:
        logger.error("Failed to add document to vector store")


def main():
    """
    Main CLI entry point.
    """
    parser = argparse.ArgumentParser(description="Cascade News Analyzer CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # News collection command
    news_parser = subparsers.add_parser("collect-news", help="Collect news from sources")
    news_parser.add_argument("query", help="Search query")
    news_parser.add_argument("--sources", help="Comma-separated list of sources (e.g., twitter,newsapi)")
    news_parser.add_argument("--output", "-o", help="Output file path (JSON)")
    news_parser.set_defaults(func=collect_news)
    
    # Document processing command
    doc_parser = subparsers.add_parser("process-document", help="Process a document file")
    doc_parser.add_argument("file", help="Document file path (JSON or text)")
    doc_parser.add_argument("--output", "-o", help="Output file path (JSON)")
    doc_parser.set_defaults(func=process_document)
    
    # Entity profile command
    entity_parser = subparsers.add_parser("update-entity", help="Update entity profile from document")
    entity_parser.add_argument("file", help="Document file path (JSON)")
    entity_parser.add_argument("--entity", "-e", help="Entity name to retrieve")
    entity_parser.add_argument("--output", "-o", help="Output file path for entity profile (JSON)")
    entity_parser.set_defaults(func=update_entity_profile)
    
    # Vector search command
    vector_parser = subparsers.add_parser("search", help="Search vector store")
    vector_parser.add_argument("query", help="Search query")
    vector_parser.add_argument("--namespace", "-n", default="cascade", help="Vector store namespace")
    vector_parser.add_argument("--limit", "-l", type=int, default=5, help="Maximum number of results")
    vector_parser.add_argument("--output", "-o", help="Output file path (JSON)")
    vector_parser.set_defaults(func=search_vectors)
    
    # Add to vector store command
    add_parser = subparsers.add_parser("add-to-vectors", help="Add document to vector store")
    add_parser.add_argument("file", help="Document file path (JSON)")
    add_parser.add_argument("--namespace", "-n", default="cascade", help="Vector store namespace")
    add_parser.add_argument("--id", help="Custom ID for the document")
    add_parser.set_defaults(func=add_to_vector_store)
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Execute command
    args.func(args)


if __name__ == "__main__":
    main()

