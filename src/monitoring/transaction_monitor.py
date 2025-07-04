import requests
import logging
import time
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from src.database.database import db
from src.database.models import Player, TransactionLog

class TransactionMonitor:
    """
    Monitor NFL transactions (trades, signings, releases) from multiple sources
    Automatically update player team assignments and log all changes
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # Transaction sources
        self.sources = {
            'nfl_com': 'https://www.nfl.com/news/transactions',
            'espn': 'https://www.espn.com/nfl/transactions',
            'rotoworld': 'https://www.rotoworld.com/football/nfl/transactions'
        }
        
    def monitor_all_transactions(self):
        """Monitor transactions from all sources"""
        try:
            all_transactions = []
            
            for source, url in self.sources.items():
                self.logger.info(f"Monitoring {source} for transactions...")
                
                try:
                    transactions = self.scrape_transactions(source, url)
                    all_transactions.extend(transactions)
                    
                    # Be respectful with requests
                    time.sleep(2)
                    
                except Exception as e:
                    self.logger.error(f"Error monitoring {source}: {e}")
                    
            # Process and update database
            updates = self.process_transactions(all_transactions)
            
            self.logger.info(f"Processed {len(all_transactions)} transactions, made {updates} database updates")
            return updates
            
        except Exception as e:
            self.logger.error(f"Error monitoring transactions: {e}")
            return 0
            
    def scrape_transactions(self, source, url):
        """Scrape transactions from a specific source"""
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            if source == 'nfl_com':
                return self._parse_nfl_com_transactions(soup)
            elif source == 'espn':
                return self._parse_espn_transactions(soup)
            elif source == 'rotoworld':
                return self._parse_rotoworld_transactions(soup)
                
        except Exception as e:
            self.logger.error(f"Error scraping {source}: {e}")
            return []
            
    def _parse_nfl_com_transactions(self, soup):
        """Parse NFL.com transaction format"""
        transactions = []
        
        try:
            # Look for transaction items
            transaction_items = soup.find_all(['div', 'article'], class_=lambda x: x and 'transaction' in x.lower())
            
            for item in transaction_items[:20]:  # Last 20 transactions
                text = item.get_text(strip=True)
                
                # Extract transaction details
                transaction = self._extract_transaction_info(text, 'nfl_com')
                if transaction:
                    transactions.append(transaction)
                    
        except Exception as e:
            self.logger.error(f"Error parsing NFL.com transactions: {e}")
            
        return transactions
        
    def _parse_espn_transactions(self, soup):
        """Parse ESPN transaction format"""
        transactions = []
        
        try:
            # Look for transaction rows
            rows = soup.find_all('tr')
            
            for row in rows[:20]:
                text = row.get_text(strip=True)
                
                if any(keyword in text.lower() for keyword in ['signed', 'traded', 'released', 'waived']):
                    transaction = self._extract_transaction_info(text, 'espn')
                    if transaction:
                        transactions.append(transaction)
                        
        except Exception as e:
            self.logger.error(f"Error parsing ESPN transactions: {e}")
            
        return transactions
        
    def _parse_rotoworld_transactions(self, soup):
        """Parse Rotoworld transaction format"""
        transactions = []
        
        try:
            # Look for transaction entries
            entries = soup.find_all(['div', 'p'], class_=lambda x: x and 'news' in x.lower())
            
            for entry in entries[:20]:
                text = entry.get_text(strip=True)
                
                transaction = self._extract_transaction_info(text, 'rotoworld')
                if transaction:
                    transactions.append(transaction)
                    
        except Exception as e:
            self.logger.error(f"Error parsing Rotoworld transactions: {e}")
            
        return transactions
        
    def _extract_transaction_info(self, text, source):
        """Extract structured transaction information from text"""
        try:
            import re
            
            # Common transaction patterns
            patterns = {
                'trade': r'(\w+\s+\w+).*?traded.*?to\s+(\w+)',
                'signing': r'(\w+\s+\w+).*?sign.*?with\s+(\w+)',
                'release': r'(\w+\s+\w+).*?released.*?by\s+(\w+)',
                'waiver': r'(\w+\s+\w+).*?waived.*?by\s+(\w+)'
            }
            
            for transaction_type, pattern in patterns.items():
                match = re.search(pattern, text, re.IGNORECASE)
                
                if match:
                    player_name = match.group(1).strip()
                    team = match.group(2).strip().upper()
                    
                    # Clean up team name
                    team = self._normalize_team_name(team)
                    
                    return {
                        'player_name': player_name,
                        'team': team,
                        'transaction_type': transaction_type,
                        'source': source,
                        'raw_text': text[:200],  # Store first 200 chars
                        'timestamp': datetime.now()
                    }
                    
        except Exception as e:
            self.logger.error(f"Error extracting transaction info: {e}")
            
        return None
        
    def _normalize_team_name(self, team_name):
        """Normalize team names to standard abbreviations"""
        team_mapping = {
            'PATRIOTS': 'NE', 'BILLS': 'BUF', 'DOLPHINS': 'MIA', 'JETS': 'NYJ',
            'RAVENS': 'BAL', 'BENGALS': 'CIN', 'BROWNS': 'CLE', 'STEELERS': 'PIT',
            'TEXANS': 'HOU', 'COLTS': 'IND', 'JAGUARS': 'JAX', 'TITANS': 'TEN',
            'BRONCOS': 'DEN', 'CHIEFS': 'KC', 'RAIDERS': 'LV', 'CHARGERS': 'LAC',
            'COWBOYS': 'DAL', 'GIANTS': 'NYG', 'EAGLES': 'PHI', 'COMMANDERS': 'WAS',
            'BEARS': 'CHI', 'LIONS': 'DET', 'PACKERS': 'GB', 'VIKINGS': 'MIN',
            'FALCONS': 'ATL', 'PANTHERS': 'CAR', 'SAINTS': 'NO', 'BUCCANEERS': 'TB',
            'CARDINALS': 'ARI', 'RAMS': 'LAR', '49ERS': 'SF', 'SEAHAWKS': 'SEA'
        }
        
        # Check if already in correct format
        if len(team_name) <= 3:
            return team_name.upper()
            
        # Try to find mapping
        for full_name, abbrev in team_mapping.items():
            if full_name in team_name.upper():
                return abbrev
                
        return team_name[:3].upper()  # Fallback
        
    def process_transactions(self, transactions):
        """Process transactions and update database"""
        session = db.get_session()
        
        try:
            updates_made = 0
            
            for transaction in transactions:
                # Check if transaction already processed
                existing = session.query(TransactionLog).filter_by(
                    raw_text=transaction['raw_text']
                ).first()
                
                if existing:
                    continue  # Skip duplicate
                    
                # Find player in database
                player = session.query(Player).filter(
                    Player.name.ilike(f"%{transaction['player_name']}%")
                ).first()
                
                if player:
                    # Update player team if trade/signing
                    if transaction['transaction_type'] in ['trade', 'signing']:
                        old_team = player.team
                        new_team = transaction['team']
                        
                        if old_team != new_team:
                            player.team = new_team
                            updates_made += 1
                            
                            self.logger.info(f"Updated {player.name}: {old_team} → {new_team}")
                            
                    # Log transaction
                    log_entry = TransactionLog(
                        player_id=player.id,
                        transaction_type=transaction['transaction_type'],
                        old_team=player.team if transaction['transaction_type'] in ['release', 'waiver'] else None,
                        new_team=transaction['team'] if transaction['transaction_type'] in ['trade', 'signing'] else None,
                        source=transaction['source'],
                        raw_text=transaction['raw_text'],
                        timestamp=transaction['timestamp']
                    )
                    
                    session.add(log_entry)
                    
                else:
                    self.logger.warning(f"Player not found: {transaction['player_name']}")
                    
            session.commit()
            return updates_made
            
        except Exception as e:
            self.logger.error(f"Error processing transactions: {e}")
            session.rollback()
            return 0
        finally:
            db.close_session(session)
            
    def get_recent_transactions(self, days=7):
        """Get recent transactions for analysis"""
        session = db.get_session()
        
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            transactions = session.query(TransactionLog).filter(
                TransactionLog.timestamp >= cutoff_date
            ).order_by(TransactionLog.timestamp.desc()).all()
            
            return [
                {
                    'player_name': trans.player.name if trans.player else 'Unknown',
                    'transaction_type': trans.transaction_type,
                    'old_team': trans.old_team,
                    'new_team': trans.new_team,
                    'source': trans.source,
                    'timestamp': trans.timestamp
                }
                for trans in transactions
            ]
            
        finally:
            db.close_session(session)
            
    def check_for_updates_needed(self):
        """Check if any transactions require prediction updates"""
        try:
            # Get transactions from last 24 hours
            recent_transactions = self.get_recent_transactions(days=1)
            
            # Filter for fantasy-relevant transactions
            relevant_transactions = [
                trans for trans in recent_transactions
                if trans['transaction_type'] in ['trade', 'signing'] and
                trans['player_name'] in self._get_fantasy_relevant_players()
            ]
            
            if relevant_transactions:
                self.logger.info(f"Found {len(relevant_transactions)} fantasy-relevant transactions")
                return relevant_transactions
            else:
                return []
                
        except Exception as e:
            self.logger.error(f"Error checking for updates: {e}")
            return []
            
    def _get_fantasy_relevant_players(self):
        """Get list of fantasy-relevant player names"""
        session = db.get_session()
        
        try:
            players = session.query(Player).filter(
                Player.position.in_(['QB', 'RB', 'WR', 'TE'])
            ).all()
            
            return [player.name for player in players]
            
        finally:
            db.close_session(session)