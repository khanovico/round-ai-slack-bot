"""
Regex-based intent classifier
"""
import re
import json
from pathlib import Path
from typing import List, Dict
from app.ai.intent_classifier.base_classifier import BaseClassifier, Intent, IntentResult
from app.core.logging_config import get_logger


class RegexClassifier(BaseClassifier):
    """Regex-based intent classifier using pattern matching"""
    
    def __init__(self, confidence_threshold: float = 0.8, patterns_file: str = None):
        super().__init__(confidence_threshold)
        self.logger = get_logger("app.ai.regex_classifier")
        
        # Load patterns from file
        if patterns_file is None:
            patterns_file = Path(__file__).parent / "intent_patterns.json"
        
        self.patterns = self._load_patterns(patterns_file)
        self.compiled_patterns = self._compile_patterns()
        
        self.logger.info(f"RegexClassifier initialized with {len(self.patterns)} patterns")
    
    def _load_patterns(self, patterns_file: Path) -> Dict[str, str]:
        """Load regex patterns from JSON file"""
        try:
            with open(patterns_file, 'r', encoding='utf-8') as f:
                patterns = json.load(f)
            self.logger.debug(f"Loaded patterns from {patterns_file}")
            return patterns
        except Exception as e:
            self.logger.error(f"Error loading patterns: {e}")
            return {}
    
    def _compile_patterns(self) -> Dict[str, re.Pattern]:
        """Compile regex patterns for better performance"""
        compiled = {}
        for intent_name, pattern in self.patterns.items():
            try:
                compiled[intent_name] = re.compile(pattern, re.IGNORECASE | re.MULTILINE)
            except re.error as e:
                self.logger.error(f"Invalid regex pattern for intent '{intent_name}': {e}")
        return compiled
    
    def _classify_internal(self, text: str) -> IntentResult:
        """Classify intent using regex patterns"""
        text = text.strip().lower()
        best_match = None
        best_confidence = 0.0
        matched_groups = {}
        
        for intent_name, pattern in self.compiled_patterns.items():
            match = pattern.search(text)
            if match:
                # Calculate confidence based on match quality
                match_length = len(match.group(0))
                text_length = len(text)
                
                # Higher confidence for longer matches relative to text length
                confidence = min(0.9, (match_length / text_length) * 1.2)
                
                # Boost confidence for exact matches
                if match.group(0).strip() == text:
                    confidence = 0.95
                
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_match = intent_name
                    matched_groups = match.groupdict() if match.groups() else {}
        
        # Map to Intent enum
        if best_match:
            try:
                intent = Intent(best_match)
            except ValueError:
                self.logger.warning(f"Unknown intent: {best_match}")
                intent = Intent.SQL_QUERY  # Default fallback
        else:
            intent = Intent.SQL_QUERY
            best_confidence = 0.1  # Very low confidence for no match
        
        return IntentResult(
            intent=intent,
            confidence=best_confidence,
            metadata={
                "classifier": "regex",
                "matched_pattern": self.patterns.get(best_match, ""),
                "matched_groups": matched_groups
            }
        )
    
    def get_supported_intents(self) -> List[Intent]:
        """Get list of supported intents"""
        supported = []
        for intent_name in self.patterns.keys():
            try:
                supported.append(Intent(intent_name))
            except ValueError:
                self.logger.warning(f"Pattern exists for unsupported intent: {intent_name}")
        return supported
    
    def add_pattern(self, intent: Intent, pattern: str) -> bool:
        """Add a new regex pattern for an intent"""
        try:
            compiled_pattern = re.compile(pattern, re.IGNORECASE | re.MULTILINE)
            self.patterns[intent.value] = pattern
            self.compiled_patterns[intent.value] = compiled_pattern
            self.logger.info(f"Added pattern for intent: {intent.value}")
            return True
        except re.error as e:
            self.logger.error(f"Invalid regex pattern: {e}")
            return False
    
    def remove_pattern(self, intent: Intent) -> bool:
        """Remove pattern for an intent"""
        intent_name = intent.value
        if intent_name in self.patterns:
            del self.patterns[intent_name]
            del self.compiled_patterns[intent_name]
            self.logger.info(f"Removed pattern for intent: {intent_name}")
            return True
        return False
    
    def get_pattern(self, intent: Intent) -> str:
        """Get the regex pattern for an intent"""
        return self.patterns.get(intent.value, "")