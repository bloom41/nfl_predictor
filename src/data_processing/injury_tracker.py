import json
import logging
import re
from datetime import datetime, timedelta
from textblob import TextBlob
from src.database.database import db
from src.database.models import Player, InjuryHistory, WorkloadTracking, TeamNews

class InjuryTracker:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Injury keywords and severity mapping
        self.injury_keywords = {
            'minor': ['day-to-day', 'questionable', 'probable', 'minor', 'soreness', 'rest'],
            'moderate': ['doubtful', 'week-to-week', 'strain', 'sprain', 'bruise', 'contusion'],
            'major': ['ir', 'injured reserve', 'surgery', 'tear', 'break', 'fracture', 'season-ending']
        }
        
        self.body_parts = {
            'leg': ['hamstring', 'quad', 'calf', 'thigh', 'knee', 'ankle', 'foot', 'achilles'],
            'arm': ['shoulder', 'elbow', 'wrist', 'hand', 'finger', 'bicep', 'tricep'],
            'back': ['back', 'spine', 'neck'],
            'head': ['concussion', 'head', 'brain'],
            'core': ['abdomen', 'ribs', 'chest', 'hip', 'groin']
        }
        
    def analyze_injury_risk(self, player_id, season):
        """Analyze injury risk based on historical patterns"""
        session = db.get_session()
        
        try:
            # Get player's injury history
            injuries = session.query(InjuryHistory).filter_by(
                player_id=player_id
            ).order_by(InjuryHistory.season.desc(), InjuryHistory.week.desc()).all()
            
            if not injuries:
                return {
                    'risk_score': 0.1,  # Baseline risk
                    'risk_factors': [],
                    'injury_prone_areas': []
                }
                
            # Calculate risk factors
            risk_factors = []
            injury_areas = {}
            recent_injuries = 0
            
            for injury in injuries:
                # Recent injury factor (last 2 seasons)
                if injury.season >= season - 2:
                    recent_injuries += 1
                    
                # Track injury-prone body parts
                if injury.body_part:
                    injury_areas[injury.body_part] = injury_areas.get(injury.body_part, 0) + 1
                    
                # Severity weighting
                if injury.severity == 'major':
                    risk_factors.append(f"Major {injury.injury_type} injury")
                elif injury.severity == 'moderate' and injury.games_missed > 2:
                    risk_factors.append(f"Recurring {injury.injury_type}")
            
            # Calculate base risk score
            base_risk = min(0.8, recent_injuries * 0.15)  # Cap at 80%
            
            # Adjust for injury-prone areas
            if injury_areas:
                most_common_area = max(injury_areas, key=injury_areas.get)
                if injury_areas[most_common_area] >= 2:
                    base_risk += 0.1
                    risk_factors.append(f"History of {most_common_area} injuries")
            
            return {
                'risk_score': min(base_risk, 0.9),  # Cap at 90%
                'risk_factors': risk_factors,
                'injury_prone_areas': list(injury_areas.keys()),
                'recent_injury_count': recent_injuries
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing injury risk for player {player_id}: {e}")
            return {'risk_score': 0.2, 'risk_factors': [], 'injury_prone_areas': []}
        finally:
            db.close_session(session)
            
    def analyze_workload_risk(self, player_id, season, current_week):
        """Analyze overuse risk based on workload patterns"""
        session = db.get_session()
        
        try:
            # Get recent workload data
            workloads = session.query(WorkloadTracking).filter_by(
                player_id=player_id,
                season=season
            ).filter(WorkloadTracking.week < current_week).all()
            
            if not workloads:
                return {
                    'overuse_risk': 0.1,
                    'risk_factors': [],
                    'usage_trend': 'stable'
                }
                
            # Calculate workload metrics
            recent_workloads = workloads[-4:]  # Last 4 games
            risk_factors = []
            
            # High snap percentage streak
            high_usage_streak = 0
            total_touches = []
            snap_percentages = []
            
            for workload in recent_workloads:
                snap_percentages.append(workload.snap_percentage)
                total_touches.append(workload.total_touches)
                
                if workload.snap_percentage > 80:
                    high_usage_streak += 1
                else:
                    high_usage_streak = 0
                    
            # Risk assessment
            overuse_risk = 0.1  # Baseline
            
            # High usage streak
            if high_usage_streak >= 3:
                overuse_risk += 0.2
                risk_factors.append(f"{high_usage_streak} games with >80% snaps")
                
            # Touch count trend
            if len(total_touches) >= 2:
                recent_avg = sum(total_touches[-2:]) / 2
                season_avg = sum(total_touches) / len(total_touches)
                
                if recent_avg > season_avg * 1.3:  # 30% above season average
                    overuse_risk += 0.15
                    risk_factors.append("Touch count significantly above season average")
                    
            # Snap percentage trend
            if len(snap_percentages) >= 3:
                trend = snap_percentages[-1] - snap_percentages[-3]
                if trend > 15:  # Increasing snap share by >15%
                    overuse_risk += 0.1
                    risk_factors.append("Increasing workload trend")
                    
            usage_trend = 'increasing' if trend > 5 else 'decreasing' if trend < -5 else 'stable'
            
            return {
                'overuse_risk': min(overuse_risk, 0.8),
                'risk_factors': risk_factors,
                'usage_trend': usage_trend,
                'current_snap_percentage': snap_percentages[-1] if snap_percentages else 0,
                'high_usage_streak': high_usage_streak
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing workload risk for player {player_id}: {e}")
            return {'overuse_risk': 0.1, 'risk_factors': [], 'usage_trend': 'stable'}
        finally:
            db.close_session(session)
            
    def extract_injury_info_from_text(self, text, player_name):
        """Extract injury information from news text"""
        text_lower = text.lower()
        player_lower = player_name.lower()
        
        # Check if player is mentioned
        if player_lower not in text_lower:
            return None
            
        # Find injury-related sentences
        sentences = text.split('.')
        injury_sentences = []
        
        for sentence in sentences:
            if player_lower in sentence.lower():
                for severity in self.injury_keywords:
                    for keyword in self.injury_keywords[severity]:
                        if keyword in sentence.lower():
                            injury_sentences.append(sentence.strip())
                            break
                            
        if not injury_sentences:
            return None
            
        # Extract injury details
        injury_info = {
            'description': ' '.join(injury_sentences),
            'severity': 'minor',  # Default
            'injury_type': None,
            'body_part': None,
            'games_missed': 0
        }
        
        # Determine severity
        text_combined = ' '.join(injury_sentences).lower()
        for severity in ['major', 'moderate', 'minor']:
            for keyword in self.injury_keywords[severity]:
                if keyword in text_combined:
                    injury_info['severity'] = severity
                    break
                    
        # Extract body part and injury type
        for body_part, injuries in self.body_parts.items():
            for injury_type in injuries:
                if injury_type in text_combined:
                    injury_info['body_part'] = body_part
                    injury_info['injury_type'] = injury_type
                    break
                    
        # Extract games missed (simple pattern matching)
        import re
        games_pattern = r'(\d+)\s*(?:game|week)'
        match = re.search(games_pattern, text_combined)
        if match:
            injury_info['games_missed'] = int(match.group(1))
            
        return injury_info
        
    def update_injury_from_news(self, news_article):
        """Update injury database from news article"""
        session = db.get_session()
        
        try:
            # Extract mentioned players
            if not news_article.players_mentioned:
                return
                
            players_mentioned = json.loads(news_article.players_mentioned)
            
            for player_name in players_mentioned:
                # Find player in database
                player = session.query(Player).filter(
                    Player.name.ilike(f"%{player_name}%")
                ).first()
                
                if not player:
                    continue
                    
                # Extract injury information
                injury_info = self.extract_injury_info_from_text(
                    news_article.title + " " + (news_article.content or ""),
                    player_name
                )
                
                if injury_info:
                    # Check if similar injury already exists
                    existing_injury = session.query(InjuryHistory).filter_by(
                        player_id=player.id,
                        season=2024,  # Current season
                        injury_type=injury_info['injury_type']
                    ).filter(InjuryHistory.is_active == True).first()
                    
                    if not existing_injury:
                        # Create new injury record
                        injury = InjuryHistory(
                            player_id=player.id,
                            season=2024,
                            week=1,  # Would need actual week calculation
                            injury_type=injury_info['injury_type'],
                            body_part=injury_info['body_part'],
                            severity=injury_info['severity'],
                            games_missed=injury_info['games_missed'],
                            description=injury_info['description']
                        )
                        session.add(injury)
                        
            session.commit()
            
        except Exception as e:
            session.rollback()
            self.logger.error(f"Error updating injury from news: {e}")
        finally:
            db.close_session(session)
            
    def calculate_combined_risk_score(self, player_id, season, week):
        """Calculate combined injury + workload risk score"""
        injury_risk = self.analyze_injury_risk(player_id, season)
        workload_risk = self.analyze_workload_risk(player_id, season, week)
        
        # Weighted combination
        combined_risk = (
            injury_risk['risk_score'] * 0.6 +  # Historical injury risk
            workload_risk['overuse_risk'] * 0.4  # Current workload risk
        )
        
        # Combine risk factors
        all_risk_factors = injury_risk['risk_factors'] + workload_risk['risk_factors']
        
        return {
            'total_risk_score': min(combined_risk, 0.95),  # Cap at 95%
            'injury_risk': injury_risk['risk_score'],
            'workload_risk': workload_risk['overuse_risk'],
            'risk_factors': all_risk_factors,
            'injury_prone_areas': injury_risk.get('injury_prone_areas', []),
            'usage_trend': workload_risk.get('usage_trend', 'stable')
        }