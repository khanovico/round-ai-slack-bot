from enum import Enum
from abc import ABC, abstractmethod
from typing import Dict, Any, List
from dataclasses import dataclass


class Intent(str, Enum):
    GREETING = "greeting"
    SQL_QUERY = "sql_query"
    SHOW_SQL = "show_sql"
    EXPORT_CSV = "export_csv"
    UNKNOWN = "unknown"  # Default fallback intent


@dataclass
class IntentResult:
    """Result of intent classification"""
    intent: Intent
    confidence: float
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class BaseClassifier(ABC):
    """Abstract base class for intent classifiers"""
    
    def __init__(self, confidence_threshold: float = 0.7, fallback_intent: Intent = Intent.UNKNOWN):
        self.confidence_threshold = confidence_threshold
        self.fallback_intent = fallback_intent
    
    @abstractmethod
    def _classify_internal(self, text: str) -> IntentResult:
        """Internal classification method to be implemented by subclasses"""
        pass
    
    def classify(self, text: str) -> IntentResult:
        """Classify the intent of the given text with fallback handling"""
        result = self._classify_internal(text)
        
        # If confidence is too low, return fallback intent
        if result.confidence < self.confidence_threshold:
            return IntentResult(
                intent=self.fallback_intent,
                confidence=0.1,
                metadata={
                    "original_intent": result.intent.value,
                    "original_confidence": result.confidence,
                    "fallback_reason": "Low confidence"
                }
            )
        
        return result
    
    @abstractmethod
    def get_supported_intents(self) -> List[Intent]:
        """Get list of supported intents"""
        pass
    
    def is_confident(self, result: IntentResult) -> bool:
        """Check if the classification result meets confidence threshold"""
        return result.confidence >= self.confidence_threshold
    
    def get_classifier_info(self) -> Dict[str, Any]:
        """Get information about the classifier"""
        return {
            "classifier_type": self.__class__.__name__,
            "confidence_threshold": self.confidence_threshold,
            "fallback_intent": self.fallback_intent.value,
            "supported_intents": [intent.value for intent in self.get_supported_intents()]
        }
    