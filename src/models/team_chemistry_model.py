"""
Advanced Team Chemistry Modeling for NFL Predictions
Analyzes player synergies, coaching system fit, and team dynamics
"""
from typing import Dict, List, Optional, Tuple, Any, Union
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from src.utils.type_hint_utility import PlayerId, Season, Week, TeamCode, Position, FantasyPoints
from src.utils.unified_database_operations import DatabaseSessionManager, CommonQueries
from src.database.models import Player, PlayerStats, TeamNews, WorkloadTracking


class ChemistryType(Enum):
    """Types of team chemistry analysis"""
    OFFENSIVE_LINE = "offensive_line"
    QUARTERBACK_RECEIVER = "qb_receiver"
    RUNNING_BACK_LINE = "rb_line"
    COACHING_FIT = "coaching_fit"
    LEADERSHIP = "leadership"
    VETERAN_ROOKIE = "veteran_rookie"
    POSITION_GROUP = "position_group"


@dataclass
class ChemistryFactor:
    """Individual chemistry factor analysis"""
    factor_type: ChemistryType
    player_id: PlayerId
    partner_ids: List[PlayerId]
    chemistry_score: float  # 0.0-1.0 scale
    confidence: float
    factors: Dict[str, float]
    improvement_trend: float  # Positive = improving, negative = declining
    
    
@dataclass
class TeamChemistryProfile:
    """Complete team chemistry profile"""
    team_code: TeamCode
    season: Season
    week: Week
    overall_chemistry_score: float
    position_group_scores: Dict[str, float]
    key_partnerships: List[ChemistryFactor]
    risk_factors: List[str]
    improvement_opportunities: List[str]
    coaching_system_fit: float
    

class TeamChemistryModel:
    """Advanced team chemistry modeling system"""
    
    def __init__(self) -> None:
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.db_manager: DatabaseSessionManager = DatabaseSessionManager()
        self.queries: CommonQueries = CommonQueries()
        
        # Chemistry weight factors
        self.chemistry_weights: Dict[ChemistryType, float] = {
            ChemistryType.OFFENSIVE_LINE: 0.25,
            ChemistryType.QUARTERBACK_RECEIVER: 0.20,
            ChemistryType.RUNNING_BACK_LINE: 0.15,
            ChemistryType.COACHING_FIT: 0.15,
            ChemistryType.LEADERSHIP: 0.10,
            ChemistryType.VETERAN_ROOKIE: 0.08,
            ChemistryType.POSITION_GROUP: 0.07
        }
        
        # Position group definitions
        self.position_groups: Dict[str, List[Position]] = {
            'offensive_line': ['C', 'LG', 'RG', 'LT', 'RT'],
            'receiving_corps': ['WR', 'TE'],
            'backfield': ['QB', 'RB'],
            'secondary': ['CB', 'S', 'FS', 'SS'],
            'linebackers': ['LB', 'ILB', 'OLB'],
            'defensive_line': ['DE', 'DT', 'NT']
        }
    
    def analyze_team_chemistry(self, team_code: TeamCode, season: Season, week: Week) -> TeamChemistryProfile:
        """Perform comprehensive team chemistry analysis"""
        self.logger.info(f"Analyzing team chemistry for {team_code} - {season} Week {week}")
        
        try:
            # Get team players
            team_players: List[Player] = self.db_manager.safe_find_team_players(team_code)
            if not team_players:
                self.logger.warning(f"No players found for team {team_code}")
                return self._create_default_profile(team_code, season, week)
            
            # Analyze different chemistry factors
            chemistry_factors: List[ChemistryFactor] = []
            
            # Analyze offensive line chemistry
            ol_chemistry = self._analyze_offensive_line_chemistry(team_players, season, week)
            if ol_chemistry:
                chemistry_factors.extend(ol_chemistry)
            
            # Analyze QB-receiver chemistry
            qb_wr_chemistry = self._analyze_qb_receiver_chemistry(team_players, season, week)
            if qb_wr_chemistry:
                chemistry_factors.extend(qb_wr_chemistry)
            
            # Analyze running back-line chemistry
            rb_line_chemistry = self._analyze_rb_line_chemistry(team_players, season, week)
            if rb_line_chemistry:
                chemistry_factors.extend(rb_line_chemistry)
            
            # Analyze coaching system fit
            coaching_fit = self._analyze_coaching_system_fit(team_code, team_players, season)
            
            # Analyze leadership dynamics
            leadership_factors = self._analyze_leadership_dynamics(team_players, season, week)
            if leadership_factors:
                chemistry_factors.extend(leadership_factors)
            
            # Calculate position group scores
            position_scores = self._calculate_position_group_scores(chemistry_factors)
            
            # Calculate overall chemistry score
            overall_score = self._calculate_overall_chemistry_score(chemistry_factors, coaching_fit)
            
            # Identify risk factors and opportunities
            risk_factors = self._identify_risk_factors(chemistry_factors, team_players)
            opportunities = self._identify_improvement_opportunities(chemistry_factors, team_players)
            
            # Get key partnerships (top chemistry factors)
            key_partnerships = sorted(chemistry_factors, key=lambda x: x.chemistry_score, reverse=True)[:5]
            
            return TeamChemistryProfile(
                team_code=team_code,
                season=season,
                week=week,
                overall_chemistry_score=overall_score,
                position_group_scores=position_scores,
                key_partnerships=key_partnerships,
                risk_factors=risk_factors,
                improvement_opportunities=opportunities,
                coaching_system_fit=coaching_fit
            )
            
        except Exception as e:
            self.logger.error(f"Error analyzing team chemistry for {team_code}: {e}")
            return self._create_default_profile(team_code, season, week)
    
    def _analyze_offensive_line_chemistry(self, players: List[Player], season: Season, week: Week) -> List[ChemistryFactor]:
        """Analyze offensive line unit chemistry"""
        ol_players = [p for p in players if p.position in self.position_groups['offensive_line']]
        if len(ol_players) < 3:
            return []
        
        chemistry_factors: List[ChemistryFactor] = []
        
        # Analyze each o-line player's chemistry with the unit
        for player in ol_players:
            partner_ids = [p.id for p in ol_players if p.id != player.id]
            
            # Get player stats history for chemistry analysis
            recent_stats = self.queries.get_recent_player_stats(player.id, limit=8)
            
            # Calculate chemistry factors
            factors = {
                'games_together': self._calculate_games_together(player.id, partner_ids, season),
                'performance_consistency': self._calculate_consistency_score(recent_stats),
                'experience_level': min(player.experience_years or 0, 10) / 10.0,
                'injury_stability': self._calculate_injury_stability(player.id, season),
                'snap_percentage_stability': self._calculate_snap_stability(player.id, season, week)
            }
            
            # Calculate overall chemistry score
            chemistry_score = (
                factors['games_together'] * 0.3 +
                factors['performance_consistency'] * 0.25 +
                factors['experience_level'] * 0.2 +
                factors['injury_stability'] * 0.15 +
                factors['snap_percentage_stability'] * 0.1
            )
            
            # Calculate improvement trend
            improvement_trend = self._calculate_improvement_trend(recent_stats)
            
            chemistry_factor = ChemistryFactor(
                factor_type=ChemistryType.OFFENSIVE_LINE,
                player_id=player.id,
                partner_ids=partner_ids,
                chemistry_score=chemistry_score,
                confidence=0.8,  # High confidence for o-line chemistry
                factors=factors,
                improvement_trend=improvement_trend
            )
            
            chemistry_factors.append(chemistry_factor)
        
        return chemistry_factors
    
    def _analyze_qb_receiver_chemistry(self, players: List[Player], season: Season, week: Week) -> List[ChemistryFactor]:
        """Analyze quarterback-receiver chemistry"""
        qbs = [p for p in players if p.position == 'QB']
        receivers = [p for p in players if p.position in ['WR', 'TE']]
        
        if not qbs or not receivers:
            return []
        
        chemistry_factors: List[ChemistryFactor] = []
        
        for qb in qbs:
            for receiver in receivers:
                # Calculate QB-WR specific chemistry
                factors = {
                    'completion_rate_together': self._calculate_completion_rate(qb.id, receiver.id, season),
                    'target_share_consistency': self._calculate_target_consistency(qb.id, receiver.id, season),
                    'red_zone_connection': self._calculate_red_zone_chemistry(qb.id, receiver.id, season),
                    'route_timing_efficiency': self._estimate_route_timing(qb.id, receiver.id, season),
                    'pressure_situation_performance': self._calculate_pressure_performance(qb.id, receiver.id, season)
                }
                
                chemistry_score = (
                    factors['completion_rate_together'] * 0.3 +
                    factors['target_share_consistency'] * 0.25 +
                    factors['red_zone_connection'] * 0.2 +
                    factors['route_timing_efficiency'] * 0.15 +
                    factors['pressure_situation_performance'] * 0.1
                )
                
                # Get recent performance trend
                qb_stats = self.queries.get_recent_player_stats(qb.id, limit=5)
                improvement_trend = self._calculate_improvement_trend(qb_stats)
                
                chemistry_factor = ChemistryFactor(
                    factor_type=ChemistryType.QUARTERBACK_RECEIVER,
                    player_id=receiver.id,
                    partner_ids=[qb.id],
                    chemistry_score=chemistry_score,
                    confidence=0.75,
                    factors=factors,
                    improvement_trend=improvement_trend
                )
                
                chemistry_factors.append(chemistry_factor)
        
        return chemistry_factors
    
    def _analyze_rb_line_chemistry(self, players: List[Player], season: Season, week: Week) -> List[ChemistryFactor]:
        """Analyze running back and offensive line chemistry"""
        rbs = [p for p in players if p.position == 'RB']
        ol_players = [p for p in players if p.position in self.position_groups['offensive_line']]
        
        if not rbs or len(ol_players) < 3:
            return []
        
        chemistry_factors: List[ChemistryFactor] = []
        
        for rb in rbs:
            ol_ids = [p.id for p in ol_players]
            
            factors = {
                'rushing_efficiency': self._calculate_rushing_efficiency(rb.id, season),
                'yards_after_contact': self._calculate_yac_performance(rb.id, season),
                'goal_line_effectiveness': self._calculate_goal_line_success(rb.id, season),
                'pass_protection_help': self._calculate_pass_pro_chemistry(rb.id, ol_ids, season),
                'snap_count_correlation': self._calculate_snap_correlation(rb.id, ol_ids, season)
            }
            
            chemistry_score = np.mean(list(factors.values()))
            
            rb_stats = self.queries.get_recent_player_stats(rb.id, limit=5)
            improvement_trend = self._calculate_improvement_trend(rb_stats)
            
            chemistry_factor = ChemistryFactor(
                factor_type=ChemistryType.RUNNING_BACK_LINE,
                player_id=rb.id,
                partner_ids=ol_ids,
                chemistry_score=chemistry_score,
                confidence=0.7,
                factors=factors,
                improvement_trend=improvement_trend
            )
            
            chemistry_factors.append(chemistry_factor)
        
        return chemistry_factors
    
    def _analyze_coaching_system_fit(self, team_code: TeamCode, players: List[Player], season: Season) -> float:
        """Analyze how well players fit the coaching system"""
        try:
            # Get team news about coaching system
            def get_coaching_news(session):
                from src.database.models import TeamNews
                return session.query(TeamNews).filter(
                    TeamNews.team == team_code,
                    TeamNews.category == 'coaching'
                ).order_by(TeamNews.published_date.desc()).limit(10).all()
            
            coaching_news = self.db_manager.execute_readonly(get_coaching_news)
            
            # Analyze player experience in current system
            system_fit_scores: List[float] = []
            
            for player in players:
                # Calculate time in current system
                years_in_system = min(player.experience_years or 0, 3) / 3.0
                
                # Position-specific system fit
                position_fit = self._calculate_position_system_fit(player.position, team_code)
                
                # Performance trend in system
                recent_stats = self.queries.get_recent_player_stats(player.id, limit=6)
                performance_trend = self._calculate_improvement_trend(recent_stats)
                
                player_fit = (
                    years_in_system * 0.4 +
                    position_fit * 0.4 +
                    max(0, performance_trend) * 0.2
                )
                
                system_fit_scores.append(player_fit)
            
            # Overall coaching system fit
            base_fit = np.mean(system_fit_scores) if system_fit_scores else 0.5
            
            # Adjust based on coaching news sentiment
            if coaching_news:
                news_sentiment = np.mean([news.sentiment_score or 0 for news in coaching_news])
                # Normalize sentiment from -1,1 to 0,1 scale
                sentiment_adjustment = (news_sentiment + 1) / 2
                base_fit = base_fit * 0.8 + sentiment_adjustment * 0.2
            
            return min(max(base_fit, 0.0), 1.0)
            
        except Exception as e:
            self.logger.error(f"Error calculating coaching system fit: {e}")
            return 0.5
    
    def _analyze_leadership_dynamics(self, players: List[Player], season: Season, week: Week) -> List[ChemistryFactor]:
        """Analyze team leadership and veteran presence"""
        # Identify veteran leaders (5+ years experience)
        veterans = [p for p in players if (p.experience_years or 0) >= 5]
        rookies = [p for p in players if (p.experience_years or 0) <= 2]
        
        if not veterans:
            return []
        
        chemistry_factors: List[ChemistryFactor] = []
        
        for veteran in veterans:
            # Calculate leadership factors
            factors = {
                'experience_level': min(veteran.experience_years or 0, 15) / 15.0,
                'positional_leadership': self._calculate_positional_leadership(veteran.position),
                'performance_stability': self._calculate_veteran_stability(veteran.id, season),
                'mentorship_impact': self._calculate_mentorship_impact(veteran.id, rookies, season),
                'team_tenure': self._calculate_team_tenure_impact(veteran.id, season)
            }
            
            chemistry_score = np.mean(list(factors.values()))
            
            # Leadership tends to be stable, so lower improvement volatility
            improvement_trend = 0.02  # Slight positive for veteran leadership
            
            chemistry_factor = ChemistryFactor(
                factor_type=ChemistryType.LEADERSHIP,
                player_id=veteran.id,
                partner_ids=[r.id for r in rookies],
                chemistry_score=chemistry_score,
                confidence=0.65,
                factors=factors,
                improvement_trend=improvement_trend
            )
            
            chemistry_factors.append(chemistry_factor)
        
        return chemistry_factors
    
    def _calculate_position_group_scores(self, chemistry_factors: List[ChemistryFactor]) -> Dict[str, float]:
        """Calculate chemistry scores by position group"""
        group_scores: Dict[str, List[float]] = {}
        
        for factor in chemistry_factors:
            # Map factor type to position group
            if factor.factor_type == ChemistryType.OFFENSIVE_LINE:
                group = 'offensive_line'
            elif factor.factor_type == ChemistryType.QUARTERBACK_RECEIVER:
                group = 'receiving_corps'
            elif factor.factor_type == ChemistryType.RUNNING_BACK_LINE:
                group = 'backfield'
            elif factor.factor_type == ChemistryType.LEADERSHIP:
                group = 'leadership'
            else:
                continue
            
            if group not in group_scores:
                group_scores[group] = []
            group_scores[group].append(factor.chemistry_score)
        
        # Calculate average scores for each group
        return {group: np.mean(scores) for group, scores in group_scores.items()}
    
    def _calculate_overall_chemistry_score(self, chemistry_factors: List[ChemistryFactor], coaching_fit: float) -> float:
        """Calculate weighted overall team chemistry score"""
        if not chemistry_factors:
            return coaching_fit * 0.5  # If no chemistry factors, rely heavily on coaching fit
        
        # Weight scores by chemistry type
        weighted_scores: List[float] = []
        
        for factor in chemistry_factors:
            weight = self.chemistry_weights.get(factor.factor_type, 0.1)
            weighted_scores.append(factor.chemistry_score * weight)
        
        base_chemistry = sum(weighted_scores) / sum(self.chemistry_weights.values())
        
        # Blend with coaching fit
        overall_score = base_chemistry * 0.7 + coaching_fit * 0.3
        
        return min(max(overall_score, 0.0), 1.0)
    
    def _identify_risk_factors(self, chemistry_factors: List[ChemistryFactor], players: List[Player]) -> List[str]:
        """Identify chemistry risk factors"""
        risks: List[str] = []
        
        # Low chemistry scores
        low_chemistry = [f for f in chemistry_factors if f.chemistry_score < 0.4]
        if low_chemistry:
            risks.append(f"Low chemistry in {len(low_chemistry)} position groups")
        
        # Declining trends
        declining = [f for f in chemistry_factors if f.improvement_trend < -0.1]
        if declining:
            risks.append(f"Declining performance trends in {len(declining)} areas")
        
        # Injury-prone key players
        injury_prone = [p for p in players if (p.experience_years or 0) > 2 and self._is_injury_prone(p.id)]
        if injury_prone:
            risks.append(f"{len(injury_prone)} key players with injury concerns")
        
        # Lack of veteran leadership
        veterans = [p for p in players if (p.experience_years or 0) >= 5]
        if len(veterans) < 3:
            risks.append("Limited veteran leadership presence")
        
        return risks[:5]  # Limit to top 5 risks
    
    def _identify_improvement_opportunities(self, chemistry_factors: List[ChemistryFactor], players: List[Player]) -> List[str]:
        """Identify chemistry improvement opportunities"""
        opportunities: List[str] = []
        
        # Improving trends
        improving = [f for f in chemistry_factors if f.improvement_trend > 0.1]
        if improving:
            opportunities.append(f"Strong improvement trends in {len(improving)} areas")
        
        # Young talent development
        young_talent = [p for p in players if 1 <= (p.experience_years or 0) <= 3]
        if len(young_talent) >= 3:
            opportunities.append(f"Developing chemistry with {len(young_talent)} young players")
        
        # High potential partnerships
        high_potential = [f for f in chemistry_factors if f.chemistry_score > 0.7 and f.confidence > 0.7]
        if high_potential:
            opportunities.append(f"Maximize {len(high_potential)} high-chemistry partnerships")
        
        return opportunities[:5]  # Limit to top 5 opportunities
    
    # Helper calculation methods
    def _calculate_games_together(self, player_id: PlayerId, partner_ids: List[PlayerId], season: Season) -> float:
        """Calculate games played together ratio"""
        # Simplified calculation - would need detailed snap count data in production
        return min(season / 2020, 1.0) * 0.8  # Mock calculation
    
    def _calculate_consistency_score(self, stats: List[Any]) -> float:
        """Calculate performance consistency from stats"""
        if not stats or len(stats) < 3:
            return 0.5
        
        fantasy_points = [getattr(stat, 'fantasy_points', 0) for stat in stats]
        if not any(fantasy_points):
            return 0.5
        
        # Calculate coefficient of variation (lower = more consistent)
        mean_fp = np.mean(fantasy_points)
        std_fp = np.std(fantasy_points)
        
        if mean_fp == 0:
            return 0.5
        
        cv = std_fp / mean_fp
        # Convert to consistency score (0-1, higher = more consistent)
        consistency = max(0, 1 - cv)
        return min(consistency, 1.0)
    
    def _calculate_injury_stability(self, player_id: PlayerId, season: Season) -> float:
        """Calculate injury stability score"""
        try:
            def get_injury_history(session):
                from src.database.models import InjuryHistory
                return session.query(InjuryHistory).filter(
                    InjuryHistory.player_id == player_id,
                    InjuryHistory.season >= season - 2
                ).all()
            
            injuries = self.db_manager.execute_readonly(get_injury_history)
            
            if not injuries:
                return 0.8  # Good stability if no recent injuries
            
            # Calculate stability based on injury frequency and severity
            total_games_missed = sum(injury.games_missed for injury in injuries)
            injury_count = len(injuries)
            
            # Lower score for more injuries and games missed
            stability = max(0, 1 - (total_games_missed / 32) - (injury_count * 0.1))
            return min(stability, 1.0)
            
        except Exception:
            return 0.6  # Default moderate stability
    
    def _calculate_snap_stability(self, player_id: PlayerId, season: Season, week: Week) -> float:
        """Calculate snap count stability"""
        try:
            def get_workload_data(session):
                return session.query(WorkloadTracking).filter(
                    WorkloadTracking.player_id == player_id,
                    WorkloadTracking.season == season,
                    WorkloadTracking.week <= week
                ).order_by(WorkloadTracking.week.desc()).limit(6).all()
            
            workload_data = self.db_manager.execute_readonly(get_workload_data)
            
            if not workload_data:
                return 0.5
            
            snap_percentages = [w.snap_percentage for w in workload_data]
            if not snap_percentages:
                return 0.5
            
            # Higher stability for consistent snap counts
            cv = np.std(snap_percentages) / (np.mean(snap_percentages) + 1e-6)
            stability = max(0, 1 - cv)
            return min(stability, 1.0)
            
        except Exception:
            return 0.5
    
    def _calculate_improvement_trend(self, stats: List[Any]) -> float:
        """Calculate performance improvement trend"""
        if not stats or len(stats) < 3:
            return 0.0
        
        fantasy_points = [getattr(stat, 'fantasy_points', 0) for stat in stats]
        if len(fantasy_points) < 3:
            return 0.0
        
        # Simple linear trend calculation
        weeks = list(range(len(fantasy_points)))
        correlation = np.corrcoef(weeks, fantasy_points)[0, 1]
        
        # Convert correlation to trend score (-1 to 1)
        return correlation if not np.isnan(correlation) else 0.0
    
    # Placeholder methods for complex calculations that would need detailed data
    def _calculate_completion_rate(self, qb_id: PlayerId, receiver_id: PlayerId, season: Season) -> float:
        """Calculate QB-receiver completion rate - placeholder"""
        return 0.65 + np.random.normal(0, 0.1)  # Mock data
    
    def _calculate_target_consistency(self, qb_id: PlayerId, receiver_id: PlayerId, season: Season) -> float:
        """Calculate target share consistency - placeholder"""
        return 0.7 + np.random.normal(0, 0.1)  # Mock data
    
    def _calculate_red_zone_chemistry(self, qb_id: PlayerId, receiver_id: PlayerId, season: Season) -> float:
        """Calculate red zone chemistry - placeholder"""
        return 0.6 + np.random.normal(0, 0.15)  # Mock data
    
    def _estimate_route_timing(self, qb_id: PlayerId, receiver_id: PlayerId, season: Season) -> float:
        """Estimate route timing efficiency - placeholder"""
        return 0.75 + np.random.normal(0, 0.1)  # Mock data
    
    def _calculate_pressure_performance(self, qb_id: PlayerId, receiver_id: PlayerId, season: Season) -> float:
        """Calculate performance under pressure - placeholder"""
        return 0.55 + np.random.normal(0, 0.15)  # Mock data
    
    def _calculate_rushing_efficiency(self, rb_id: PlayerId, season: Season) -> float:
        """Calculate rushing efficiency - placeholder"""
        return 0.6 + np.random.normal(0, 0.1)  # Mock data
    
    def _calculate_yac_performance(self, rb_id: PlayerId, season: Season) -> float:
        """Calculate yards after contact - placeholder"""
        return 0.65 + np.random.normal(0, 0.1)  # Mock data
    
    def _calculate_goal_line_success(self, rb_id: PlayerId, season: Season) -> float:
        """Calculate goal line success rate - placeholder"""
        return 0.7 + np.random.normal(0, 0.15)  # Mock data
    
    def _calculate_pass_pro_chemistry(self, rb_id: PlayerId, ol_ids: List[PlayerId], season: Season) -> float:
        """Calculate pass protection chemistry - placeholder"""
        return 0.6 + np.random.normal(0, 0.1)  # Mock data
    
    def _calculate_snap_correlation(self, rb_id: PlayerId, ol_ids: List[PlayerId], season: Season) -> float:
        """Calculate snap count correlation - placeholder"""
        return 0.8 + np.random.normal(0, 0.05)  # Mock data
    
    def _calculate_position_system_fit(self, position: Position, team_code: TeamCode) -> float:
        """Calculate position-specific system fit - placeholder"""
        return 0.7 + np.random.normal(0, 0.1)  # Mock data
    
    def _calculate_positional_leadership(self, position: Position) -> float:
        """Calculate positional leadership value"""
        leadership_values = {
            'QB': 0.9, 'C': 0.8, 'LB': 0.7, 'S': 0.6,
            'TE': 0.5, 'RB': 0.4, 'WR': 0.3
        }
        return leadership_values.get(position, 0.3)
    
    def _calculate_veteran_stability(self, player_id: PlayerId, season: Season) -> float:
        """Calculate veteran player stability - placeholder"""
        return 0.75 + np.random.normal(0, 0.1)  # Mock data
    
    def _calculate_mentorship_impact(self, veteran_id: PlayerId, rookies: List[Player], season: Season) -> float:
        """Calculate mentorship impact - placeholder"""
        return min(len(rookies) * 0.1 + 0.5, 1.0)  # More rookies = more mentorship opportunity
    
    def _calculate_team_tenure_impact(self, player_id: PlayerId, season: Season) -> float:
        """Calculate team tenure impact - placeholder"""
        return 0.6 + np.random.normal(0, 0.1)  # Mock data
    
    def _is_injury_prone(self, player_id: PlayerId) -> bool:
        """Check if player is injury prone - placeholder"""
        return np.random.random() < 0.2  # 20% chance of being injury prone
    
    def _create_default_profile(self, team_code: TeamCode, season: Season, week: Week) -> TeamChemistryProfile:
        """Create default chemistry profile when analysis fails"""
        return TeamChemistryProfile(
            team_code=team_code,
            season=season,
            week=week,
            overall_chemistry_score=0.5,
            position_group_scores={},
            key_partnerships=[],
            risk_factors=["Insufficient data for analysis"],
            improvement_opportunities=["Gather more team chemistry data"],
            coaching_system_fit=0.5
        )


def get_team_chemistry_impact(team_code: TeamCode, season: Season, week: Week) -> Dict[str, float]:
    """Convenience function to get team chemistry impact for predictions"""
    model = TeamChemistryModel()
    profile = model.analyze_team_chemistry(team_code, season, week)
    
    return {
        'overall_chemistry_multiplier': 0.8 + (profile.overall_chemistry_score * 0.4),  # 0.8 to 1.2 range
        'coaching_fit_multiplier': 0.9 + (profile.coaching_system_fit * 0.2),  # 0.9 to 1.1 range
        'risk_penalty': max(0, len(profile.risk_factors) * 0.02),  # Up to 10% penalty
        'chemistry_confidence': profile.overall_chemistry_score
    }


__all__ = [
    'TeamChemistryModel', 'ChemistryFactor', 'TeamChemistryProfile', 'ChemistryType',
    'get_team_chemistry_impact'
]