"""
Intent Classifier Factory for managing singleton instances
"""
from typing import Dict, Any, Optional
from .base_classifier import BaseClassifier, Intent
from .regex.regex_classifier import RegexClassifier
from .semantic.semantic_classifier import SemanticClassifier


class IntentClassifierFactory:
    """Factory class for managing intent classifier instances with singleton pattern"""
    
    _instances: Dict[str, BaseClassifier] = {}
    _default_configs = {
        'regex': {
            'confidence_threshold': 0.8,
            'fallback_intent': Intent.UNKNOWN
        },
        'semantic': {
            'confidence_threshold': 0.6,
            'fallback_intent': Intent.SQL_QUERY
        }
    }
    
    @classmethod
    def get_regex_classifier(cls, confidence_threshold: Optional[float] = None, 
                           fallback_intent: Optional[Intent] = None) -> RegexClassifier:
        """Get or create RegexClassifier instance"""
        config = cls._get_config('regex', confidence_threshold, fallback_intent)
        key = f"regex_{config['confidence_threshold']}"
        
        if key not in cls._instances:
            cls._instances[key] = RegexClassifier(
                confidence_threshold=config['confidence_threshold']
            )
        
        return cls._instances[key]
    
    @classmethod
    def get_semantic_classifier(cls, confidence_threshold: Optional[float] = None,
                              fallback_intent: Optional[Intent] = None) -> SemanticClassifier:
        """Get or create SemanticClassifier instance"""
        config = cls._get_config('semantic', confidence_threshold, fallback_intent)
        key = f"semantic_{config['confidence_threshold']}_{config['fallback_intent'].value}"
        
        if key not in cls._instances:
            cls._instances[key] = SemanticClassifier(
                confidence_threshold=config['confidence_threshold'],
                fallback_intent=config['fallback_intent']
            )
        
        return cls._instances[key]
    
    @classmethod
    def _get_config(cls, classifier_type: str, confidence_threshold: Optional[float],
                   fallback_intent: Optional[Intent]) -> Dict[str, Any]:
        """Get configuration for classifier, using defaults if not specified"""
        config = cls._default_configs[classifier_type].copy()
        
        if confidence_threshold is not None:
            config['confidence_threshold'] = confidence_threshold
        if fallback_intent is not None:
            config['fallback_intent'] = fallback_intent
            
        return config
    
    @classmethod
    def clear_instances(cls):
        """Clear all cached instances (useful for testing)"""
        cls._instances.clear()
    
    @classmethod
    def get_instance_count(cls) -> int:
        """Get number of cached instances"""
        return len(cls._instances)