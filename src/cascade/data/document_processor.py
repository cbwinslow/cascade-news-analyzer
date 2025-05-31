"""
Document processing module for Cascade News Analyzer.

This module handles processing and analyzing government documents,
bills, treaties, and legal texts.
"""

import logging
import re
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

import spacy
from spacy.tokens import Doc

from ..config import NLP_MODEL

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """
    Processes and analyzes documents, especially legal and government texts.
    """
    
    def __init__(self):
        """
        Initialize the document processor.
        """
        self.nlp = None
        try:
            self.nlp = spacy.load(NLP_MODEL)
            logger.info(f"Loaded NLP model: {NLP_MODEL}")
        except Exception as e:
            logger.error(f"Failed to load NLP model {NLP_MODEL}: {str(e)}")
    
    def process_document(self, text: str) -> Dict[str, Any]:
        """
        Process a document and extract key information.
        
        Args:
            text (str): Document text
            
        Returns:
            Dict[str, Any]: Processed document information
        """
        if not self.nlp:
            logger.error("NLP model not loaded, cannot process document")
            return {'error': 'NLP model not loaded'}
        
        try:
            doc = self.nlp(text)
            
            # Extract key information
            entities = self._extract_entities(doc)
            key_sentences = self._extract_key_sentences(doc)
            summary = self._generate_summary(doc, key_sentences)
            
            return {
                'entities': entities,
                'key_sentences': key_sentences,
                'summary': summary,
                'word_count': len(doc),
                'processed': True
            }
        except Exception as e:
            logger.error(f"Error processing document: {str(e)}")
            return {'error': str(e), 'processed': False}
    
    def _extract_entities(self, doc: Doc) -> List[Dict[str, Any]]:
        """
        Extract named entities from a document.
        
        Args:
            doc (Doc): spaCy document
            
        Returns:
            List[Dict[str, Any]]: List of extracted entities
        """
        entities = []
        for ent in doc.ents:
            entities.append({
                'text': ent.text,
                'label': ent.label_,
                'start': ent.start_char,
                'end': ent.end_char
            })
        return entities
    
    def _extract_key_sentences(self, doc: Doc, top_n: int = 5) -> List[str]:
        """
        Extract key sentences from a document based on importance.
        
        Args:
            doc (Doc): spaCy document
            top_n (int, optional): Number of key sentences to extract. Defaults to 5.
            
        Returns:
            List[str]: List of key sentences
        """
        # Simple heuristic: sentences with entities and longer sentences tend to be more important
        sentence_scores = []
        for sent in doc.sents:
            # Score based on entities and length
            entity_count = sum(1 for _ in sent.ents)
            length_score = min(len(sent) / 20, 1.0)  # Normalize length
            importance_words = sum(1 for token in sent if token.is_stop is False and token.is_punct is False)
            
            score = entity_count * 0.5 + length_score * 0.3 + (importance_words / len(sent)) * 0.2
            sentence_scores.append((sent.text, score))
        
        # Get top N sentences
        sentence_scores.sort(key=lambda x: x[1], reverse=True)
        return [sent for sent, score in sentence_scores[:top_n]]
    
    def _generate_summary(self, doc: Doc, key_sentences: List[str], max_length: int = 200) -> str:
        """
        Generate a summary from key sentences.
        
        Args:
            doc (Doc): spaCy document
            key_sentences (List[str]): List of key sentences
            max_length (int, optional): Maximum summary length. Defaults to 200.
            
        Returns:
            str: Generated summary
        """
        # For now, just concatenate key sentences
        summary = " ".join(key_sentences)
        
        # Truncate if too long
        if len(summary) > max_length:
            summary = summary[:max_length] + "..."
            
        return summary
    
    def analyze_legal_document(self, text: str) -> Dict[str, Any]:
        """
        Analyze a legal document for specific legal concepts and structures.
        
        Args:
            text (str): Document text
            
        Returns:
            Dict[str, Any]: Legal analysis results
        """
        if not self.nlp:
            logger.error("NLP model not loaded, cannot analyze legal document")
            return {'error': 'NLP model not loaded'}
        
        try:
            doc = self.nlp(text)
            
            # Process document
            basic_info = self.process_document(text)
            
            # Extract legal-specific elements
            sections = self._extract_document_sections(text)
            references = self._extract_legal_references(text)
            definitions = self._extract_definitions(text)
            
            return {
                **basic_info,
                'sections': sections,
                'legal_references': references,
                'definitions': definitions
            }
        except Exception as e:
            logger.error(f"Error analyzing legal document: {str(e)}")
            return {'error': str(e)}
    
    def _extract_document_sections(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract sections from a document.
        
        Args:
            text (str): Document text
            
        Returns:
            List[Dict[str, Any]]: List of document sections
        """
        # Simple regex-based section extraction
        # This is a basic implementation and would need to be enhanced for real documents
        section_pattern = re.compile(r'(?:Section|SECTION|Article|ARTICLE)\s+(\d+)[.\s]+(.+?)(?=(?:Section|SECTION|Article|ARTICLE)\s+\d+|$)', re.DOTALL)
        sections = []
        
        for match in section_pattern.finditer(text):
            section_num = match.group(1)
            section_content = match.group(2).strip()
            sections.append({
                'number': section_num,
                'content': section_content,
                'start': match.start(),
                'end': match.end()
            })
        
        return sections
    
    def _extract_legal_references(self, text: str) -> List[str]:
        """
        Extract legal references from text.
        
        Args:
            text (str): Document text
            
        Returns:
            List[str]: List of legal references
        """
        # Extract references to laws, statutes, etc.
        reference_patterns = [
            r'\d+\s+U\.S\.C\.\s+§*\s*\d+',  # U.S. Code references
            r'Public\s+Law\s+\d+-\d+',  # Public Law references
            r'\d+\s+C\.F\.R\.\s+§*\s*\d+',  # Code of Federal Regulations
            r'S\.\s*\d+',  # Senate bills
            r'H\.R\.\s*\d+'  # House bills
        ]
        
        references = []
        for pattern in reference_patterns:
            matches = re.findall(pattern, text)
            references.extend(matches)
        
        return references
    
    def _extract_definitions(self, text: str) -> Dict[str, str]:
        """
        Extract defined terms from legal documents.
        
        Args:
            text (str): Document text
            
        Returns:
            Dict[str, str]: Dictionary of term definitions
        """
        # Look for definition patterns
        definition_patterns = [
            r'(?:"|\'|«|")([A-Z][a-zA-Z\s]+)(?:"|\'|»|")(?:\s+means|refers to|shall mean)\s+([^.]+)',
            r'the term\s+(?:"|\'|«|")([A-Z][a-zA-Z\s]+)(?:"|\'|»|")(?:\s+means|refers to|shall mean)\s+([^.]+)',
            r'([A-Z][a-zA-Z\s]+)(?:\s+means|is defined as|shall mean)\s+([^.]+)'
        ]
        
        definitions = {}
        for pattern in definition_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                term = match.group(1).strip()
                definition = match.group(2).strip()
                definitions[term] = definition
        
        return definitions
    
    def process_file(self, file_path: str) -> Dict[str, Any]:
        """
        Process a document file.
        
        Args:
            file_path (str): Path to document file
            
        Returns:
            Dict[str, Any]: Processed document information
        """
        try:
            path = Path(file_path)
            if not path.exists():
                return {'error': f'File not found: {file_path}'}
            
            with open(path, 'r', encoding='utf-8') as f:
                text = f.read()
            
            # Determine if it's a legal document based on content
            if self._is_legal_document(text):
                result = self.analyze_legal_document(text)
            else:
                result = self.process_document(text)
            
            result['file_path'] = str(path)
            result['file_name'] = path.name
            
            return result
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {str(e)}")
            return {'error': str(e), 'file_path': file_path}
    
    def _is_legal_document(self, text: str) -> bool:
        """
        Determine if a document is likely a legal document.
        
        Args:
            text (str): Document text
            
        Returns:
            bool: True if document appears to be legal in nature
        """
        # Check for common legal document markers
        legal_markers = [
            r'Act', r'Bill', r'Statute', r'Law', r'Regulation',
            r'U\.S\.C', r'C\.F\.R', r'Public Law', r'Section \d+',
            r'Article \d+', r'whereas', r'pursuant to', r'hereinafter',
            r'jurisdiction', r'legislation'
        ]
        
        marker_count = 0
        for marker in legal_markers:
            if re.search(r'\b' + marker + r'\b', text, re.IGNORECASE):
                marker_count += 1
        
        # If more than 3 legal markers are found, consider it a legal document
        return marker_count > 3

