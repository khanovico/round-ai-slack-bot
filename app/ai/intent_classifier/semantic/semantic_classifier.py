"""
Semantic intent classifier using sentence embeddings
"""
import json
import numpy as np
from pathlib import Path
from typing import List, Dict
from sentence_transformers import SentenceTransformer
from app.ai.intent_classifier.base_classifier import BaseClassifier, Intent, IntentResult
from app.core.logging_config import get_logger


class SemanticClassifier(BaseClassifier):
    """Semantic intent classifier using sentence similarity"""
    
    def __init__(self, confidence_threshold: float = 0.6, examples_file: str = None):
        super().__init__(confidence_threshold)
        self.logger = get_logger("app.ai.semantic_classifier")
        
        # Load examples from file
        if examples_file is None:
            examples_file = Path(__file__).parent / "intent_examples.json"
        
        self.examples = self._load_examples(examples_file)
        self.embeddings_cache = {}
        
        # Try to import sentence transformers, fallback to simple similarity
        try:
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
            self.use_embeddings = True
            self.logger.info("SemanticClassifier initialized with SentenceTransformer")
        except ImportError:
            self.logger.warning("SentenceTransformer not available, using simple similarity")
            self.model = None
            self.use_embeddings = False
        
        # Pre-compute embeddings for examples
        self._precompute_embeddings()
        
        self.logger.info(f"SemanticClassifier initialized with {len(self.examples)} intent types")
    
    def _load_examples(self, examples_file: Path) -> Dict[str, List[str]]:
        """Load intent examples from JSON file"""
        try:
            with open(examples_file, 'r', encoding='utf-8') as f:
                examples = json.load(f)
            self.logger.debug(f"Loaded examples from {examples_file}")
            return examples
        except Exception as e:
            self.logger.error(f"Error loading examples: {e}")
            return {}
    
    def _precompute_embeddings(self):
        """Pre-compute embeddings for all examples"""
        if not self.use_embeddings:
            return
        
        for intent_name, examples in self.examples.items():
            try:
                embeddings = self.model.encode(examples)
                self.embeddings_cache[intent_name] = embeddings
                self.logger.debug(f"Computed embeddings for {intent_name}: {len(examples)} examples")
            except Exception as e:
                self.logger.error(f"Error computing embeddings for {intent_name}: {e}")
    
    def _simple_similarity(self, text1: str, text2: str) -> float:
        """Simple word-based similarity as fallback"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def _semantic_similarity(self, text: str, examples: List[str]) -> List[float]:
        """Compute semantic similarity with examples"""
        if self.use_embeddings:
            try:
                text_embedding = self.model.encode([text])
                example_embeddings = self.embeddings_cache.get(examples[0], [])
                self.logger.info(f"[CAREFUL] {example_embeddings}")
                
                if len(example_embeddings) == 0:
                    return [0.0] * len(examples)
                
                # Compute cosine similarity
                similarities = []
                for example_emb in example_embeddings:
                    similarity = np.dot(text_embedding[0], example_emb) / (
                        np.linalg.norm(text_embedding[0]) * np.linalg.norm(example_emb)
                    )
                    similarities.append(max(0.0, similarity))  # Ensure non-negative
                
                return similarities
            except Exception as e:
                self.logger.error(f"Error computing semantic similarity: {e}")
        
        # Fallback to simple similarity
        return [self._simple_similarity(text, example) for example in examples]
    
    def _classify_internal(self, text: str) -> IntentResult:
        """Classify intent using semantic similarity"""
        text = text.strip()
        
        if self.use_embeddings:
            # Encode the input text once
            text_embedding = self.model.encode([text])[0]
            
            # Collect all embeddings and their metadata
            all_embeddings = []
            embedding_metadata = []  # (intent_name, example_text, example_index)
            
            for intent_name, examples in self.examples.items():
                if not examples or intent_name not in self.embeddings_cache:
                    continue
                
                example_embeddings = self.embeddings_cache[intent_name]
                all_embeddings.extend(example_embeddings)
                
                for i, example in enumerate(examples):
                    embedding_metadata.append((intent_name, example, i))
            
            if not all_embeddings:
                return IntentResult(
                    intent=Intent.SQL_QUERY,
                    confidence=0.1,
                    metadata={"classifier": "semantic", "best_example": "", "similarity_method": "embeddings"}
                )
            
            # Batch compute cosine similarities
            all_embeddings = np.array(all_embeddings)
            
            # Compute dot products in batch
            dot_products = np.dot(all_embeddings, text_embedding)
            
            # Compute norms in batch
            text_norm = np.linalg.norm(text_embedding)
            example_norms = np.linalg.norm(all_embeddings, axis=1)
            
            # Compute cosine similarities in batch
            similarities = dot_products / (example_norms * text_norm)
            similarities = np.maximum(similarities, 0.0)  # Ensure non-negative
            
            # Find best match
            best_idx = np.argmax(similarities)
            best_confidence = similarities[best_idx]
            best_intent, best_example, _ = embedding_metadata[best_idx]
            
        else:
            # Fallback to simple similarity
            best_intent = None
            best_confidence = 0.0
            best_example = ""
            
            for intent_name, examples in self.examples.items():
                if not examples:
                    continue
                
                for example in examples:
                    similarity = self._simple_similarity(text, example)
                    if similarity > best_confidence:
                        best_confidence = similarity
                        best_intent = intent_name
                        best_example = example
        
        # Map to Intent enum
        if best_intent:
            try:
                intent = Intent(best_intent)
            except ValueError:
                self.logger.warning(f"Unknown intent: {best_intent}")
                intent = Intent.SQL_QUERY  # Default fallback
        else:
            intent = Intent.SQL_QUERY
            best_confidence = 0.1  # Very low confidence for no match
        
        return IntentResult(
            intent=intent,
            confidence=float(best_confidence),
            metadata={
                "classifier": "semantic",
                "best_example": best_example,
                "similarity_method": "embeddings" if self.use_embeddings else "simple"
            }
        )
    
    def get_supported_intents(self) -> List[Intent]:
        """Get list of supported intents"""
        supported = []
        for intent_name in self.examples.keys():
            try:
                supported.append(Intent(intent_name))
            except ValueError:
                self.logger.warning(f"Examples exist for unsupported intent: {intent_name}")
        return supported
    
    def add_example(self, intent: Intent, example: str) -> bool:
        """Add a new example for an intent"""
        intent_name = intent.value
        if intent_name not in self.examples:
            self.examples[intent_name] = []
        
        self.examples[intent_name].append(example)
        
        # Recompute embeddings for this intent
        if self.use_embeddings:
            try:
                embeddings = self.model.encode(self.examples[intent_name])
                self.embeddings_cache[intent_name] = embeddings
            except Exception as e:
                self.logger.error(f"Error recomputing embeddings: {e}")
                return False
        
        self.logger.info(f"Added example for intent {intent_name}: '{example}'")
        return True
    
    def get_examples(self, intent: Intent) -> List[str]:
        """Get examples for an intent"""
        return self.examples.get(intent.value, [])
    
    def remove_example(self, intent: Intent, example: str) -> bool:
        """Remove an example for an intent"""
        intent_name = intent.value
        if intent_name in self.examples and example in self.examples[intent_name]:
            self.examples[intent_name].remove(example)
            
            # Recompute embeddings
            if self.use_embeddings and self.examples[intent_name]:
                try:
                    embeddings = self.model.encode(self.examples[intent_name])
                    self.embeddings_cache[intent_name] = embeddings
                except Exception as e:
                    self.logger.error(f"Error recomputing embeddings: {e}")
            
            self.logger.info(f"Removed example for intent {intent_name}: '{example}'")
            return True
        return False