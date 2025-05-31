"""
Vector storage module for Cascade News Analyzer.

This module handles embeddings storage and retrieval using vector databases
such as Pinecone and Weaviate.
"""

import logging
import json
from typing import Dict, Any, List, Optional, Union, Tuple
import time
import hashlib

import numpy as np
from sentence_transformers import SentenceTransformer
import pinecone
from weaviate import Client, AuthClientPassword

from ..config import (
    VECTOR_DB_TYPE, EMBEDDING_MODEL, 
    PINECONE_API_KEY, PINECONE_ENVIRONMENT,
    WEAVIATE_URL, WEAVIATE_API_KEY
)

logger = logging.getLogger(__name__)


class VectorStore:
    """
    Manages vector embeddings storage and retrieval using vector databases.
    """
    
    def __init__(self, namespace: str = "cascade", vector_dimensions: int = 384):
        """
        Initialize the vector store.
        
        Args:
            namespace (str, optional): Namespace for vectors. Defaults to "cascade".
            vector_dimensions (int, optional): Dimensions of vectors. Defaults to 384.
        """
        self.namespace = namespace
        self.vector_dimensions = vector_dimensions
        self.client = None
        self.embedding_model = None
        self.index_name = f"cascade_{namespace}"
        
        # Initialize embedding model
        self._initialize_embedding_model()
        
        # Initialize vector database client based on configuration
        if VECTOR_DB_TYPE.lower() == "pinecone":
            self._initialize_pinecone()
        elif VECTOR_DB_TYPE.lower() == "weaviate":
            self._initialize_weaviate()
        else:
            logger.error(f"Unsupported vector database type: {VECTOR_DB_TYPE}")
    
    def _initialize_embedding_model(self) -> None:
        """
        Initialize the embedding model.
        """
        try:
            self.embedding_model = SentenceTransformer(EMBEDDING_MODEL)
            logger.info(f"Initialized embedding model: {EMBEDDING_MODEL}")
        except Exception as e:
            logger.error(f"Failed to initialize embedding model: {str(e)}")
            self.embedding_model = None
    
    def _initialize_pinecone(self) -> None:
        """
        Initialize Pinecone client.
        """
        if not PINECONE_API_KEY or not PINECONE_ENVIRONMENT:
            logger.error("Pinecone API key or environment not set")
            return
        
        try:
            pinecone.init(api_key=PINECONE_API_KEY, environment=PINECONE_ENVIRONMENT)
            
            # Check if index exists, create if not
            if self.index_name not in pinecone.list_indexes():
                pinecone.create_index(
                    name=self.index_name,
                    dimension=self.vector_dimensions,
                    metric="cosine"
                )
                logger.info(f"Created new Pinecone index: {self.index_name}")
            
            self.client = pinecone.Index(self.index_name)
            logger.info(f"Connected to Pinecone index: {self.index_name}")
        except Exception as e:
            logger.error(f"Failed to initialize Pinecone: {str(e)}")
            self.client = None
    
    def _initialize_weaviate(self) -> None:
        """
        Initialize Weaviate client.
        """
        if not WEAVIATE_URL:
            logger.error("Weaviate URL not set")
            return
        
        try:
            auth_config = None
            if WEAVIATE_API_KEY:
                auth_config = AuthClientPassword(username="", password=WEAVIATE_API_KEY)
            
            self.client = Client(WEAVIATE_URL, auth_client_secret=auth_config)
            
            # Check if schema class exists, create if not
            schema = self.client.schema.get()
            class_exists = any(cls["class"] == self.namespace for cls in schema.get("classes", []))
            
            if not class_exists:
                class_obj = {
                    "class": self.namespace,
                    "description": f"Cascade News Analyzer data for {self.namespace}",
                    "vectorizer": "none",  # We'll provide our own vectors
                    "properties": [
                        {
                            "name": "content",
                            "dataType": ["text"],
                            "description": "The content of the document"
                        },
                        {
                            "name": "metadata",
                            "dataType": ["text"],
                            "description": "JSON-encoded metadata"
                        },
                        {
                            "name": "source",
                            "dataType": ["text"],
                            "description": "Source of the document"
                        }
                    ]
                }
                self.client.schema.create_class(class_obj)
                logger.info(f"Created new Weaviate class: {self.namespace}")
            
            logger.info(f"Connected to Weaviate instance at {WEAVIATE_URL}")
        except Exception as e:
            logger.error(f"Failed to initialize Weaviate: {str(e)}")
            self.client = None
    
    def get_embedding(self, text: str) -> Optional[List[float]]:
        """
        Get embedding vector for text.
        
        Args:
            text (str): Text to embed
            
        Returns:
            Optional[List[float]]: Embedding vector or None if embedding fails
        """
        if not self.embedding_model:
            logger.error("Embedding model not initialized")
            return None
        
        try:
            embedding = self.embedding_model.encode(text)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Failed to generate embedding: {str(e)}")
            return None
    
    def add_item(self, content: str, metadata: Dict[str, Any], id: Optional[str] = None) -> Optional[str]:
        """
        Add an item to the vector store.
        
        Args:
            content (str): Content to embed and store
            metadata (Dict[str, Any]): Metadata for the content
            id (Optional[str], optional): Item ID. If None, a hash ID will be generated. Defaults to None.
            
        Returns:
            Optional[str]: Item ID if successful, None otherwise
        """
        if not self.client or not self.embedding_model:
            logger.error("Vector store not properly initialized")
            return None
        
        try:
            # Generate embedding
            embedding = self.get_embedding(content)
            if not embedding:
                return None
            
            # Generate ID if not provided
            if not id:
                content_hash = hashlib.md5(content.encode()).hexdigest()
                id = f"{self.namespace}_{content_hash}"
            
            # Store based on vector database type
            if VECTOR_DB_TYPE.lower() == "pinecone":
                return self._add_item_pinecone(id, embedding, content, metadata)
            elif VECTOR_DB_TYPE.lower() == "weaviate":
                return self._add_item_weaviate(id, embedding, content, metadata)
            else:
                logger.error(f"Unsupported vector database type: {VECTOR_DB_TYPE}")
                return None
        except Exception as e:
            logger.error(f"Failed to add item to vector store: {str(e)}")
            return None
    
    def _add_item_pinecone(self, id: str, embedding: List[float], content: str, metadata: Dict[str, Any]) -> str:
        """
        Add an item to Pinecone.
        
        Args:
            id (str): Item ID
            embedding (List[float]): Embedding vector
            content (str): Content text
            metadata (Dict[str, Any]): Metadata
            
        Returns:
            str: Item ID
        """
        # Add content to metadata
        metadata_with_content = {
            **metadata,
            "content": content[:1000]  # Limit content length for metadata
        }
        
        # Upsert to Pinecone
        self.client.upsert(
            vectors=[(id, embedding, metadata_with_content)],
            namespace=self.namespace
        )
        
        logger.info(f"Added item {id} to Pinecone index {self.index_name}")
        return id
    
    def _add_item_weaviate(self, id: str, embedding: List[float], content: str, metadata: Dict[str, Any]) -> str:
        """
        Add an item to Weaviate.
        
        Args:
            id (str): Item ID
            embedding (List[float]): Embedding vector
            content (str): Content text
            metadata (Dict[str, Any]): Metadata
            
        Returns:
            str: Item ID
        """
        # Convert metadata to JSON string
        metadata_json = json.dumps(metadata)
        
        # Create data object
        data_object = {
            "content": content,
            "metadata": metadata_json,
            "source": metadata.get("source", "unknown")
        }
        
        # Add with vector
        self.client.data_object.create(
            class_name=self.namespace,
            data_object=data_object,
            uuid=id,
            vector=embedding
        )
        
        logger.info(f"Added item {id} to Weaviate class {self.namespace}")
        return id
    
    def search(self, query: str, top_k: int = 5, filter: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Search for similar items using vector similarity.
        
        Args:
            query (str): Query text
            top_k (int, optional): Number of results to return. Defaults to 5.
            filter (Optional[Dict[str, Any]], optional): Filter for results. Defaults to None.
            
        Returns:
            List[Dict[str, Any]]: Search results
        """
        if not self.client or not self.embedding_model:
            logger.error("Vector store not properly initialized")
            return []
        
        try:
            # Generate query embedding
            query_embedding = self.get_embedding(query)
            if not query_embedding:
                return []
            
            # Search based on vector database type
            if VECTOR_DB_TYPE.lower() == "pinecone":
                return self._search_pinecone(query_embedding, top_k, filter)
            elif VECTOR_DB_TYPE.lower() == "weaviate":
                return self._search_weaviate(query_embedding, top_k, filter)
            else:
                logger.error(f"Unsupported vector database type: {VECTOR_DB_TYPE}")
                return []
        except Exception as e:
            logger.error(f"Failed to search vector store: {str(e)}")
            return []
    
    def _search_pinecone(self, query_embedding: List[float], top_k: int, filter: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Search Pinecone for similar items.
        
        Args:
            query_embedding (List[float]): Query embedding vector
            top_k (int): Number of results to return
            filter (Optional[Dict[str, Any]]): Filter for results
            
        Returns:
            List[Dict[str, Any]]: Search results
        """
        results = self.client.query(
            vector=query_embedding,
            top_k=top_k,
            namespace=self.namespace,
            filter=filter,
            include_metadata=True
        )
        
        # Format results
        formatted_results = []
        for match in results.get('matches', []):
            item = {
                'id': match.get('id'),
                'score': match.get('score'),
                'content': match.get('metadata', {}).get('content', ''),
                'metadata': {k: v for k, v in match.get('metadata', {}).items() if k != 'content'}
            }
            formatted_results.append(item)
        
        return formatted_results
    
    def _search_weaviate(self, query_embedding: List[float], top_k: int, filter: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Search Weaviate for similar items.
        
        Args:
            query_embedding (List[float]): Query embedding vector
            top_k (int): Number of results to return
            filter (Optional[Dict[str, Any]]): Filter for results
            
        Returns:
            List[Dict[str, Any]]: Search results
        """
        # Prepare filter if provided
        where_filter = None
        if filter:
            # This is a simplified example - would need to be expanded for real use
            where_filter = {
                "operator": "Equal",
                "path": ["source"],
                "valueText": filter.get("source")
            }
        
        # Execute vector search
        result = (
            self.client.query
            .get(self.namespace, ["content", "metadata", "source", "_additional {id, certainty}"])
            .with_near_vector({"vector": query_embedding})
            .with_limit(top_k)
        )
        
        if where_filter:
            result = result.with_where(where_filter)
            
        result = result.do()
        
        # Format results
        formatted_results = []
        for item in result.get('data', {}).get('Get', {}).get(self.namespace, []):
            try:
                metadata = json.loads(item.get('metadata', '{}'))
            except:
                metadata = {}
                
            formatted_result = {
                'id': item.get('_additional', {}).get('id'),
                'score': item.get('_additional', {}).get('certainty'),
                'content': item.get('content', ''),
                'metadata': metadata,
                'source': item.get('source', 'unknown')
            }
            formatted_results.append(formatted_result)
        
        return formatted_results
    
    def delete_item(self, id: str) -> bool:
        """
        Delete an item from the vector store.
        
        Args:
            id (str): Item ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.client:
            logger.error("Vector store not properly initialized")
            return False
        
        try:
            # Delete based on vector database type
            if VECTOR_DB_TYPE.lower() == "pinecone":
                self.client.delete(ids=[id], namespace=self.namespace)
            elif VECTOR_DB_TYPE.lower() == "weaviate":
                self.client.data_object.delete(uuid=id, class_name=self.namespace)
            else:
                logger.error(f"Unsupported vector database type: {VECTOR_DB_TYPE}")
                return False
            
            logger.info(f"Deleted item {id} from vector store")
            return True
        except Exception as e:
            logger.error(f"Failed to delete item from vector store: {str(e)}")
            return False
    
    def batch_add_items(self, items: List[Tuple[str, Dict[str, Any], Optional[str]]]) -> List[Optional[str]]:
        """
        Add multiple items to the vector store in batch.
        
        Args:
            items (List[Tuple[str, Dict[str, Any], Optional[str]]]): List of (content, metadata, id) tuples
            
        Returns:
            List[Optional[str]]: List of item IDs (None for failed items)
        """
        if not self.client or not self.embedding_model:
            logger.error("Vector store not properly initialized")
            return [None] * len(items)
        
        # Generate embeddings and prepare items
        prepared_items = []
        for content, metadata, id in items:
            embedding = self.get_embedding(content)
            if not embedding:
                prepared_items.append(None)
                continue
                
            # Generate ID if not provided
            if not id:
                content_hash = hashlib.md5(content.encode()).hexdigest()
                id = f"{self.namespace}_{content_hash}"
                
            prepared_items.append((id, embedding, content, metadata))
        
        try:
            # Batch add based on vector database type
            if VECTOR_DB_TYPE.lower() == "pinecone":
                return self._batch_add_pinecone(prepared_items)
            elif VECTOR_DB_TYPE.lower() == "weaviate":
                return self._batch_add_weaviate(prepared_items)
            else:
                logger.error(f"Unsupported vector database type: {VECTOR_DB_TYPE}")
                return [None] * len(items)
        except Exception as e:
            logger.error(f"Failed to batch add items to vector store: {str(e)}")
            return [None] * len(items)
    
    def _batch_add_pinecone(self, prepared_items: List[Tuple[str, List[float], str, Dict[str, Any]]]) -> List[Optional[str]]:
        """
        Batch add items to Pinecone.
        
        Args:
            prepared_items (List[Tuple[str, List[float], str, Dict[str, Any]]]): Prepared items
            
        Returns:
            List[Optional[str]]: List of item IDs
        """
        vectors = []
        item_ids = []
        
        for id, embedding, content, metadata in prepared_items:
            if id is None or embedding is None:
                item_ids.append(None)
                continue
                
            # Add content to metadata
            metadata_with_content = {
                **metadata,
                "content": content[:1000]  # Limit content length for metadata
            }
            
            vectors.append((id, embedding, metadata_with_content))
            item_ids.append(id)
        
        # Batch upsert to Pinecone
        if vectors:
            self.client.upsert(vectors=vectors, namespace=self.namespace)
            logger.info(f"Added {len(vectors)} items to Pinecone in batch")
        
        return item_ids
    
    def _batch_add_weaviate(self, prepared_items: List[Tuple[str, List[float], str, Dict[str, Any]]]) -> List[Optional[str]]:
        """
        Batch add items to Weaviate.
        
        Args:
            prepared_items (List[Tuple[str, List[float], str, Dict[str, Any]]]): Prepared items
            
        Returns:
            List[Optional[str]]: List of item IDs
        """
        item_ids = []
        
        # Weaviate doesn't have a true batch import with custom vectors,
        # so we process items individually but could use a batch import library for larger datasets
        for id, embedding, content, metadata in prepared_items:
            if id is None or embedding is None:
                item_ids.append(None)
                continue
                
            # Convert metadata to JSON string
            metadata_json = json.dumps(metadata)
            
            # Create data object
            data_object = {
                "content": content,
                "metadata": metadata_json,
                "source": metadata.get("source", "unknown")
            }
            
            # Add with vector
            try:
                self.client.data_object.create(
                    class_name=self.namespace,
                    data_object=data_object,
                    uuid=id,
                    vector=embedding
                )
                item_ids.append(id)
            except Exception as e:
                logger.error(f"Failed to add item {id} to Weaviate: {str(e)}")
                item_ids.append(None)
        
        logger.info(f"Added {len([id for id in item_ids if id is not None])} items to Weaviate")
        return item_ids

