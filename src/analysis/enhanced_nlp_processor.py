#!/usr/bin/env python3
"""
Enhanced Natural Language Processing for News Comprehension
Advanced NLP for breaking news analysis and sentiment understanding
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
import re
import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum
import nltk
try:
    from nltk.sentiment import SentimentIntensityAnalyzer
    from nltk.tokenize import word_tokenize, sent_tokenize
    from nltk.corpus import stopwords
    from nltk.stem import WordNetLemmatizer
    from nltk.tag import pos_tag
    from nltk.chunk import ne_chunk
    from nltk.tree import Tree
except ImportError:
    print("NLTK not available, using basic sentiment analysis")

logger = logging.getLogger(__name__)

class NewsCategory(Enum):
    """Categories of NFL news"""
    INJURY = "injury"
    TRADE = "trade"
    SUSPENSION = "suspension"
    COACHING_CHANGE = "coaching_change"
    DEPTH_CHART = "depth_chart"
    CONTRACT = "contract"
    PERFORMANCE = "performance"
    WEATHER = "weather"
    TEAM_NEWS = "team_news"
    GENERAL = "general"

class SentimentPolarity(Enum):
    """Sentiment polarity levels"""
    VERY_POSITIVE = "very_positive"
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    VERY_NEGATIVE = "very_negative"

class ImpactLevel(Enum):
    """Fantasy impact levels"""
    CRITICAL = "critical"      # Major lineup changes needed
    HIGH = "high"              # Significant impact
    MODERATE = "moderate"      # Some impact
    LOW = "low"                # Minor impact
    MINIMAL = "minimal"        # Little to no impact

@dataclass
class EntityMention:
    """Named entity mention in text"""
    entity_text: str
    entity_type: str  # PERSON, ORGANIZATION, etc.
    start_position: int
    end_position: int
    confidence: float

@dataclass
class NewsAnalysisResult:
    """Result of news article analysis"""
    article_id: str
    headline: str
    content: str
    publish_date: datetime
    
    # Categorization
    category: NewsCategory
    category_confidence: float
    
    # Sentiment analysis
    sentiment_polarity: SentimentPolarity
    sentiment_score: float  # -1 to 1
    sentiment_confidence: float
    
    # Entity extraction
    players_mentioned: List[str]
    teams_mentioned: List[str]
    coaches_mentioned: List[str]
    entities: List[EntityMention]
    
    # Impact assessment
    fantasy_impact_level: ImpactLevel
    impact_reasoning: str
    affected_positions: List[str]
    
    # Key insights
    key_phrases: List[str]
    action_items: List[str]  # What fantasy managers should do
    confidence_changes: Dict[str, float]  # Player confidence adjustments
    
    # Processing metadata
    processing_timestamp: datetime
    nlp_confidence: float

class EnhancedNLPProcessor:
    """
    Enhanced NLP processor for fantasy football news analysis
    Uses advanced NLP techniques for news comprehension
    """
    
    def __init__(self):
        """Initialize enhanced NLP processor"""
        self.logger = logging.getLogger(__name__)
        
        # Initialize NLTK components
        self._initialize_nltk()
        
        # Fantasy football specific keywords and patterns
        self.injury_keywords = [
            'injured', 'hurt', 'questionable', 'doubtful', 'out', 'ir', 'injured reserve',
            'strain', 'sprain', 'tear', 'surgery', 'concussion', 'ankle', 'knee', 'hamstring',
            'shoulder', 'back', 'groin', 'calf', 'quad', 'hip', 'wrist', 'finger', 'ribs',
            'aggravated', 'setback', 'recovery', 'rehab', 'limited', 'dnp', 'did not practice'
        ]
        
        self.positive_keywords = [
            'cleared', 'healthy', 'returned', 'practicing', 'full participant', 'activated',
            'expected to play', 'good to go', 'no limitations', 'full speed', 'recovered',
            'upgraded', 'probable', 'playing', 'starting', 'increased role', 'more targets',
            'featured', 'breakout', 'explosive', 'dominant'
        ]
        
        self.negative_keywords = [
            'benched', 'demoted', 'reduced role', 'losing snaps', 'fumble', 'dropped passes',
            'struggling', 'ineffective', 'disappointing', 'concerning', 'suspended',
            'disciplinary', 'arrest', 'legal trouble', 'off-field', 'investigation'
        ]
        
        self.impact_keywords = {
            ImpactLevel.CRITICAL: ['ruled out', 'season ending', 'ir', 'major surgery', 'suspended', 'traded'],
            ImpactLevel.HIGH: ['doubtful', 'likely out', 'significant injury', 'starting role', 'lead back'],
            ImpactLevel.MODERATE: ['questionable', 'limited', 'snap count', 'rotational', 'depth chart'],
            ImpactLevel.LOW: ['probable', 'minor', 'day-to-day', 'precautionary', 'rest'],
            ImpactLevel.MINIMAL: ['full participant', 'no concerns', 'expected to play']
        }
        
        # Position and team mappings
        self.position_keywords = {
            'QB': ['quarterback', 'qb', 'signal caller', 'passer'],
            'RB': ['running back', 'rb', 'rusher', 'backfield', 'runner'],
            'WR': ['wide receiver', 'wr', 'receiver', 'wideout', 'pass catcher'],
            'TE': ['tight end', 'te', 'inline', 'h-back'],
            'K': ['kicker', 'k', 'placekicker'],
            'DEF': ['defense', 'dst', 'defensive']
        }
        
        self.nfl_teams = {
            'arizona cardinals': 'ARI', 'atlanta falcons': 'ATL', 'baltimore ravens': 'BAL',
            'buffalo bills': 'BUF', 'carolina panthers': 'CAR', 'chicago bears': 'CHI',
            'cincinnati bengals': 'CIN', 'cleveland browns': 'CLE', 'dallas cowboys': 'DAL',
            'denver broncos': 'DEN', 'detroit lions': 'DET', 'green bay packers': 'GB',
            'houston texans': 'HOU', 'indianapolis colts': 'IND', 'jacksonville jaguars': 'JAX',
            'kansas city chiefs': 'KC', 'las vegas raiders': 'LV', 'los angeles chargers': 'LAC',
            'los angeles rams': 'LAR', 'miami dolphins': 'MIA', 'minnesota vikings': 'MIN',
            'new england patriots': 'NE', 'new orleans saints': 'NO', 'new york giants': 'NYG',
            'new york jets': 'NYJ', 'philadelphia eagles': 'PHI', 'pittsburgh steelers': 'PIT',
            'san francisco 49ers': 'SF', 'seattle seahawks': 'SEA', 'tampa bay buccaneers': 'TB',
            'tennessee titans': 'TEN', 'washington commanders': 'WAS'
        }
        
        self.logger.info("Enhanced NLP Processor initialized")
    
    def _initialize_nltk(self):
        """Initialize NLTK components"""
        try:
            # Download required NLTK data
            required_data = [
                'punkt', 'stopwords', 'wordnet', 'averaged_perceptron_tagger',
                'maxent_ne_chunker', 'words', 'vader_lexicon'
            ]
            
            for data in required_data:
                try:
                    nltk.data.find(f'tokenizers/{data}')
                except LookupError:
                    try:
                        nltk.download(data, quiet=True)
                    except:
                        pass
            
            # Initialize components
            self.sentiment_analyzer = SentimentIntensityAnalyzer()
            self.lemmatizer = WordNetLemmatizer()
            self.stop_words = set(stopwords.words('english'))
            
        except Exception as e:
            self.logger.warning(f"NLTK initialization failed: {e}")
            self.sentiment_analyzer = None
            self.lemmatizer = None
            self.stop_words = set()
    
    def analyze_news_article(self, headline: str, content: str, article_id: str = None,
                           publish_date: datetime = None) -> NewsAnalysisResult:
        """
        Analyze a news article for fantasy football insights
        
        Args:
            headline: Article headline
            content: Article content
            article_id: Unique article identifier
            publish_date: When article was published
            
        Returns:
            NewsAnalysisResult with comprehensive analysis
        """
        try:
            self.logger.debug(f"Analyzing news article: {headline[:50]}...")
            
            # Default values
            if article_id is None:
                article_id = f"article_{datetime.now().timestamp()}"
            if publish_date is None:
                publish_date = datetime.now()
            
            # Combine headline and content for analysis
            full_text = f"{headline}. {content}"
            
            # Categorize the news
            category, category_confidence = self._categorize_news(full_text)
            
            # Analyze sentiment
            sentiment_polarity, sentiment_score, sentiment_confidence = self._analyze_sentiment(full_text)
            
            # Extract entities
            entities = self._extract_entities(full_text)
            players_mentioned = self._extract_players(full_text, entities)
            teams_mentioned = self._extract_teams(full_text)
            coaches_mentioned = self._extract_coaches(full_text, entities)
            
            # Assess fantasy impact
            impact_level, impact_reasoning, affected_positions = self._assess_fantasy_impact(
                full_text, category, sentiment_score, players_mentioned
            )
            
            # Extract key insights
            key_phrases = self._extract_key_phrases(full_text, category)
            action_items = self._generate_action_items(
                category, impact_level, players_mentioned, sentiment_score
            )
            confidence_changes = self._calculate_confidence_changes(
                players_mentioned, category, sentiment_score, impact_level
            )
            
            # Calculate overall NLP confidence
            nlp_confidence = self._calculate_nlp_confidence(
                category_confidence, sentiment_confidence, len(entities), len(players_mentioned)
            )
            
            return NewsAnalysisResult(
                article_id=article_id,
                headline=headline,
                content=content,
                publish_date=publish_date,
                category=category,
                category_confidence=category_confidence,
                sentiment_polarity=sentiment_polarity,
                sentiment_score=sentiment_score,
                sentiment_confidence=sentiment_confidence,
                players_mentioned=players_mentioned,
                teams_mentioned=teams_mentioned,
                coaches_mentioned=coaches_mentioned,
                entities=entities,
                fantasy_impact_level=impact_level,
                impact_reasoning=impact_reasoning,
                affected_positions=affected_positions,
                key_phrases=key_phrases,
                action_items=action_items,
                confidence_changes=confidence_changes,
                processing_timestamp=datetime.now(),
                nlp_confidence=nlp_confidence
            )
            
        except Exception as e:
            self.logger.error(f"Error analyzing news article: {e}")
            return self._create_fallback_analysis(headline, content, article_id, publish_date)
    
    def _categorize_news(self, text: str) -> Tuple[NewsCategory, float]:
        """Categorize news article"""
        try:
            text_lower = text.lower()
            category_scores = {}
            
            # Score each category based on keyword presence
            category_keywords = {
                NewsCategory.INJURY: self.injury_keywords,
                NewsCategory.TRADE: ['traded', 'trade', 'acquired', 'deal', 'exchange', 'waiver'],
                NewsCategory.SUSPENSION: ['suspended', 'suspension', 'banned', 'violation', 'disciplinary'],
                NewsCategory.COACHING_CHANGE: ['coach', 'fired', 'hired', 'promoted', 'coordinator'],
                NewsCategory.DEPTH_CHART: ['depth chart', 'starter', 'backup', 'depth', 'rotation'],
                NewsCategory.CONTRACT: ['contract', 'extension', 'signed', 'deal', 'money', 'salary'],
                NewsCategory.PERFORMANCE: ['performance', 'stats', 'yards', 'touchdown', 'catch', 'carry'],
                NewsCategory.WEATHER: ['weather', 'rain', 'snow', 'wind', 'temperature', 'conditions'],
                NewsCategory.TEAM_NEWS: ['team', 'organization', 'facility', 'practice', 'meeting']
            }
            
            for category, keywords in category_keywords.items():
                score = sum(1 for keyword in keywords if keyword in text_lower)
                if score > 0:
                    category_scores[category] = score / len(keywords)
            
            if not category_scores:
                return NewsCategory.GENERAL, 0.5
            
            # Find highest scoring category
            best_category = max(category_scores.items(), key=lambda x: x[1])
            
            return best_category[0], min(0.95, best_category[1] * 2)  # Scale confidence
            
        except Exception as e:
            self.logger.error(f"Error categorizing news: {e}")
            return NewsCategory.GENERAL, 0.3
    
    def _analyze_sentiment(self, text: str) -> Tuple[SentimentPolarity, float, float]:
        """Analyze sentiment of text"""
        try:
            if self.sentiment_analyzer:
                # Use VADER sentiment analyzer
                scores = self.sentiment_analyzer.polarity_scores(text)
                compound_score = scores['compound']
                
                # Classify polarity
                if compound_score >= 0.5:
                    polarity = SentimentPolarity.VERY_POSITIVE
                elif compound_score >= 0.1:
                    polarity = SentimentPolarity.POSITIVE
                elif compound_score <= -0.5:
                    polarity = SentimentPolarity.VERY_NEGATIVE
                elif compound_score <= -0.1:
                    polarity = SentimentPolarity.NEGATIVE
                else:
                    polarity = SentimentPolarity.NEUTRAL
                
                confidence = abs(compound_score)
                
            else:
                # Fallback to keyword-based sentiment
                compound_score, confidence = self._keyword_sentiment_analysis(text)
                
                if compound_score >= 0.3:
                    polarity = SentimentPolarity.POSITIVE
                elif compound_score <= -0.3:
                    polarity = SentimentPolarity.NEGATIVE
                else:
                    polarity = SentimentPolarity.NEUTRAL
            
            return polarity, compound_score, confidence
            
        except Exception as e:
            self.logger.error(f"Error analyzing sentiment: {e}")
            return SentimentPolarity.NEUTRAL, 0.0, 0.3
    
    def _keyword_sentiment_analysis(self, text: str) -> Tuple[float, float]:
        """Fallback keyword-based sentiment analysis"""
        text_lower = text.lower()
        
        positive_count = sum(1 for keyword in self.positive_keywords if keyword in text_lower)
        negative_count = sum(1 for keyword in self.negative_keywords if keyword in text_lower)
        
        total_sentiment_words = positive_count + negative_count
        
        if total_sentiment_words == 0:
            return 0.0, 0.3
        
        sentiment_score = (positive_count - negative_count) / max(total_sentiment_words, 1)
        confidence = min(0.8, total_sentiment_words / 10.0)
        
        return sentiment_score, confidence
    
    def _extract_entities(self, text: str) -> List[EntityMention]:
        """Extract named entities from text"""
        try:
            entities = []
            
            if self.sentiment_analyzer:  # NLTK available
                # Tokenize and tag
                tokens = word_tokenize(text)
                pos_tags = pos_tag(tokens)
                
                # Named entity recognition
                chunks = ne_chunk(pos_tags, binary=False)
                
                current_entity = []
                current_label = None
                start_pos = 0
                
                for chunk in chunks:
                    if isinstance(chunk, Tree):
                        # Named entity
                        entity_text = ' '.join([token for token, pos in chunk.leaves()])
                        entity_type = chunk.label()
                        
                        entities.append(EntityMention(
                            entity_text=entity_text,
                            entity_type=entity_type,
                            start_position=start_pos,
                            end_position=start_pos + len(entity_text),
                            confidence=0.8
                        ))
                    
                    start_pos += len(str(chunk)) + 1
            
            return entities
            
        except Exception as e:
            self.logger.error(f"Error extracting entities: {e}")
            return []
    
    def _extract_players(self, text: str, entities: List[EntityMention]) -> List[str]:
        """Extract player names from text"""
        try:
            players = []
            text_lower = text.lower()
            
            # Extract from named entities (PERSON type)
            for entity in entities:
                if entity.entity_type == 'PERSON':
                    players.append(entity.entity_text)
            
            # Pattern-based extraction for common name formats
            name_patterns = [
                r'\b[A-Z][a-z]+ [A-Z][a-z]+\b',  # First Last
                r'\b[A-Z]\. [A-Z][a-z]+\b',      # F. Last
                r'\b[A-Z][a-z]+ [A-Z]\. [A-Z][a-z]+\b'  # First M. Last
            ]
            
            for pattern in name_patterns:
                matches = re.findall(pattern, text)
                for match in matches:
                    if match not in players and len(match.split()) >= 2:
                        # Filter out common non-player names
                        if not any(word in match.lower() for word in ['coach', 'dr.', 'mr.', 'ms.']):
                            players.append(match)
            
            # Remove duplicates while preserving order
            unique_players = []
            for player in players:
                if player not in unique_players:
                    unique_players.append(player)
            
            return unique_players[:10]  # Limit to reasonable number
            
        except Exception as e:
            self.logger.error(f"Error extracting players: {e}")
            return []
    
    def _extract_teams(self, text: str) -> List[str]:
        """Extract team names from text"""
        try:
            teams = []
            text_lower = text.lower()
            
            # Check for team names and abbreviations
            for team_name, abbrev in self.nfl_teams.items():
                if team_name in text_lower or abbrev.lower() in text_lower:
                    teams.append(abbrev)
            
            # Remove duplicates
            return list(set(teams))
            
        except Exception as e:
            self.logger.error(f"Error extracting teams: {e}")
            return []
    
    def _extract_coaches(self, text: str, entities: List[EntityMention]) -> List[str]:
        """Extract coach names from text"""
        try:
            coaches = []
            text_lower = text.lower()
            
            # Look for coach-related context
            coach_contexts = ['coach', 'head coach', 'coordinator', 'coaching staff']
            
            for entity in entities:
                if entity.entity_type == 'PERSON':
                    # Check if mentioned near coaching context
                    entity_start = max(0, entity.start_position - 50)
                    entity_end = min(len(text), entity.end_position + 50)
                    context = text[entity_start:entity_end].lower()
                    
                    if any(coach_term in context for coach_term in coach_contexts):
                        coaches.append(entity.entity_text)
            
            return coaches
            
        except Exception as e:
            self.logger.error(f"Error extracting coaches: {e}")
            return []
    
    def _assess_fantasy_impact(self, text: str, category: NewsCategory, 
                             sentiment_score: float, players_mentioned: List[str]) -> Tuple[ImpactLevel, str, List[str]]:
        """Assess fantasy football impact"""
        try:
            text_lower = text.lower()
            
            # Base impact by category
            category_impact = {
                NewsCategory.INJURY: ImpactLevel.HIGH,
                NewsCategory.TRADE: ImpactLevel.HIGH,
                NewsCategory.SUSPENSION: ImpactLevel.CRITICAL,
                NewsCategory.COACHING_CHANGE: ImpactLevel.MODERATE,
                NewsCategory.DEPTH_CHART: ImpactLevel.MODERATE,
                NewsCategory.CONTRACT: ImpactLevel.LOW,
                NewsCategory.PERFORMANCE: ImpactLevel.LOW,
                NewsCategory.WEATHER: ImpactLevel.LOW,
                NewsCategory.TEAM_NEWS: ImpactLevel.MINIMAL,
                NewsCategory.GENERAL: ImpactLevel.MINIMAL
            }
            
            base_impact = category_impact.get(category, ImpactLevel.MINIMAL)
            
            # Adjust based on keyword presence
            impact_adjustment = 0
            reasoning_parts = []
            
            for impact_level, keywords in self.impact_keywords.items():
                keyword_count = sum(1 for keyword in keywords if keyword in text_lower)
                if keyword_count > 0:
                    if impact_level == ImpactLevel.CRITICAL:
                        impact_adjustment = max(impact_adjustment, 3)
                        reasoning_parts.append("Critical keywords detected")
                    elif impact_level == ImpactLevel.HIGH:
                        impact_adjustment = max(impact_adjustment, 2)
                        reasoning_parts.append("High impact keywords detected")
                    elif impact_level == ImpactLevel.MODERATE:
                        impact_adjustment = max(impact_adjustment, 1)
                    elif impact_level == ImpactLevel.MINIMAL:
                        impact_adjustment = min(impact_adjustment, -1)
            
            # Adjust based on sentiment
            if sentiment_score < -0.5:
                impact_adjustment += 1
                reasoning_parts.append("Very negative sentiment")
            elif sentiment_score > 0.5:
                impact_adjustment -= 1
            
            # Determine final impact level
            impact_levels = [ImpactLevel.MINIMAL, ImpactLevel.LOW, ImpactLevel.MODERATE, 
                           ImpactLevel.HIGH, ImpactLevel.CRITICAL]
            
            base_index = impact_levels.index(base_impact)
            final_index = max(0, min(len(impact_levels) - 1, base_index + impact_adjustment))
            final_impact = impact_levels[final_index]
            
            # Generate reasoning
            if not reasoning_parts:
                reasoning_parts.append(f"Based on {category.value} category")
            
            reasoning = "; ".join(reasoning_parts)
            
            # Identify affected positions
            affected_positions = []
            for position, keywords in self.position_keywords.items():
                if any(keyword in text_lower for keyword in keywords):
                    affected_positions.append(position)
            
            if not affected_positions and players_mentioned:
                affected_positions = ['UNKNOWN']
            
            return final_impact, reasoning, affected_positions
            
        except Exception as e:
            self.logger.error(f"Error assessing fantasy impact: {e}")
            return ImpactLevel.MINIMAL, "Error in analysis", []
    
    def _extract_key_phrases(self, text: str, category: NewsCategory) -> List[str]:
        """Extract key phrases from text"""
        try:
            phrases = []
            text_lower = text.lower()
            
            # Category-specific key phrase patterns
            phrase_patterns = {
                NewsCategory.INJURY: [
                    r'(injured|hurt|strain|sprain|tear) (?:his|her|their) (\w+)',
                    r'(\w+ injury)',
                    r'(questionable|doubtful|out) for (\w+)',
                    r'placed on (injured reserve|ir)'
                ],
                NewsCategory.TRADE: [
                    r'traded to (\w+)',
                    r'acquired (\w+ \w+)',
                    r'(\w+) deal'
                ],
                NewsCategory.PERFORMANCE: [
                    r'(\d+) (yards|touchdowns|catches|carries)',
                    r'(career high|season high|best performance)'
                ]
            }
            
            patterns = phrase_patterns.get(category, [])
            
            for pattern in patterns:
                matches = re.findall(pattern, text_lower)
                for match in matches:
                    if isinstance(match, tuple):
                        phrase = ' '.join(match)
                    else:
                        phrase = match
                    phrases.append(phrase)
            
            return phrases[:5]  # Limit to top 5
            
        except Exception as e:
            self.logger.error(f"Error extracting key phrases: {e}")
            return []
    
    def _generate_action_items(self, category: NewsCategory, impact_level: ImpactLevel,
                             players_mentioned: List[str], sentiment_score: float) -> List[str]:
        """Generate actionable items for fantasy managers"""
        try:
            actions = []
            
            if impact_level == ImpactLevel.CRITICAL:
                if players_mentioned:
                    actions.append(f"Remove {players_mentioned[0]} from all lineups immediately")
                    actions.append("Identify replacement options on waiver wire")
                
            elif impact_level == ImpactLevel.HIGH:
                if category == NewsCategory.INJURY:
                    if players_mentioned:
                        actions.append(f"Monitor {players_mentioned[0]} injury status closely")
                        actions.append("Prepare backup options for this week")
                elif category == NewsCategory.TRADE:
                    if players_mentioned:
                        actions.append(f"Reassess {players_mentioned[0]} value in new situation")
                
            elif impact_level == ImpactLevel.MODERATE:
                if players_mentioned:
                    actions.append(f"Keep {players_mentioned[0]} but monitor situation")
                    if sentiment_score > 0.3:
                        actions.append("Consider as potential buy-low candidate")
                    elif sentiment_score < -0.3:
                        actions.append("Consider selling while value remains")
            
            # General actions based on sentiment
            if sentiment_score > 0.5 and players_mentioned:
                actions.append(f"Consider targeting {players_mentioned[0]} as breakout candidate")
            elif sentiment_score < -0.5 and players_mentioned:
                actions.append(f"Avoid {players_mentioned[0]} until situation clarifies")
            
            return actions[:3]  # Limit to top 3 actions
            
        except Exception as e:
            self.logger.error(f"Error generating action items: {e}")
            return []
    
    def _calculate_confidence_changes(self, players_mentioned: List[str], category: NewsCategory,
                                    sentiment_score: float, impact_level: ImpactLevel) -> Dict[str, float]:
        """Calculate confidence adjustments for mentioned players"""
        try:
            confidence_changes = {}
            
            for player in players_mentioned:
                change = 0.0
                
                # Base change by category
                if category == NewsCategory.INJURY:
                    change = -0.3
                elif category == NewsCategory.TRADE:
                    change = -0.1  # Uncertainty
                elif category == NewsCategory.SUSPENSION:
                    change = -0.5
                elif category == NewsCategory.PERFORMANCE:
                    change = 0.1 if sentiment_score > 0 else -0.1
                
                # Adjust by sentiment
                sentiment_adjustment = sentiment_score * 0.2
                change += sentiment_adjustment
                
                # Adjust by impact level
                impact_multipliers = {
                    ImpactLevel.CRITICAL: 2.0,
                    ImpactLevel.HIGH: 1.5,
                    ImpactLevel.MODERATE: 1.0,
                    ImpactLevel.LOW: 0.5,
                    ImpactLevel.MINIMAL: 0.2
                }
                
                multiplier = impact_multipliers.get(impact_level, 1.0)
                change *= multiplier
                
                # Clamp to reasonable range
                change = max(-0.8, min(0.6, change))
                
                if abs(change) > 0.05:  # Only include significant changes
                    confidence_changes[player] = change
            
            return confidence_changes
            
        except Exception as e:
            self.logger.error(f"Error calculating confidence changes: {e}")
            return {}
    
    def _calculate_nlp_confidence(self, category_confidence: float, sentiment_confidence: float,
                                entity_count: int, player_count: int) -> float:
        """Calculate overall NLP processing confidence"""
        try:
            # Weight different factors
            confidence_score = (
                category_confidence * 0.3 +
                sentiment_confidence * 0.3 +
                min(1.0, entity_count / 5.0) * 0.2 +
                min(1.0, player_count / 3.0) * 0.2
            )
            
            return max(0.1, min(0.95, confidence_score))
            
        except Exception as e:
            self.logger.error(f"Error calculating NLP confidence: {e}")
            return 0.5
    
    def _create_fallback_analysis(self, headline: str, content: str, 
                                article_id: str, publish_date: datetime) -> NewsAnalysisResult:
        """Create fallback analysis when processing fails"""
        return NewsAnalysisResult(
            article_id=article_id or f"fallback_{datetime.now().timestamp()}",
            headline=headline,
            content=content,
            publish_date=publish_date or datetime.now(),
            category=NewsCategory.GENERAL,
            category_confidence=0.3,
            sentiment_polarity=SentimentPolarity.NEUTRAL,
            sentiment_score=0.0,
            sentiment_confidence=0.3,
            players_mentioned=[],
            teams_mentioned=[],
            coaches_mentioned=[],
            entities=[],
            fantasy_impact_level=ImpactLevel.MINIMAL,
            impact_reasoning="Fallback analysis",
            affected_positions=[],
            key_phrases=[],
            action_items=[],
            confidence_changes={},
            processing_timestamp=datetime.now(),
            nlp_confidence=0.3
        )

if __name__ == "__main__":
    print("🧠 ENHANCED NLP PROCESSOR TEST")
    print("=" * 40)
    
    processor = EnhancedNLPProcessor()
    
    # Test with sample news articles
    test_articles = [
        {
            'headline': "Cooper Kupp Questionable for Sunday with Ankle Injury",
            'content': "Los Angeles Rams wide receiver Cooper Kupp is listed as questionable for Sunday's game against the Cardinals after suffering an ankle sprain in practice. The star receiver was limited in practice this week and will be a game-time decision."
        },
        {
            'headline': "Josh Allen Throws for 300 Yards in Dominant Performance",
            'content': "Buffalo Bills quarterback Josh Allen had an outstanding performance, throwing for 315 yards and 3 touchdowns while adding 45 rushing yards. Allen looked sharp all game and connected well with his receivers."
        },
        {
            'headline': "Christian McCaffrey Traded to 49ers",
            'content': "The Carolina Panthers have traded star running back Christian McCaffrey to the San Francisco 49ers for multiple draft picks. McCaffrey will join a more explosive offense and could see increased opportunities."
        }
    ]
    
    for i, article in enumerate(test_articles):
        print(f"\n📰 Analyzing Article {i + 1}")
        print("-" * 30)
        print(f"Headline: {article['headline']}")
        
        analysis = processor.analyze_news_article(
            article['headline'], 
            article['content']
        )
        
        print(f"Category: {analysis.category.value} ({analysis.category_confidence:.1%})")
        print(f"Sentiment: {analysis.sentiment_polarity.value} ({analysis.sentiment_score:+.2f})")
        print(f"Impact: {analysis.fantasy_impact_level.value}")
        print(f"Players: {', '.join(analysis.players_mentioned) if analysis.players_mentioned else 'None'}")
        print(f"Teams: {', '.join(analysis.teams_mentioned) if analysis.teams_mentioned else 'None'}")
        
        if analysis.action_items:
            print(f"Actions: {'; '.join(analysis.action_items)}")
        
        if analysis.confidence_changes:
            print(f"Confidence Changes: {analysis.confidence_changes}")
        
        print(f"NLP Confidence: {analysis.nlp_confidence:.1%}")
    
    print("\n✅ Enhanced NLP Processor test completed!")