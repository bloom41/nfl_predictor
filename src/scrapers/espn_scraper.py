import json
import re
from datetime import datetime
from .base_scraper import BaseScraper

class ESPNScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.base_url = "https://www.espn.com/nfl"
        self.api_base = "https://site.api.espn.com/apis/site/v2/sports/football/nfl"
        
    def scrape_player_stats(self, season, week=None):
        """Scrape player statistics from ESPN"""
        stats_data = []
        
        # Construct URL for player stats
        if week:
            stats_url = f"{self.base_url}/stats/player/_/season/{season}/seasontype/2/week/{week}"
        else:
            stats_url = f"{self.base_url}/stats/player/_/season/{season}/seasontype/2"
            
        # Scrape passing stats
        passing_stats = self._scrape_passing_stats(stats_url)
        stats_data.extend(passing_stats)
        
        # Scrape rushing stats
        rushing_stats = self._scrape_rushing_stats(stats_url)
        stats_data.extend(rushing_stats)
        
        # Scrape receiving stats
        receiving_stats = self._scrape_receiving_stats(stats_url)
        stats_data.extend(receiving_stats)
        
        return stats_data
        
    def _scrape_passing_stats(self, base_url):
        """Scrape quarterback passing statistics"""
        url = f"{base_url}/stat/passing"
        response = self.get_page(url)
        
        if not response:
            return []
            
        soup = self.parse_html(response.content)
        stats = []
        
        # Look for stats table
        table = soup.find('table', class_='Table')
        if not table:
            return stats
            
        rows = table.find('tbody').find_all('tr') if table.find('tbody') else []
        
        for row in rows:
            try:
                cells = row.find_all('td')
                if len(cells) >= 10:  # Ensure we have enough columns
                    player_name = cells[0].get_text(strip=True)
                    team = cells[1].get_text(strip=True) if len(cells) > 1 else ''
                    
                    stat_data = {
                        'player_name': player_name,
                        'team': team,
                        'position': 'QB',
                        'passing_completions': self._safe_int(cells[2].get_text(strip=True)),
                        'passing_attempts': self._safe_int(cells[3].get_text(strip=True)),
                        'passing_yards': self._safe_int(cells[5].get_text(strip=True)),
                        'passing_tds': self._safe_int(cells[7].get_text(strip=True)),
                        'interceptions': self._safe_int(cells[8].get_text(strip=True)),
                    }
                    stats.append(stat_data)
            except Exception as e:
                self.logger.error(f"Error parsing passing stats row: {e}")
                continue
                
        return stats
        
    def _scrape_rushing_stats(self, base_url):
        """Scrape running back rushing statistics"""
        url = f"{base_url}/stat/rushing"
        response = self.get_page(url)
        
        if not response:
            return []
            
        soup = self.parse_html(response.content)
        stats = []
        
        table = soup.find('table', class_='Table')
        if not table:
            return stats
            
        rows = table.find('tbody').find_all('tr') if table.find('tbody') else []
        
        for row in rows:
            try:
                cells = row.find_all('td')
                if len(cells) >= 6:
                    player_name = cells[0].get_text(strip=True)
                    team = cells[1].get_text(strip=True) if len(cells) > 1 else ''
                    
                    stat_data = {
                        'player_name': player_name,
                        'team': team,
                        'position': 'RB',
                        'rushing_attempts': self._safe_int(cells[2].get_text(strip=True)),
                        'rushing_yards': self._safe_int(cells[3].get_text(strip=True)),
                        'rushing_tds': self._safe_int(cells[5].get_text(strip=True)),
                    }
                    stats.append(stat_data)
            except Exception as e:
                self.logger.error(f"Error parsing rushing stats row: {e}")
                continue
                
        return stats
        
    def _scrape_receiving_stats(self, base_url):
        """Scrape wide receiver and tight end receiving statistics"""
        url = f"{base_url}/stat/receiving"
        response = self.get_page(url)
        
        if not response:
            return []
            
        soup = self.parse_html(response.content)
        stats = []
        
        table = soup.find('table', class_='Table')
        if not table:
            return stats
            
        rows = table.find('tbody').find_all('tr') if table.find('tbody') else []
        
        for row in rows:
            try:
                cells = row.find_all('td')
                if len(cells) >= 6:
                    player_name = cells[0].get_text(strip=True)
                    team = cells[1].get_text(strip=True) if len(cells) > 1 else ''
                    
                    # Determine position (WR/TE) - would need additional logic
                    position = 'WR'  # Default, could be enhanced
                    
                    stat_data = {
                        'player_name': player_name,
                        'team': team,
                        'position': position,
                        'receptions': self._safe_int(cells[2].get_text(strip=True)),
                        'targets': self._safe_int(cells[3].get_text(strip=True)) if len(cells) > 3 else 0,
                        'receiving_yards': self._safe_int(cells[4].get_text(strip=True)),
                        'receiving_tds': self._safe_int(cells[6].get_text(strip=True)),
                    }
                    stats.append(stat_data)
            except Exception as e:
                self.logger.error(f"Error parsing receiving stats row: {e}")
                continue
                
        return stats
        
    def scrape_news(self, limit=50):
        """Scrape NFL news from ESPN"""
        # Use ESPN API for news
        news_url = f"{self.api_base}/news?limit={limit}"
        response = self.get_page(news_url)
        
        if not response:
            return []
            
        try:
            # Parse JSON response
            data = response.json()
            articles = []
            
            # Extract articles from API response
            if 'articles' in data:
                for article in data['articles'][:limit]:
                    try:
                        # Get publication date
                        pub_date = None
                        if 'published' in article:
                            try:
                                pub_date = datetime.fromisoformat(article['published'].replace('Z', '+00:00'))
                            except:
                                pass
                        
                        article_data = {
                            'title': article.get('headline', ''),
                            'url': article.get('links', {}).get('web', {}).get('href', ''),
                            'source': 'ESPN',
                            'published_date': pub_date,
                            'content': article.get('description', '')
                        }
                        
                        if article_data['title']:  # Only add if we have a title
                            articles.append(article_data)
                        
                    except Exception as e:
                        self.logger.error(f"Error parsing news article: {e}")
                        continue
            
            return articles
            
        except Exception as e:
            self.logger.error(f"Error parsing JSON response: {e}")
            return []
        
    def _safe_int(self, value):
        """Safely convert string to integer"""
        try:
            return int(value.replace(',', ''))
        except (ValueError, AttributeError):
            return 0