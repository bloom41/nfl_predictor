"""
Unified player name extraction utility
Consolidates duplicate functionality from multiple modules
"""
import re
import logging
from typing import List, Optional, Set, Dict, Any
from src.utils.input_validation import InputValidator, SecurityValidator

logger = logging.getLogger(__name__)

class PlayerNameExtractor:
    """Unified player name extraction and validation"""
    
    def __init__(self):
        self.validator = InputValidator()
        self._player_cache: Set[str] = set()
        self._name_patterns = [
            # Pattern 1: "First Last POS - TEAM"
            re.compile(r'([A-Za-z\'\-\s]+)\s+(?:QB|RB|WR|TE)\s*[-–]\s*([A-Z]{2,4})', re.IGNORECASE),
            # Pattern 2: "First Last - TEAM"  
            re.compile(r'([A-Za-z\'\-\s]+)\s*[-–]\s*([A-Z]{2,4})'),
            # Pattern 3: "Last, First TEAM"
            re.compile(r'([A-Za-z\'\-]+),\s*([A-Za-z\'\-\s]+)\s+([A-Z]{2,4})'),
            # Pattern 4: Simple name matching
            re.compile(r'\b([A-Z][a-z]+\s+[A-Z][a-z]+)\b')
        ]
    
    def extract_from_text(self, text: str) -> List[str]:
        """Extract player names from text using all patterns"""
        if not text:
            return []
        
        # Validate and sanitize input
        is_safe, sanitized_text = SecurityValidator.validate_safe_input(text, "player_extraction")
        if not is_safe:
            logger.warning("Unsafe text provided for player extraction")
            return []
        
        extracted_names = set()
        
        # Try each pattern
        for pattern in self._name_patterns:
            matches = pattern.findall(sanitized_text)
            
            for match in matches:
                if isinstance(match, tuple):
                    if len(match) >= 2:
                        # Handle "Last, First" format
                        if len(match) == 3:
                            name = f"{match[1].strip()} {match[0].strip()}"
                        else:
                            name = match[0].strip()
                    else:
                        name = match[0].strip() if match else ""
                else:
                    name = match.strip()
                
                # Validate extracted name
                is_valid, validated_name = self.validator.validate_player_name(name)
                if is_valid and len(validated_name) > 3:
                    extracted_names.add(validated_name)
        
        return list(extracted_names)
    
    def extract_with_confidence(self, text: str) -> List[Dict[str, Any]]:
        """Extract player names with confidence scores"""
        names = self.extract_from_text(text)
        
        results = []
        for name in names:
            confidence = self._calculate_confidence(name, text)
            results.append({
                'name': name,
                'confidence': confidence,
                'is_likely_player': confidence > 0.7
            })
        
        # Sort by confidence
        results.sort(key=lambda x: x['confidence'], reverse=True)
        return results
    
    def _calculate_confidence(self, name: str, context: str) -> float:
        """Calculate confidence that this is actually a player name"""
        confidence = 0.5  # Base confidence
        
        # Higher confidence if name appears with football-related keywords
        football_keywords = ['quarterback', 'qb', 'running back', 'rb', 'wide receiver', 'wr', 
                           'tight end', 'te', 'touchdown', 'yard', 'pass', 'rush', 'catch']
        
        context_lower = context.lower()
        for keyword in football_keywords:
            if keyword in context_lower:
                confidence += 0.1
                if confidence >= 0.9:
                    break
        
        # Higher confidence for common NFL name patterns
        name_parts = name.split()
        if len(name_parts) == 2:
            confidence += 0.1
        
        # Lower confidence for very common words
        common_words = {'and', 'the', 'for', 'with', 'team', 'game', 'play', 'time'}
        if any(part.lower() in common_words for part in name_parts):
            confidence -= 0.3
        
        return min(max(confidence, 0.0), 1.0)
    
    def is_likely_player_reference(self, text: str) -> bool:
        """Check if text likely contains player references"""
        if not text or len(text) < 10:
            return False
        
        # Look for football-related context
        football_indicators = [
            'quarterback', 'qb', 'running back', 'rb', 'wide receiver', 'wr',
            'tight end', 'te', 'nfl', 'football', 'touchdown', 'yard', 'stats'
        ]
        
        text_lower = text.lower()
        return any(indicator in text_lower for indicator in football_indicators)

# Global instance for easy access
player_name_extractor = PlayerNameExtractor()

def extract_player_names(text: str) -> List[str]:
    """Convenience function for quick player name extraction"""
    return player_name_extractor.extract_from_text(text)

def extract_player_names_with_confidence(text: str) -> List[Dict[str, Any]]:
    """Convenience function for extraction with confidence scores"""
    return player_name_extractor.extract_with_confidence(text)

__all__ = ['PlayerNameExtractor', 'player_name_extractor', 'extract_player_names', 'extract_player_names_with_confidence']