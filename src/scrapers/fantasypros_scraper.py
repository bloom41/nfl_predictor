import requests
import pandas as pd
import logging
import time
from bs4 import BeautifulSoup
from datetime import datetime
from src.database.database import db
from src.database.models import Player, PlayerStats

class FantasyProsScraper:
    """
    Scrape FantasyPros for expert consensus rankings and rookie analysis
    Focus on offensive players only (QB, RB, WR, TE)
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.base_url = "https://www.fantasypros.com"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # Position mappings
        self.position_urls = {
            'QB': '/nfl/rankings/qb.php',
            'RB': '/nfl/rankings/rb.php', 
            'WR': '/nfl/rankings/wr.php',
            'TE': '/nfl/rankings/te.php'
        }
        
    def scrape_consensus_rankings(self, position, week=None):
        """Scrape expert consensus rankings for a position"""
        try:
            if position not in self.position_urls:
                self.logger.error(f"Invalid position: {position}")
                return []
                
            url = f"{self.base_url}{self.position_urls[position]}"
            if week:
                url += f"?week={week}"
                
            self.logger.info(f"Scraping {position} rankings from {url}")
            
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Parse rankings table
            rankings = self._parse_rankings_table(soup, position)
            
            self.logger.info(f"Successfully scraped {len(rankings)} {position} players")
            return rankings
            
        except Exception as e:
            self.logger.error(f"Error scraping {position} rankings: {e}")
            return []
            
    def _parse_rankings_table(self, soup, position):
        """Parse the rankings table from FantasyPros"""
        players = []
        
        try:
            # Look for the main rankings table
            table = soup.find('table', {'id': 'data'}) or soup.find('table', class_='table')
            
            if not table:
                # Try alternative selectors
                tables = soup.find_all('table')
                table = tables[0] if tables else None
                
            if not table:
                self.logger.warning("Could not find rankings table")
                return []
                
            rows = table.find_all('tr')[1:]  # Skip header
            
            for rank, row in enumerate(rows[:30], 1):  # Top 30 per position
                cells = row.find_all(['td', 'th'])
                
                if len(cells) >= 2:
                    # Extract player name and team
                    player_cell = cells[1]  # Usually second column
                    player_text = player_cell.get_text(strip=True)
                    
                    # Parse player info
                    player_info = self._parse_player_info(player_text, position, rank)
                    
                    if player_info:
                        players.append(player_info)
                        
            return players
            
        except Exception as e:
            self.logger.error(f"Error parsing rankings table: {e}")
            return []
            
    def _parse_player_info(self, text, position, rank):
        """Parse player name and team from FantasyPros text"""
        try:
            import re
            
            # Clean up text
            text = text.replace('\\n', ' ').replace('\\t', ' ')
            text = ' '.join(text.split())
            
            # Common FantasyPros formats:
            # "Josh Allen QB - BUF"
            # "Christian McCaffrey RB - SF" 
            # "Allen, Josh BUF"
            
            # Pattern 1: "First Last POS - TEAM"
            pattern1 = r'^([A-Za-z\'\.\-\s]+)\s+(?:QB|RB|WR|TE)\s*[-–]\s*([A-Z]{2,4})'
            match1 = re.search(pattern1, text, re.IGNORECASE)
            
            if match1:
                name = match1.group(1).strip()
                team = match1.group(2).strip().upper()
                
                return {
                    'name': name,
                    'team': team,
                    'position': position,
                    'expert_rank': rank,
                    'source': 'fantasypros'
                }
                
            # Pattern 2: "First Last - TEAM"
            pattern2 = r'^([A-Za-z\'\.\-\s]+)\s*[-–]\s*([A-Z]{2,4})'
            match2 = re.search(pattern2, text)
            
            if match2:
                name = match2.group(1).strip()
                team = match2.group(2).strip().upper()
                
                return {
                    'name': name,
                    'team': team, 
                    'position': position,
                    'expert_rank': rank,
                    'source': 'fantasypros'
                }
                
            # Pattern 3: "Last, First TEAM"
            pattern3 = r'^([A-Za-z\'\.\-]+),\s*([A-Za-z\'\.\-\s]+)\s+([A-Z]{2,4})'
            match3 = re.search(pattern3, text)
            
            if match3:
                last = match3.group(1).strip()
                first = match3.group(2).strip()
                team = match3.group(3).strip().upper()
                name = f"{first} {last}"
                
                return {
                    'name': name,
                    'team': team,
                    'position': position,
                    'expert_rank': rank,
                    'source': 'fantasypros'
                }
                
            return None
            
        except Exception as e:
            self.logger.error(f"Error parsing player info '{text}': {e}")
            return None
            
    def scrape_rookie_analysis(self):
        """Scrape rookie analysis and projections"""
        try:
            rookie_url = f"{self.base_url}/nfl/draft/rankings.php"
            
            self.logger.info(f"Scraping rookie analysis from {rookie_url}")
            
            response = self.session.get(rookie_url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            rookies = self._parse_rookie_data(soup)
            
            self.logger.info(f"Successfully scraped {len(rookies)} rookie projections")
            return rookies
            
        except Exception as e:
            self.logger.error(f"Error scraping rookie analysis: {e}")
            return []
            
    def _parse_rookie_data(self, soup):
        """Parse rookie draft rankings and analysis"""
        rookies = []
        
        try:
            # Look for draft rankings table
            tables = soup.find_all('table')
            
            for table in tables:
                rows = table.find_all('tr')[1:]  # Skip header
                
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    
                    if len(cells) >= 3:
                        # Try to extract rookie info
                        name_cell = cells[1] if len(cells) > 1 else cells[0]
                        name_text = name_cell.get_text(strip=True)
                        
                        # Look for position indicators
                        full_text = ' '.join([cell.get_text(strip=True) for cell in cells])
                        
                        for position in ['QB', 'RB', 'WR', 'TE']:
                            if position in full_text.upper():
                                rookie_info = self._parse_player_info(name_text, position, len(rookies) + 1)
                                
                                if rookie_info:
                                    rookie_info['is_rookie'] = True
                                    rookie_info['draft_analysis'] = full_text[:200]  # First 200 chars
                                    rookies.append(rookie_info)
                                    break
                                    
        except Exception as e:
            self.logger.error(f"Error parsing rookie data: {e}")
            
        return rookies[:20]  # Top 20 rookies
        
    def get_expert_projections(self, position):
        """Get expert projections for statistical analysis"""
        try:
            # FantasyPros projections URL
            proj_url = f"{self.base_url}/nfl/projections/{position.lower()}.php"
            
            response = self.session.get(proj_url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            projections = self._parse_projections_table(soup, position)
            
            return projections
            
        except Exception as e:
            self.logger.error(f"Error getting {position} projections: {e}")
            return []
            
    def _parse_projections_table(self, soup, position):
        """Parse statistical projections table"""
        projections = []
        
        try:
            # Find projections table
            table = soup.find('table', {'id': 'data'}) or soup.find('table')
            
            if not table:
                return []
                
            headers = [th.get_text(strip=True) for th in table.find('tr').find_all(['th', 'td'])]
            rows = table.find_all('tr')[1:]
            
            for row in rows[:20]:  # Top 20
                cells = row.find_all(['td', 'th'])
                
                if len(cells) >= len(headers):
                    row_data = {}
                    
                    for i, cell in enumerate(cells):
                        if i < len(headers):
                            header = headers[i].lower()
                            value = cell.get_text(strip=True)
                            
                            # Map common stat headers
                            if 'pass' in header and 'yd' in header:
                                row_data['projected_passing_yards'] = self._safe_int(value)
                            elif 'pass' in header and 'td' in header:
                                row_data['projected_passing_tds'] = self._safe_int(value)
                            elif 'rush' in header and 'yd' in header:
                                row_data['projected_rushing_yards'] = self._safe_int(value)
                            elif 'rush' in header and 'td' in header:
                                row_data['projected_rushing_tds'] = self._safe_int(value)
                            elif 'rec' in header and 'yd' in header:
                                row_data['projected_receiving_yards'] = self._safe_int(value)
                            elif 'rec' in header and 'td' in header:
                                row_data['projected_receiving_tds'] = self._safe_int(value)
                            elif 'fpts' in header or 'fantasy' in header:
                                row_data['projected_fantasy_points'] = self._safe_float(value)
                                
                    if row_data and len(cells) > 0:
                        # Get player name from first cell
                        player_text = cells[0].get_text(strip=True)
                        player_info = self._parse_player_info(player_text, position, len(projections) + 1)
                        
                        if player_info:
                            player_info.update(row_data)
                            projections.append(player_info)
                            
        except Exception as e:
            self.logger.error(f"Error parsing projections: {e}")
            
        return projections
        
    def _safe_int(self, value):
        """Safely convert to int"""
        try:
            return int(float(value.replace(',', '')))
        except:
            return 0
            
    def _safe_float(self, value):
        """Safely convert to float"""
        try:
            return float(value.replace(',', ''))
        except:
            return 0.0
            
    def update_database_with_expert_data(self, expert_data):
        """Update database with expert rankings and projections"""
        session = db.get_session()
        
        try:
            updates_made = 0
            
            for data in expert_data:
                # Find matching player
                player = session.query(Player).filter_by(
                    name=data['name']
                ).first()
                
                if player:
                    # Update team if different (handles trades)
                    if player.team != data['team']:
                        self.logger.info(f"Updating {player.name}: {player.team} → {data['team']}")
                        player.team = data['team']
                        updates_made += 1
                        
                else:
                    # Add new player discovered by experts
                    new_player = Player(
                        name=data['name'],
                        position=data['position'],
                        team=data['team'],
                        age=data.get('age', 25),
                        experience_years=1 if data.get('is_rookie') else 3
                    )
                    
                    session.add(new_player)
                    updates_made += 1
                    self.logger.info(f"Added new player from experts: {data['name']} ({data['team']})")
                    
            session.commit()
            
            self.logger.info(f"Database updated with {updates_made} expert-based changes")
            return updates_made
            
        except Exception as e:
            self.logger.error(f"Error updating database: {e}")
            session.rollback()
            return 0
        finally:
            db.close_session(session)
            
    def scrape_all_offensive_positions(self):
        """Scrape all offensive positions from FantasyPros"""
        all_data = []
        
        for position in ['QB', 'RB', 'WR', 'TE']:
            self.logger.info(f"Scraping {position} data...")
            
            # Get rankings
            rankings = self.scrape_consensus_rankings(position)
            all_data.extend(rankings)
            
            # Get projections
            projections = self.get_expert_projections(position)
            
            # Merge projections with rankings
            for proj in projections:
                # Find matching ranking
                for rank in all_data:
                    if rank['name'] == proj['name'] and rank['position'] == proj['position']:
                        rank.update(proj)
                        break
                        
            # Be respectful with requests
            time.sleep(2)
            
        # Get rookie data
        self.logger.info("Scraping rookie analysis...")
        rookies = self.scrape_rookie_analysis()
        all_data.extend(rookies)
        
        return all_data