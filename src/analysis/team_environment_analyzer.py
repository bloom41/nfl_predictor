import logging
import numpy as np
from datetime import datetime, timedelta
from src.database.database import db
from src.database.models import Player, PlayerStats, TransactionLog, TeamNews

class TeamEnvironmentAnalyzer:
    """
    Analyze team environment impact on player performance
    Track coaching changes, scheme changes, and team chemistry
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Team offensive schemes and coaching tendencies
        self.team_schemes = {
            'KC': {'pass_heavy': 0.8, 'rb_committee': 0.3, 'wr_spread': 0.9},
            'BUF': {'pass_heavy': 0.7, 'rb_committee': 0.4, 'wr_spread': 0.6},
            'MIA': {'pass_heavy': 0.9, 'rb_committee': 0.2, 'wr_spread': 0.8},
            'SF': {'pass_heavy': 0.5, 'rb_committee': 0.6, 'wr_spread': 0.4},
            'PHI': {'pass_heavy': 0.6, 'rb_committee': 0.3, 'wr_spread': 0.5},
            # Add more teams...
        }
        
        # Position value by scheme
        self.scheme_impact = {
            'pass_heavy': {'QB': 1.2, 'WR': 1.15, 'TE': 1.1, 'RB': 0.85},
            'run_heavy': {'QB': 0.9, 'WR': 0.9, 'TE': 1.0, 'RB': 1.25},
            'balanced': {'QB': 1.0, 'WR': 1.0, 'TE': 1.0, 'RB': 1.0}
        }
        
    def analyze_player_environment_change(self, player_id, old_team, new_team):
        """Analyze how team change affects player projections"""
        try:
            session = db.get_session()
            
            player = session.query(Player).filter_by(id=player_id).first()
            if not player:
                return None
                
            # Get team scheme differences
            old_scheme = self.team_schemes.get(old_team, self._get_default_scheme())
            new_scheme = self.team_schemes.get(new_team, self._get_default_scheme())
            
            # Calculate environment impact
            impact_analysis = {
                'player_name': player.name,
                'position': player.position,
                'old_team': old_team,
                'new_team': new_team,
                'scheme_change': self._calculate_scheme_impact(player.position, old_scheme, new_scheme),
                'opportunity_change': self._calculate_opportunity_change(player.position, old_team, new_team),
                'target_share_impact': self._calculate_target_share_impact(player, old_team, new_team),
                'coaching_impact': self._calculate_coaching_impact(old_team, new_team),
                'overall_impact': 0.0
            }
            
            # Calculate overall impact score
            impact_analysis['overall_impact'] = self._calculate_overall_impact(impact_analysis)
            
            self.logger.info(f"Environment analysis for {player.name}: {impact_analysis['overall_impact']:.2f} impact")
            
            return impact_analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing environment change: {e}")
            return None
        finally:
            db.close_session(session)
            
    def _calculate_scheme_impact(self, position, old_scheme, new_scheme):
        """Calculate impact of scheme change on position"""
        try:
            # Compare key scheme metrics
            scheme_factors = {
                'pass_heavy_change': new_scheme['pass_heavy'] - old_scheme['pass_heavy'],
                'rb_committee_change': new_scheme['rb_committee'] - old_scheme['rb_committee'],
                'wr_spread_change': new_scheme['wr_spread'] - old_scheme['wr_spread']
            }
            
            # Position-specific impact calculation
            if position == 'QB':
                impact = scheme_factors['pass_heavy_change'] * 0.8
            elif position == 'RB':
                impact = -scheme_factors['pass_heavy_change'] * 0.6 - scheme_factors['rb_committee_change'] * 0.4
            elif position == 'WR':
                impact = scheme_factors['pass_heavy_change'] * 0.5 + scheme_factors['wr_spread_change'] * 0.3
            elif position == 'TE':
                impact = scheme_factors['pass_heavy_change'] * 0.4 - scheme_factors['wr_spread_change'] * 0.2
            else:
                impact = 0.0
                
            return round(impact, 3)
            
        except Exception as e:
            self.logger.error(f"Error calculating scheme impact: {e}")
            return 0.0
            
    def _calculate_opportunity_change(self, position, old_team, new_team):
        """Calculate change in opportunity/usage"""
        try:
            session = db.get_session()
            
            # Get team usage patterns
            old_usage = self._get_team_usage_patterns(old_team, position, session)
            new_usage = self._get_team_usage_patterns(new_team, position, session)
            
            # Calculate opportunity change
            if position == 'QB':
                # QB opportunities are fairly consistent
                opportunity_change = 0.0
            elif position == 'RB':
                # RB opportunity based on team run volume and committee usage
                old_touches_per_game = old_usage.get('avg_rb_touches', 20)
                new_touches_per_game = new_usage.get('avg_rb_touches', 20)
                opportunity_change = (new_touches_per_game - old_touches_per_game) / old_touches_per_game
            elif position in ['WR', 'TE']:
                # WR/TE opportunity based on target distribution
                old_targets_per_game = old_usage.get(f'avg_{position.lower()}_targets', 8)
                new_targets_per_game = new_usage.get(f'avg_{position.lower()}_targets', 8)
                opportunity_change = (new_targets_per_game - old_targets_per_game) / old_targets_per_game
            else:
                opportunity_change = 0.0
                
            return round(opportunity_change, 3)
            
        except Exception as e:
            self.logger.error(f"Error calculating opportunity change: {e}")
            return 0.0
        finally:
            db.close_session(session)
            
    def _get_team_usage_patterns(self, team, position, session):
        """Get team's historical usage patterns"""
        try:
            # Get recent season data for team
            team_players = session.query(Player).filter_by(
                team=team, position=position
            ).limit(5).all()
            
            if not team_players:
                return self._get_default_usage_patterns(position)
                
            # Calculate average usage metrics
            usage_data = {}
            
            if position == 'RB':
                avg_rushing_attempts = 0
                avg_targets = 0
                count = 0
                
                for player in team_players:
                    recent_stats = session.query(PlayerStats).filter_by(
                        player_id=player.id, season=2024
                    ).first()
                    
                    if recent_stats:
                        avg_rushing_attempts += recent_stats.rushing_attempts or 0
                        avg_targets += recent_stats.targets or 0
                        count += 1
                        
                if count > 0:
                    usage_data['avg_rb_touches'] = (avg_rushing_attempts + avg_targets) / count
                else:
                    usage_data['avg_rb_touches'] = 15
                    
            elif position in ['WR', 'TE']:
                avg_targets = 0
                count = 0
                
                for player in team_players:
                    recent_stats = session.query(PlayerStats).filter_by(
                        player_id=player.id, season=2024
                    ).first()
                    
                    if recent_stats:
                        avg_targets += recent_stats.targets or 0
                        count += 1
                        
                if count > 0:
                    usage_data[f'avg_{position.lower()}_targets'] = avg_targets / count
                else:
                    usage_data[f'avg_{position.lower()}_targets'] = 6 if position == 'TE' else 8
                    
            return usage_data
            
        except Exception as e:
            self.logger.error(f"Error getting team usage patterns: {e}")
            return self._get_default_usage_patterns(position)
            
    def _get_default_usage_patterns(self, position):
        """Get default usage patterns"""
        defaults = {
            'QB': {'avg_attempts': 35},
            'RB': {'avg_rb_touches': 15},
            'WR': {'avg_wr_targets': 8},
            'TE': {'avg_te_targets': 6}
        }
        
        return defaults.get(position, {})
        
    def _calculate_target_share_impact(self, player, old_team, new_team):
        """Calculate expected change in target/touch share"""
        try:
            session = db.get_session()
            
            # Get team depth charts and competition
            old_competition = self._get_position_competition(old_team, player.position, session)
            new_competition = self._get_position_competition(new_team, player.position, session)
            
            # Calculate competition level change
            competition_change = len(old_competition) - len(new_competition)
            
            # Convert to target share impact
            if player.position == 'QB':
                target_share_impact = 0.0  # QBs typically don't share targets
            elif player.position == 'RB':
                # More RBs = less touches per player
                target_share_impact = competition_change * 0.1
            elif player.position in ['WR', 'TE']:
                # More receivers = fewer targets per player
                target_share_impact = competition_change * 0.08
            else:
                target_share_impact = 0.0
                
            return round(target_share_impact, 3)
            
        except Exception as e:
            self.logger.error(f"Error calculating target share impact: {e}")
            return 0.0
        finally:
            db.close_session(session)
            
    def _get_position_competition(self, team, position, session):
        """Get list of players at same position on team"""
        try:
            competitors = session.query(Player).filter_by(
                team=team, position=position
            ).all()
            
            return [p.name for p in competitors]
            
        except Exception as e:
            self.logger.error(f"Error getting position competition: {e}")
            return []
            
    def _calculate_coaching_impact(self, old_team, new_team):
        """Calculate impact of coaching philosophy change"""
        try:
            # Coaching impact factors (simplified)
            coaching_factors = {
                'KC': {'offensive_innovation': 0.9, 'player_development': 0.8},
                'BUF': {'offensive_innovation': 0.7, 'player_development': 0.7},
                'SF': {'offensive_innovation': 0.8, 'player_development': 0.9},
                'NE': {'offensive_innovation': 0.6, 'player_development': 0.8},
                # Add more teams...
            }
            
            old_coaching = coaching_factors.get(old_team, {'offensive_innovation': 0.5, 'player_development': 0.5})
            new_coaching = coaching_factors.get(new_team, {'offensive_innovation': 0.5, 'player_development': 0.5})
            
            # Calculate coaching impact
            innovation_change = new_coaching['offensive_innovation'] - old_coaching['offensive_innovation']
            development_change = new_coaching['player_development'] - old_coaching['player_development']
            
            coaching_impact = (innovation_change + development_change) / 2
            
            return round(coaching_impact, 3)
            
        except Exception as e:
            self.logger.error(f"Error calculating coaching impact: {e}")
            return 0.0
            
    def _calculate_overall_impact(self, impact_analysis):
        """Calculate overall environment impact score"""
        try:
            # Weight different factors
            weights = {
                'scheme_change': 0.3,
                'opportunity_change': 0.35,
                'target_share_impact': 0.25,
                'coaching_impact': 0.1
            }
            
            overall_impact = 0.0
            
            for factor, weight in weights.items():
                overall_impact += impact_analysis.get(factor, 0.0) * weight
                
            # Cap impact at reasonable bounds
            overall_impact = max(-0.3, min(0.3, overall_impact))
            
            return round(overall_impact, 3)
            
        except Exception as e:
            self.logger.error(f"Error calculating overall impact: {e}")
            return 0.0
            
    def _get_default_scheme(self):
        """Get default team scheme"""
        return {
            'pass_heavy': 0.6,
            'rb_committee': 0.5,
            'wr_spread': 0.6
        }
        
    def get_recent_team_environment_changes(self, days=30):
        """Get recent environment changes that may affect predictions"""
        try:
            session = db.get_session()
            
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # Get recent transactions
            recent_transactions = session.query(TransactionLog).filter(
                TransactionLog.timestamp >= cutoff_date,
                TransactionLog.transaction_type.in_(['trade', 'signing'])
            ).all()
            
            environment_changes = []
            
            for transaction in recent_transactions:
                if transaction.player and transaction.old_team != transaction.new_team:
                    # Analyze environment impact
                    impact = self.analyze_player_environment_change(
                        transaction.player_id,
                        transaction.old_team,
                        transaction.new_team
                    )
                    
                    if impact and abs(impact['overall_impact']) > 0.05:  # Meaningful impact
                        environment_changes.append(impact)
                        
            return environment_changes
            
        except Exception as e:
            self.logger.error(f"Error getting environment changes: {e}")
            return []
        finally:
            db.close_session(session)
            
    def update_predictions_for_environment_changes(self):
        """Update predictions based on recent environment changes"""
        try:
            changes = self.get_recent_team_environment_changes()
            
            updates_needed = []
            
            for change in changes:
                if abs(change['overall_impact']) > 0.1:  # Significant impact
                    updates_needed.append({
                        'player_name': change['player_name'],
                        'impact_factor': change['overall_impact'],
                        'reason': f"Team change from {change['old_team']} to {change['new_team']}"
                    })
                    
            if updates_needed:
                self.logger.info(f"Found {len(updates_needed)} players needing prediction updates due to environment changes")
                
            return updates_needed
            
        except Exception as e:
            self.logger.error(f"Error updating predictions for environment changes: {e}")
            return []