import logging
import numpy as np
from datetime import datetime
from src.database.database import db
from src.database.models import Player, PlayerStats, WorkloadTracking

class WorkloadAnalyzer:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Workload thresholds by position
        self.position_thresholds = {
            'QB': {'high_snap_pct': 85, 'high_touches': 35},  # Passing attempts + rushes
            'RB': {'high_snap_pct': 70, 'high_touches': 25},  # Carries + receptions  
            'WR': {'high_snap_pct': 75, 'high_touches': 12},  # Targets/receptions
            'TE': {'high_snap_pct': 70, 'high_touches': 8}    # Targets/receptions
        }
        
    def calculate_workload_metrics(self, player_id, season, week):
        """Calculate comprehensive workload metrics for a player"""
        session = db.get_session()
        
        try:
            player = session.query(Player).filter_by(id=player_id).first()
            if not player:
                return None
                
            # Get player stats for the week
            stats = session.query(PlayerStats).filter_by(
                player_id=player_id,
                season=season,
                week=week
            ).first()
            
            if not stats:
                return None
                
            # Calculate position-specific workload
            workload_data = self._calculate_position_workload(player, stats)
            
            # Get historical context
            historical_workload = self._get_historical_workload(player_id, season, week, session)
            
            # Calculate risk indicators
            risk_indicators = self._calculate_risk_indicators(
                workload_data, historical_workload, player.position
            )
            
            # Combine all metrics
            workload_metrics = {
                **workload_data,
                **risk_indicators,
                'player_id': player_id,
                'season': season,
                'week': week
            }
            
            return workload_metrics
            
        except Exception as e:
            self.logger.error(f"Error calculating workload metrics: {e}")
            return None
        finally:
            db.close_session(session)
            
    def _calculate_position_workload(self, player, stats):
        """Calculate position-specific workload metrics"""
        position = player.position
        
        # Base metrics for all positions
        total_touches = (stats.rushing_attempts or 0) + (stats.receptions or 0)
        
        # Estimate snap counts (would need actual data in production)
        estimated_snaps = self._estimate_snap_count(player, stats)
        total_team_snaps = 65  # Average team snaps per game
        snap_percentage = (estimated_snaps / total_team_snaps) * 100
        
        workload_data = {
            'offensive_snaps': estimated_snaps,
            'total_snaps': total_team_snaps,
            'snap_percentage': snap_percentage,
            'total_touches': total_touches,
            'targets': stats.targets or 0
        }
        
        # Position-specific calculations
        if position == 'QB':
            workload_data.update({
                'total_touches': (stats.passing_attempts or 0) + (stats.rushing_attempts or 0),
                'red_zone_touches': (stats.passing_tds or 0) + (stats.rushing_tds or 0)  # Approximation
            })
        elif position == 'RB':
            workload_data.update({
                'red_zone_touches': stats.rushing_tds or 0,
                'yards_after_contact': (stats.rushing_yards or 0) * 0.6  # Estimate
            })
        elif position in ['WR', 'TE']:
            workload_data.update({
                'red_zone_touches': stats.receiving_tds or 0,
                'air_yards_share': 0.15 if stats.receiving_yards and stats.receiving_yards > 50 else 0.08
            })
            
        return workload_data
        
    def _estimate_snap_count(self, player, stats):
        """Estimate snap count based on statistical production"""
        position = player.position
        
        # Rough estimation based on production (would use actual snap data in production)
        if position == 'QB':
            # QBs with passing attempts likely played most snaps
            if (stats.passing_attempts or 0) > 20:
                return 65  # Assume starter played most snaps
            elif (stats.passing_attempts or 0) > 5:
                return 30  # Backup got some snaps
            else:
                return 5   # Minimal snaps
                
        elif position == 'RB':
            touches = (stats.rushing_attempts or 0) + (stats.receptions or 0)
            if touches > 15:
                return 50  # Featured back
            elif touches > 8:
                return 35  # Rotational back
            else:
                return 15  # Limited role
                
        elif position in ['WR', 'TE']:
            targets = stats.targets or 0
            if targets > 8:
                return 55  # Primary receiver
            elif targets > 4:
                return 40  # Secondary receiver
            else:
                return 20  # Limited role
                
        return 25  # Default
        
    def _get_historical_workload(self, player_id, season, current_week, session):
        """Get historical workload data for comparison"""
        # Get previous weeks this season
        previous_workloads = session.query(WorkloadTracking).filter_by(
            player_id=player_id,
            season=season
        ).filter(WorkloadTracking.week < current_week).all()
        
        if not previous_workloads:
            return {'season_avg_snaps': 0, 'season_avg_touches': 0, 'games_played': 0}
            
        total_snaps = sum(w.snap_percentage for w in previous_workloads)
        total_touches = sum(w.total_touches for w in previous_workloads)
        games_played = len(previous_workloads)
        
        return {
            'season_avg_snaps': total_snaps / games_played if games_played > 0 else 0,
            'season_avg_touches': total_touches / games_played if games_played > 0 else 0,
            'games_played': games_played
        }
        
    def _calculate_risk_indicators(self, current_workload, historical, position):
        """Calculate workload risk indicators"""
        thresholds = self.position_thresholds.get(position, self.position_thresholds['RB'])
        
        # High usage indicators
        high_snap_game = current_workload['snap_percentage'] > thresholds['high_snap_pct']
        high_touch_game = current_workload['total_touches'] > thresholds['high_touches']
        
        # Compared to season average
        touches_vs_avg = 0
        if historical['season_avg_touches'] > 0:
            touches_vs_avg = (current_workload['total_touches'] - historical['season_avg_touches']) / historical['season_avg_touches']
            
        # Calculate consecutive high usage (would need database tracking)
        consecutive_high_usage = 1 if high_snap_game else 0  # Simplified
        
        return {
            'consecutive_games_high_usage': consecutive_high_usage,
            'touches_vs_season_avg': touches_vs_avg,
            'is_high_usage_game': high_snap_game or high_touch_game,
            'usage_intensity': min(1.0, current_workload['snap_percentage'] / 100 + current_workload['total_touches'] / 30)
        }
        
    def store_workload_data(self, workload_metrics):
        """Store workload data in database"""
        session = db.get_session()
        
        try:
            # Check if workload data already exists
            existing = session.query(WorkloadTracking).filter_by(
                player_id=workload_metrics['player_id'],
                season=workload_metrics['season'],
                week=workload_metrics['week']
            ).first()
            
            if existing:
                # Update existing record
                for key, value in workload_metrics.items():
                    if hasattr(existing, key):
                        setattr(existing, key, value)
            else:
                # Create new record
                workload = WorkloadTracking(**workload_metrics)
                session.add(workload)
                
            session.commit()
            
        except Exception as e:
            session.rollback()
            self.logger.error(f"Error storing workload data: {e}")
        finally:
            db.close_session(session)
            
    def analyze_all_players_workload(self, season, week):
        """Analyze workload for all players with stats in given week"""
        session = db.get_session()
        
        try:
            # Get all player stats for the week
            stats_records = session.query(PlayerStats).filter_by(
                season=season,
                week=week
            ).all()
            
            workload_records = []
            
            for stats in stats_records:
                workload_metrics = self.calculate_workload_metrics(
                    stats.player_id, season, week
                )
                
                if workload_metrics:
                    workload_records.append(workload_metrics)
                    self.store_workload_data(workload_metrics)
                    
            self.logger.info(f"Analyzed workload for {len(workload_records)} players in week {week}")
            return workload_records
            
        except Exception as e:
            self.logger.error(f"Error analyzing all players workload: {e}")
            return []
        finally:
            db.close_session(session)
            
    def get_overuse_alerts(self, season, week, risk_threshold=0.7):
        """Get players at high risk of overuse/injury"""
        session = db.get_session()
        
        try:
            # Get recent workload data
            workloads = session.query(WorkloadTracking).filter_by(
                season=season,
                week=week
            ).filter(WorkloadTracking.usage_intensity > risk_threshold).all()
            
            alerts = []
            for workload in workloads:
                player = session.query(Player).filter_by(id=workload.player_id).first()
                if player:
                    alerts.append({
                        'player_name': player.name,
                        'team': player.team,
                        'position': player.position,
                        'snap_percentage': workload.snap_percentage,
                        'total_touches': workload.total_touches,
                        'usage_intensity': workload.usage_intensity,
                        'risk_level': 'HIGH' if workload.usage_intensity > 0.85 else 'MODERATE'
                    })
                    
            return sorted(alerts, key=lambda x: x['usage_intensity'], reverse=True)
            
        except Exception as e:
            self.logger.error(f"Error getting overuse alerts: {e}")
            return []
        finally:
            db.close_session(session)