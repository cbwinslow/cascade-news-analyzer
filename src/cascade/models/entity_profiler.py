"""
Entity profiling module for Cascade News Analyzer.

This module handles building and maintaining comprehensive profiles
for entities (people, organizations, governments, etc.)
"""

import logging
from typing import Dict, Any, List, Optional, Set, Tuple
from datetime import datetime
import json
from pathlib import Path

import spacy
from spacy.tokens import Doc

from ..config import NLP_MODEL, DATA_DIR

logger = logging.getLogger(__name__)


class EntityProfiler:
    """
    Builds and maintains comprehensive profiles of entities.
    """
    
    def __init__(self):
        """
        Initialize the entity profiler.
        """
        self.nlp = None
        self.profiles_dir = DATA_DIR / "entity_profiles"
        self.profiles_dir.mkdir(exist_ok=True)
        
        try:
            self.nlp = spacy.load(NLP_MODEL)
            logger.info(f"Loaded NLP model: {NLP_MODEL}")
        except Exception as e:
            logger.error(f"Failed to load NLP model {NLP_MODEL}: {str(e)}")
    
    def process_document(self, document: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Process a document and extract entity information.
        
        Args:
            document (Dict[str, Any]): Document data
            
        Returns:
            List[Dict[str, Any]]: List of entity updates
        """
        if not self.nlp:
            logger.error("NLP model not loaded, cannot process document")
            return []
        
        try:
            # Extract text from document
            text = ""
            if 'text' in document:
                text = document['text']
            elif 'content' in document:
                text = document['content']
            elif 'title' in document and 'description' in document:
                text = f"{document['title']}. {document['description']}"
            
            if not text:
                logger.warning("No text content found in document")
                return []
            
            # Process text with spaCy
            doc = self.nlp(text)
            
            # Group entities by name to consolidate information
            entity_groups = {}
            for ent in doc.ents:
                if ent.label_ in ['PERSON', 'ORG', 'GPE', 'NORP', 'FAC']:
                    entity_name = ent.text
                    
                    if entity_name not in entity_groups:
                        entity_groups[entity_name] = {
                            'name': entity_name,
                            'type': ent.label_,
                            'mentions': [],
                            'document_ids': set(),
                            'relations': set()
                        }
                    
                    # Add mention with context
                    sent = ent.sent.text
                    entity_groups[entity_name]['mentions'].append({
                        'text': ent.text,
                        'context': sent,
                        'char_start': ent.start_char,
                        'char_end': ent.end_char
                    })
                    
                    # Add document ID
                    if 'id' in document:
                        entity_groups[entity_name]['document_ids'].add(document['id'])
            
            # Extract relations between entities
            self._extract_entity_relations(doc, entity_groups)
            
            # Update entity profiles
            entity_updates = []
            for entity_name, entity_data in entity_groups.items():
                # Convert sets to lists for serialization
                entity_data['document_ids'] = list(entity_data['document_ids'])
                entity_data['relations'] = list(entity_data['relations'])
                
                # Add metadata from the document
                entity_data['last_updated'] = datetime.now().isoformat()
                entity_data['source'] = document.get('source', 'unknown')
                entity_data['source_url'] = document.get('url', '')
                
                # Update profile
                self._update_entity_profile(entity_name, entity_data)
                entity_updates.append(entity_data)
            
            logger.info(f"Processed document and updated {len(entity_updates)} entity profiles")
            return entity_updates
        
        except Exception as e:
            logger.error(f"Error processing document for entity profiling: {str(e)}")
            return []
    
    def _extract_entity_relations(self, doc: Doc, entity_groups: Dict[str, Dict[str, Any]]) -> None:
        """
        Extract relations between entities.
        
        Args:
            doc (Doc): spaCy document
            entity_groups (Dict[str, Dict[str, Any]]): Entity groups to update
        """
        # Extract co-occurrence relations (entities in the same sentence)
        for sent in doc.sents:
            sent_entities = [ent for ent in sent.ents if ent.label_ in ['PERSON', 'ORG', 'GPE', 'NORP', 'FAC']]
            
            # Add co-occurrence relations
            for i, ent1 in enumerate(sent_entities):
                for ent2 in sent_entities[i+1:]:
                    relation = f"co-occurs-with:{ent2.text}"
                    if ent1.text in entity_groups:
                        entity_groups[ent1.text]['relations'].add(relation)
                    
                    relation = f"co-occurs-with:{ent1.text}"
                    if ent2.text in entity_groups:
                        entity_groups[ent2.text]['relations'].add(relation)
    
    def _update_entity_profile(self, entity_name: str, entity_data: Dict[str, Any]) -> None:
        """
        Update an entity profile with new information.
        
        Args:
            entity_name (str): Entity name
            entity_data (Dict[str, Any]): Entity data to update
        """
        # Create a safe filename from the entity name
        safe_name = "".join(c if c.isalnum() else "_" for c in entity_name)
        profile_path = self.profiles_dir / f"{safe_name}.json"
        
        # Load existing profile if it exists
        existing_profile = {}
        if profile_path.exists():
            try:
                with open(profile_path, 'r', encoding='utf-8') as f:
                    existing_profile = json.load(f)
            except Exception as e:
                logger.error(f"Error loading profile for {entity_name}: {str(e)}")
        
        # Merge new data with existing profile
        updated_profile = self._merge_entity_data(existing_profile, entity_data)
        
        # Save updated profile
        try:
            with open(profile_path, 'w', encoding='utf-8') as f:
                json.dump(updated_profile, f, indent=2, ensure_ascii=False)
            logger.debug(f"Updated profile for entity: {entity_name}")
        except Exception as e:
            logger.error(f"Error saving profile for {entity_name}: {str(e)}")
    
    def _merge_entity_data(self, existing: Dict[str, Any], new_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge existing profile with new entity data.
        
        Args:
            existing (Dict[str, Any]): Existing profile data
            new_data (Dict[str, Any]): New entity data
            
        Returns:
            Dict[str, Any]: Merged profile data
        """
        if not existing:
            return new_data
        
        # Start with existing data
        merged = existing.copy()
        
        # Update type if it's more specific
        if new_data.get('type') and (not merged.get('type') or merged.get('type') == 'MISC'):
            merged['type'] = new_data['type']
        
        # Append new mentions
        if 'mentions' not in merged:
            merged['mentions'] = []
        merged['mentions'].extend(new_data.get('mentions', []))
        
        # Limit mentions to the most recent 100
        if len(merged['mentions']) > 100:
            merged['mentions'] = merged['mentions'][-100:]
        
        # Update document IDs
        if 'document_ids' not in merged:
            merged['document_ids'] = []
        merged['document_ids'].extend(new_data.get('document_ids', []))
        merged['document_ids'] = list(set(merged['document_ids']))
        
        # Update relations
        if 'relations' not in merged:
            merged['relations'] = []
        merged['relations'].extend(new_data.get('relations', []))
        merged['relations'] = list(set(merged['relations']))
        
        # Update metadata
        merged['last_updated'] = new_data.get('last_updated', datetime.now().isoformat())
        
        # Add source information if new
        if 'sources' not in merged:
            merged['sources'] = []
        
        source_info = {
            'name': new_data.get('source'),
            'url': new_data.get('source_url'),
            'date': new_data.get('last_updated')
        }
        if source_info not in merged['sources']:
            merged['sources'].append(source_info)
        
        return merged
    
    def get_entity_profile(self, entity_name: str) -> Optional[Dict[str, Any]]:
        """
        Get the profile for a specific entity.
        
        Args:
            entity_name (str): Entity name
            
        Returns:
            Optional[Dict[str, Any]]: Entity profile or None if not found
        """
        # Create a safe filename from the entity name
        safe_name = "".join(c if c.isalnum() else "_" for c in entity_name)
        profile_path = self.profiles_dir / f"{safe_name}.json"
        
        if not profile_path.exists():
            return None
        
        try:
            with open(profile_path, 'r', encoding='utf-8') as f:
                profile = json.load(f)
            return profile
        except Exception as e:
            logger.error(f"Error loading profile for {entity_name}: {str(e)}")
            return None
    
    def list_entities(self) -> List[str]:
        """
        List all entities with profiles.
        
        Returns:
            List[str]: List of entity names
        """
        entities = []
        for profile_path in self.profiles_dir.glob('*.json'):
            try:
                with open(profile_path, 'r', encoding='utf-8') as f:
                    profile = json.load(f)
                entities.append(profile.get('name', profile_path.stem))
            except Exception as e:
                logger.error(f"Error loading profile {profile_path}: {str(e)}")
        
        return entities
    
    def search_entities(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for entities matching a query.
        
        Args:
            query (str): Search query
            
        Returns:
            List[Dict[str, Any]]: List of matching entity profiles
        """
        matching_entities = []
        query = query.lower()
        
        for profile_path in self.profiles_dir.glob('*.json'):
            try:
                with open(profile_path, 'r', encoding='utf-8') as f:
                    profile = json.load(f)
                
                # Check if query matches entity name
                if query in profile.get('name', '').lower():
                    matching_entities.append(profile)
                    continue
                
                # Check mentions for query
                for mention in profile.get('mentions', []):
                    if query in mention.get('text', '').lower() or query in mention.get('context', '').lower():
                        matching_entities.append(profile)
                        break
            except Exception as e:
                logger.error(f"Error searching profile {profile_path}: {str(e)}")
        
        return matching_entities
    
    def get_entity_relations(self, entity_name: str) -> Dict[str, List[str]]:
        """
        Get the relations for a specific entity.
        
        Args:
            entity_name (str): Entity name
            
        Returns:
            Dict[str, List[str]]: Dictionary of relation types to related entities
        """
        profile = self.get_entity_profile(entity_name)
        if not profile:
            return {}
        
        relations = {}
        for relation in profile.get('relations', []):
            # Parse relation string (e.g., "co-occurs-with:Entity Name")
            if ':' in relation:
                rel_type, related_entity = relation.split(':', 1)
                if rel_type not in relations:
                    relations[rel_type] = []
                relations[rel_type].append(related_entity)
        
        return relations

