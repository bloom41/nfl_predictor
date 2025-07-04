import requests
import pandas as pd
import logging
import time
from bs4 import BeautifulSoup
from datetime import datetime
from src.database.database import db
from src.database.models import Player, PlayerStats

class BorisChenScraper:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.base_url = "https://www.borischen.co"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
    def scrape_weekly_rankings(self, week=None):
        """Scrape current weekly rankings from Boris Chen"""
        try:
            # Boris Chen has separate pages for each position
            positions = {
                'qb': 'QB',
                'rb': 'RB', 
                'wr': 'WR',
                'te': 'TE',
                'k': 'K',
                'dst': 'DST'
            }
            
            all_players = []
            
            for pos_code, position in positions.items():
                if position in ['K', 'DST']:  # Skip kickers and defenses for now
                    continue
                    
                self.logger.info(f"Scraping {position} rankings...")
                
                # Boris Chen URL structure
                url = f"{self.base_url}/{pos_code}"
                
                try:
                    response = self.session.get(url, timeout=10)
                    response.raise_for_status()
                    
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Parse player data from the rankings table
                    players = self._parse_position_rankings(soup, position)
                    all_players.extend(players)
                    
                    # Be respectful with requests
                    time.sleep(1)
                    
                except Exception as e:
                    self.logger.error(f"Error scraping {position}: {e}")
                    continue
                    
            self.logger.info(f"Scraped {len(all_players)} total players")
            return all_players
            
        except Exception as e:
            self.logger.error(f"Error in scrape_weekly_rankings: {e}")
            return []
            
    def _parse_position_rankings(self, soup, position):
        """Parse player rankings from Boris Chen page"""
        players = []
        
        try:
            # Boris Chen uses different table structures, let's try multiple approaches
            
            # Approach 1: Look for ranking tables
            tables = soup.find_all('table')
            
            for table in tables:
                rows = table.find_all('tr')
                
                for row in rows[1:]:  # Skip header row
                    cells = row.find_all(['td', 'th'])
                    
                    if len(cells) >= 2:
                        # Try to extract player name and team
                        player_text = cells[1].get_text(strip=True) if len(cells) > 1 else cells[0].get_text(strip=True)
                        
                        # Parse player name and team (format usually "Player Name TEAM")
                        player_info = self._parse_player_name_team(player_text, position)
                        
                        if player_info:
                            players.append(player_info)
                            
            # Approach 2: Look for player names in divs or spans
            if not players:
                player_elements = soup.find_all(['div', 'span'], class_=lambda x: x and 'player' in x.lower())
                
                for element in player_elements:
                    player_text = element.get_text(strip=True)
                    player_info = self._parse_player_name_team(player_text, position)
                    
                    if player_info:
                        players.append(player_info)
                        
            # Remove duplicates
            seen = set()
            unique_players = []
            for player in players:
                key = (player['name'], player['team'])
                if key not in seen:
                    seen.add(key)
                    unique_players.append(player)
                    
            return unique_players[:50]  # Limit to top 50 per position
            
        except Exception as e:
            self.logger.error(f"Error parsing {position} rankings: {e}")
            return []
            
    def _parse_player_name_team(self, text, position):
        """Parse player name and team from text"""
        try:
            # Common formats:
            # "Christian McCaffrey SF"
            # "McCaffrey, Christian (SF)"
            # "C. McCaffrey - SF"
            
            import re
            
            # Remove extra whitespace
            text = ' '.join(text.split())
            
            # Pattern 1: "First Last TEAM"
            pattern1 = r'^([A-Za-z\'\.\-\s]+)\s+([A-Z]{2,4})$'
            match1 = re.match(pattern1, text)
            
            if match1:
                name = match1.group(1).strip()
                team = match1.group(2).strip()
                
                # Clean up name
                name = re.sub(r'\s+', ' ', name)
                
                if len(name) > 2 and len(team) <= 4:
                    return {
                        'name': name,
                        'team': team,
                        'position': position,
                        'source': 'boris_chen'
                    }
                    
            # Pattern 2: "Last, First (TEAM)"
            pattern2 = r'^([A-Za-z\'\.\-\s]+),\s*([A-Za-z\'\.\-\s]+)\s*\(([A-Z]{2,4})\)$'
            match2 = re.match(pattern2, text)
            
            if match2:
                last = match2.group(1).strip()
                first = match2.group(2).strip()
                team = match2.group(3).strip()
                name = f"{first} {last}"
                
                return {
                    'name': name,
                    'team': team,
                    'position': position,
                    'source': 'boris_chen'
                }
                
            # Pattern 3: "F. Last - TEAM"
            pattern3 = r'^([A-Za-z\'\.\-\s]+)\s*[-–]\s*([A-Z]{2,4})$'
            match3 = re.match(pattern3, text)
            
            if match3:
                name = match3.group(1).strip()
                team = match3.group(2).strip()
                
                if len(name) > 2:
                    return {
                        'name': name,
                        'team': team,
                        'position': position,
                        'source': 'boris_chen'
                    }
                    
            return None
            
        except Exception as e:
            self.logger.error(f"Error parsing player text '{text}': {e}")
            return None
            
    def get_consensus_rankings_data(self):
        """Get additional consensus data from Boris Chen API if available"""
        try:
            # Boris Chen sometimes has JSON endpoints for chart data
            api_endpoints = [
                f"{self.base_url}/api/rankings",
                f"{self.base_url}/data/rankings.json"
            ]
            
            for endpoint in api_endpoints:
                try:
                    response = self.session.get(endpoint, timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        self.logger.info(f"Found API data at {endpoint}")
                        return data
                except:
                    continue
                    
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting consensus data: {e}")
            return None
            
    def add_scraped_players_to_database(self, players_data):
        """Add scraped players to database"""
        session = db.get_session()
        
        try:
            added_count = 0
            updated_count = 0
            
            for player_data in players_data:
                # Check if player exists
                existing = session.query(Player).filter_by(
                    name=player_data['name']
                ).first()
                
                if existing:
                    # Update team if different (handles trades)
                    if existing.team != player_data['team']:
                        self.logger.info(f"Updating {existing.name}: {existing.team} → {player_data['team']}")
                        existing.team = player_data['team']
                        updated_count += 1
                else:
                    # Add new player
                    new_player = Player(
                        name=player_data['name'],
                        position=player_data['position'],
                        team=player_data['team'],
                        age=self._estimate_age(player_data['name']),
                        experience_years=self._estimate_experience(player_data['name'])
                    )
                    
                    session.add(new_player)
                    added_count += 1
                    self.logger.info(f"Added new player: {player_data['name']} ({player_data['team']})")
                    
            session.commit()
            
            self.logger.info(f"Database updated: {added_count} added, {updated_count} updated")
            return {'added': added_count, 'updated': updated_count}
            
        except Exception as e:
            self.logger.error(f"Error updating database: {e}")
            session.rollback()
            return {'added': 0, 'updated': 0}
        finally:
            db.close_session(session)
            
    def _estimate_age(self, player_name):
        """Estimate player age (would be enhanced with actual data)"""
        # Default estimates - in production this would lookup actual ages
        return 26
        
    def _estimate_experience(self, player_name):
        """Estimate player experience (would be enhanced with actual data)"""
        # Default estimates - in production this would lookup actual experience
        return 4
        
    def scrape_and_update_database(self):
        """Complete workflow: scrape data and update database"""
        try:
            self.logger.info("Starting Boris Chen scraping workflow...")
            
            # Scrape current rankings
            players = self.scrape_weekly_rankings()
            
            if not players:
                self.logger.warning("No players scraped")
                return False
                
            # Add to database
            results = self.add_scraped_players_to_database(players)
            
            self.logger.info(f"Workflow complete: {results}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error in scrape workflow: {e}")
            return False