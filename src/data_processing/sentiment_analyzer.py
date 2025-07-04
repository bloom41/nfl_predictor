import re
import json
import logging
from textblob import TextBlob
# from transformers import pipeline  # Commented out for now
from src.database.database import db
from src.database.models import NewsArticle, Player

class SentimentAnalyzer:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Initialize sentiment analysis pipeline (using a pre-trained model)
        # For now, we'll use TextBlob only to avoid heavy dependencies
        self.sentiment_pipeline = None
        self.logger.info("Using TextBlob for sentiment analysis")
            
    def analyze_sentiment(self, text):
        """Analyze sentiment of text"""
        if not text:
            return 0
            
        try:
            if self.sentiment_pipeline:
                # Use transformer model
                results = self.sentiment_pipeline(text[:512])  # Limit text length
                
                # Convert to simple positive/negative score
                scores = {item['label']: item['score'] for item in results[0]}
                
                if 'LABEL_2' in scores:  # Positive
                    positive_score = scores['LABEL_2']
                elif 'POSITIVE' in scores:
                    positive_score = scores['POSITIVE']
                else:
                    positive_score = 0
                    
                if 'LABEL_0' in scores:  # Negative
                    negative_score = scores['LABEL_0']
                elif 'NEGATIVE' in scores:
                    negative_score = scores['NEGATIVE']
                else:
                    negative_score = 0
                    
                # Return score from -1 (negative) to 1 (positive)
                return positive_score - negative_score
            else:
                # Fallback to TextBlob
                blob = TextBlob(text)
                return blob.sentiment.polarity
                
        except Exception as e:
            self.logger.error(f"Error analyzing sentiment: {e}")
            return 0
            
    def extract_player_mentions(self, text):
        """Extract player names mentioned in text"""
        session = db.get_session()
        
        try:
            # Get all players from database
            players = session.query(Player).all()
            player_mentions = []
            
            text_lower = text.lower()
            
            for player in players:
                # Check for full name
                if player.name.lower() in text_lower:
                    player_mentions.append(player.name)
                    continue
                    
                # Check for last name (if it's unique enough)
                name_parts = player.name.split()
                if len(name_parts) >= 2:
                    last_name = name_parts[-1]
                    if len(last_name) > 3 and last_name.lower() in text_lower:
                        # Additional check to avoid false positives
                        if self._is_likely_player_reference(text, last_name, player.team):
                            player_mentions.append(player.name)
                            
            return list(set(player_mentions))  # Remove duplicates
            
        except Exception as e:
            self.logger.error(f"Error extracting player mentions: {e}")
            return []
        finally:
            db.close_session(session)
            
    def extract_team_mentions(self, text):
        """Extract team names mentioned in text"""
        nfl_teams = [
            'Cardinals', 'Falcons', 'Ravens', 'Bills', 'Panthers', 'Bears',
            'Bengals', 'Browns', 'Cowboys', 'Broncos', 'Lions', 'Packers',
            'Texans', 'Colts', 'Jaguars', 'Chiefs', 'Raiders', 'Chargers',
            'Rams', 'Dolphins', 'Vikings', 'Patriots', 'Saints', 'Giants',
            'Jets', 'Eagles', 'Steelers', '49ers', 'Seahawks', 'Buccaneers',
            'Titans', 'Commanders'
        ]
        
        team_mentions = []
        text_lower = text.lower()
        
        for team in nfl_teams:
            if team.lower() in text_lower:
                team_mentions.append(team)
                
        return list(set(team_mentions))
        
    def process_news_articles(self, limit=None):
        """Process all unanalyzed news articles"""
        session = db.get_session()
        
        try:
            # Get articles without sentiment analysis
            query = session.query(NewsArticle).filter(
                NewsArticle.sentiment_score.is_(None)
            )
            
            if limit:
                query = query.limit(limit)
                
            articles = query.all()
            
            self.logger.info(f"Processing {len(articles)} articles for sentiment analysis")
            
            for article in articles:
                try:
                    # Analyze sentiment
                    full_text = f"{article.title} {article.content or ''}"
                    sentiment_score = self.analyze_sentiment(full_text)
                    
                    # Extract player mentions
                    player_mentions = self.extract_player_mentions(full_text)
                    
                    # Extract team mentions
                    team_mentions = self.extract_team_mentions(full_text)
                    
                    # Update article
                    article.sentiment_score = sentiment_score
                    article.players_mentioned = json.dumps(player_mentions)
                    article.teams_mentioned = json.dumps(team_mentions)
                    
                except Exception as e:
                    self.logger.error(f"Error processing article {article.id}: {e}")
                    continue
                    
            session.commit()
            self.logger.info(f"Completed sentiment analysis for {len(articles)} articles")
            
        except Exception as e:
            session.rollback()
            self.logger.error(f"Error processing news articles: {e}")
        finally:
            db.close_session(session)
            
    def _is_likely_player_reference(self, text, last_name, team):
        """Check if a last name mention is likely referring to the player"""
        # Look for contextual clues around the name
        text_lower = text.lower()
        last_name_lower = last_name.lower()
        
        # Find position of the name
        name_pos = text_lower.find(last_name_lower)
        if name_pos == -1:
            return False
            
        # Get context around the name (50 characters before and after)
        start = max(0, name_pos - 50)
        end = min(len(text), name_pos + len(last_name) + 50)
        context = text_lower[start:end]
        
        # Look for football-related keywords
        football_keywords = [
            'touchdown', 'yards', 'pass', 'run', 'catch', 'quarterback', 'qb',
            'running back', 'rb', 'wide receiver', 'wr', 'tight end', 'te',
            'fantasy', 'points', 'game', 'week', 'season', 'nfl', 'football',
            team.lower()
        ]
        
        return any(keyword in context for keyword in football_keywords)