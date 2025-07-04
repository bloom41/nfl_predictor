import json
import logging
from datetime import datetime
from textblob import TextBlob
from .base_scraper import BaseScraper
from src.database.database import db
from src.database.models import TeamNews, Player

class TeamNewsScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.api_base = "https://site.api.espn.com/apis/site/v2/sports/football/nfl"
        
        # NFL team mapping
        self.nfl_teams = {
            'arizona-cardinals': 'ARI', 'atlanta-falcons': 'ATL', 'baltimore-ravens': 'BAL',
            'buffalo-bills': 'BUF', 'carolina-panthers': 'CAR', 'chicago-bears': 'CHI',
            'cincinnati-bengals': 'CIN', 'cleveland-browns': 'CLE', 'dallas-cowboys': 'DAL',
            'denver-broncos': 'DEN', 'detroit-lions': 'DET', 'green-bay-packers': 'GB',
            'houston-texans': 'HOU', 'indianapolis-colts': 'IND', 'jacksonville-jaguars': 'JAX',
            'kansas-city-chiefs': 'KC', 'las-vegas-raiders': 'LV', 'los-angeles-chargers': 'LAC',
            'los-angeles-rams': 'LAR', 'miami-dolphins': 'MIA', 'minnesota-vikings': 'MIN',
            'new-england-patriots': 'NE', 'new-orleans-saints': 'NO', 'new-york-giants': 'NYG',
            'new-york-jets': 'NYJ', 'philadelphia-eagles': 'PHI', 'pittsburgh-steelers': 'PIT',
            'san-francisco-49ers': 'SF', 'seattle-seahawks': 'SEA', 'tampa-bay-buccaneers': 'TB',
            'tennessee-titans': 'TEN', 'washington-commanders': 'WSH'
        }
        
        # News category keywords
        self.category_keywords = {
            'injury_report': ['injury', 'injured', 'hurt', 'questionable', 'doubtful', 'ir', 'injured reserve'],
            'coaching': ['coach', 'coordinator', 'fired', 'hired', 'promoted', 'strategy'],
            'roster': ['signed', 'released', 'traded', 'waived', 'activated', 'practice squad'],
            'strategy': ['game plan', 'offense', 'defense', 'scheme', 'formation', 'playcalling']
        }
        
    def scrape_team_news(self, team_abbr, limit=20):
        """Scrape team-specific news"""
        team_news = []
        
        try:
            # Get team news from ESPN API
            team_url = f"{self.api_base}/teams/{self._get_team_id(team_abbr)}/news"
            response = self.get_page(team_url)
            
            if response and response.status_code == 200:
                data = response.json()
                
                if 'articles' in data:
                    for article in data['articles'][:limit]:
                        news_item = self._process_team_article(article, team_abbr)
                        if news_item:
                            team_news.append(news_item)
                            
        except Exception as e:
            self.logger.error(f"Error scraping team news for {team_abbr}: {e}")
            
        return team_news
        
    def scrape_all_team_news(self, limit_per_team=10):
        """Scrape news for all NFL teams"""
        all_team_news = []
        
        for team_name, team_abbr in self.nfl_teams.items():
            try:
                self.logger.info(f"Scraping news for {team_abbr}")
                team_news = self.scrape_team_news(team_abbr, limit_per_team)
                all_team_news.extend(team_news)
                
                # Rate limiting
                import time
                time.sleep(1)
                
            except Exception as e:
                self.logger.error(f"Error scraping news for {team_abbr}: {e}")
                continue
                
        return all_team_news
        
    def _process_team_article(self, article, team_abbr):
        """Process individual team news article"""
        try:
            # Extract basic info
            title = article.get('headline', '')
            content = article.get('description', '')
            url = article.get('links', {}).get('web', {}).get('href', '')
            
            # Parse publication date
            pub_date = None
            if 'published' in article:
                try:
                    pub_date = datetime.fromisoformat(article['published'].replace('Z', '+00:00'))
                except:
                    pass
                    
            # Analyze content
            full_text = f"{title} {content}".lower()
            
            # Categorize news
            category = self._categorize_news(full_text)
            impact_level = self._assess_impact_level(full_text, category)
            
            # Extract affected players and positions
            affected_players = self._extract_affected_players(full_text)
            affected_positions = self._extract_affected_positions(full_text)
            
            # Sentiment analysis
            sentiment_score = self._analyze_team_sentiment(title + " " + content)
            
            return {
                'team': team_abbr,
                'title': title,
                'content': content,
                'source': 'ESPN',
                'url': url,
                'published_date': pub_date,
                'category': category,
                'impact_level': impact_level,
                'affected_players': json.dumps(affected_players),
                'affected_positions': json.dumps(affected_positions),
                'sentiment_score': sentiment_score
            }
            
        except Exception as e:
            self.logger.error(f"Error processing team article: {e}")
            return None
            
    def _categorize_news(self, text):
        """Categorize team news by type"""
        category_scores = {}
        
        for category, keywords in self.category_keywords.items():
            score = sum(1 for keyword in keywords if keyword in text)
            if score > 0:
                category_scores[category] = score
                
        if category_scores:
            return max(category_scores, key=category_scores.get)
        return 'general'
        
    def _assess_impact_level(self, text, category):
        """Assess the impact level of team news"""
        high_impact_words = ['star', 'starter', 'key', 'major', 'significant', 'season-ending', 'surgery']
        medium_impact_words = ['backup', 'rotation', 'depth', 'minor', 'week-to-week']
        low_impact_words = ['practice squad', 'reserve', 'rookie', 'training camp']
        
        high_count = sum(1 for word in high_impact_words if word in text)
        medium_count = sum(1 for word in medium_impact_words if word in text)
        low_count = sum(1 for word in low_impact_words if word in text)
        
        if high_count > 0 or category == 'injury_report':
            return 'high'
        elif medium_count > 0:
            return 'medium'
        else:
            return 'low'
            
    def _extract_affected_players(self, text):
        """Extract player names mentioned in the news"""
        # This is a simplified version - would need a more sophisticated NER approach
        session = db.get_session()
        
        try:
            players = session.query(Player).all()
            mentioned_players = []
            
            for player in players:
                # Check for full name or last name
                if player.name.lower() in text:
                    mentioned_players.append(player.name)
                else:
                    name_parts = player.name.split()
                    if len(name_parts) >= 2:
                        last_name = name_parts[-1].lower()
                        if len(last_name) > 3 and last_name in text:
                            mentioned_players.append(player.name)
                            
            return list(set(mentioned_players))  # Remove duplicates
            
        except Exception as e:
            self.logger.error(f"Error extracting affected players: {e}")
            return []
        finally:
            db.close_session(session)
            
    def _extract_affected_positions(self, text):
        """Extract positions mentioned in the news"""
        positions = ['quarterback', 'qb', 'running back', 'rb', 'wide receiver', 'wr', 
                    'tight end', 'te', 'offensive line', 'ol', 'center', 'guard', 'tackle']
        
        mentioned_positions = []
        for position in positions:
            if position in text:
                # Normalize to standard abbreviations
                if position in ['quarterback', 'qb']:
                    mentioned_positions.append('QB')
                elif position in ['running back', 'rb']:
                    mentioned_positions.append('RB')
                elif position in ['wide receiver', 'wr']:
                    mentioned_positions.append('WR')
                elif position in ['tight end', 'te']:
                    mentioned_positions.append('TE')
                elif position in ['offensive line', 'ol', 'center', 'guard', 'tackle']:
                    mentioned_positions.append('OL')
                    
        return list(set(mentioned_positions))
    
    def scrape_player_stats(self, season, week=None):
        """Required abstract method - not implemented for team news scraper"""
        self.logger.warning("scrape_player_stats called on TeamNewsScraper - not implemented")
        return []
        
    def scrape_news(self, limit=50):
        """Required abstract method - delegates to scrape_all_team_news"""
        return self.scrape_all_team_news(limit_per_team=max(1, limit // 32))
        
    def _analyze_team_sentiment(self, text):
        """Analyze sentiment specific to team context"""
        try:
            blob = TextBlob(text)
            base_sentiment = blob.sentiment.polarity
            
            # Adjust for team-specific context
            positive_team_words = ['win', 'victory', 'strong', 'improved', 'healthy', 'return', 'signed']
            negative_team_words = ['lose', 'injury', 'injured', 'out', 'suspended', 'released', 'struggle']
            
            text_lower = text.lower()
            positive_boost = sum(0.1 for word in positive_team_words if word in text_lower)
            negative_boost = sum(-0.1 for word in negative_team_words if word in text_lower)
            
            adjusted_sentiment = base_sentiment + positive_boost + negative_boost
            return max(-1.0, min(1.0, adjusted_sentiment))  # Clamp to [-1, 1]
            
        except Exception as e:
            self.logger.error(f"Error analyzing team sentiment: {e}")
            return 0.0
            
    def _get_team_id(self, team_abbr):
        """Get ESPN team ID from abbreviation"""
        # This would need to be mapped to actual ESPN team IDs
        # For now, return a placeholder
        team_id_map = {
            'ARI': '22', 'ATL': '1', 'BAL': '33', 'BUF': '2', 'CAR': '29', 'CHI': '3',
            'CIN': '4', 'CLE': '5', 'DAL': '6', 'DEN': '7', 'DET': '8', 'GB': '9',
            'HOU': '34', 'IND': '11', 'JAX': '30', 'KC': '12', 'LV': '13', 'LAC': '24',
            'LAR': '14', 'MIA': '15', 'MIN': '16', 'NE': '17', 'NO': '18', 'NYG': '19',
            'NYJ': '20', 'PHI': '21', 'PIT': '23', 'SF': '25', 'SEA': '26', 'TB': '27',
            'TEN': '10', 'WSH': '28'
        }
        return team_id_map.get(team_abbr, '1')
        
    def store_team_news(self, team_news_data):
        """Store team news in database"""
        session = db.get_session()
        
        try:
            for news_item in team_news_data:
                # Check if news already exists
                existing_news = session.query(TeamNews).filter_by(
                    url=news_item['url']
                ).first()
                
                if not existing_news and news_item['url']:
                    team_news = TeamNews(**news_item)
                    session.add(team_news)
                    
            session.commit()
            self.logger.info(f"Stored {len(team_news_data)} team news articles")
            
        except Exception as e:
            session.rollback()
            self.logger.error(f"Error storing team news: {e}")
        finally:
            db.close_session(session)