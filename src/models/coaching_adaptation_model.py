"""
Coaching System Adaptation Analysis
Analyzes how players adapt to coaching systems and predicts performance impacts
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
from src.database.models import Player, PlayerStats, TeamNews, TransactionLog


class CoachingSystemType(Enum):
    """Types of coaching systems"""
    WEST_COAST = "west_coast"
    AIR_RAID = "air_raid"
    SPREAD = "spread"
    POWER_RUN = "power_run"
    ZONE_BLOCKING = "zone_blocking"
    VERTICAL_PASSING = "vertical_passing"
    SHORT_PASSING = "short_passing"
    BALANCED = "balanced"
    DEFENSIVE_MINDED = "defensive_minded"
    INNOVATIVE = "innovative"


class AdaptationPhase(Enum):
    """Player adaptation phases to new systems"""
    LEARNING = "learning"          # First 4-6 games
    ADJUSTING = "adjusting"        # Games 7-12
    ADAPTING = "adapting"          # Games 13-16
    MASTERED = "mastered"          # Full season+
    STRUGGLING = "struggling"       # Poor adaptation


@dataclass
class CoachingChange:
    """Information about coaching changes"""
    team_code: TeamCode
    season: Season
    change_type: str  # "head_coach", "offensive_coordinator", "position_coach"
    new_system_type: CoachingSystemType
    previous_system_type: Optional[CoachingSystemType]
    change_date: datetime
    impact_magnitude: float  # 0.0-1.0 scale


@dataclass
class PlayerAdaptationProfile:
    """Player's adaptation profile to coaching systems"""
    player_id: PlayerId
    current_system_type: CoachingSystemType
    adaptation_phase: AdaptationPhase
    adaptation_score: float  # 0.0-1.0 scale
    system_tenure: int  # Games in current system
    adaptation_trend: float  # Positive = improving adaptation
    system_fit_factors: Dict[str, float]
    historical_adaptations: List[Dict[str, Any]]
    predicted_peak_performance: float
    confidence: float


@dataclass
class TeamCoachingProfile:
    """Team's overall coaching system profile"""
    team_code: TeamCode
    season: Season
    head_coach_system: CoachingSystemType
    offensive_system: CoachingSystemType
    system_stability: float  # How stable the system has been
    player_adaptation_scores: Dict[PlayerId, float]
    system_effectiveness: float
    recent_changes: List[CoachingChange]


class CoachingAdaptationModel:
    """Model for analyzing coaching system adaptation"""
    
    def __init__(self) -> None:
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.db_manager: DatabaseSessionManager = DatabaseSessionManager()
        self.queries: CommonQueries = CommonQueries()
        
        # System characteristics by position
        self.position_system_affinity: Dict[Position, Dict[CoachingSystemType, float]] = {
            'QB': {
                CoachingSystemType.WEST_COAST: 0.9,
                CoachingSystemType.AIR_RAID: 0.95,
                CoachingSystemType.SPREAD: 0.8,
                CoachingSystemType.VERTICAL_PASSING: 0.85,
                CoachingSystemType.SHORT_PASSING: 0.9,
                CoachingSystemType.BALANCED: 0.8,
                CoachingSystemType.POWER_RUN: 0.6,
                CoachingSystemType.ZONE_BLOCKING: 0.7
            },
            'RB': {
                CoachingSystemType.POWER_RUN: 0.95,
                CoachingSystemType.ZONE_BLOCKING: 0.9,
                CoachingSystemType.BALANCED: 0.85,
                CoachingSystemType.WEST_COAST: 0.7,
                CoachingSystemType.SHORT_PASSING: 0.8,
                CoachingSystemType.SPREAD: 0.75,
                CoachingSystemType.AIR_RAID: 0.6,
                CoachingSystemType.VERTICAL_PASSING: 0.65
            },
            'WR': {
                CoachingSystemType.AIR_RAID: 0.95,
                CoachingSystemType.VERTICAL_PASSING: 0.9,
                CoachingSystemType.WEST_COAST: 0.85,
                CoachingSystemType.SPREAD: 0.9,
                CoachingSystemType.SHORT_PASSING: 0.8,
                CoachingSystemType.BALANCED: 0.8,
                CoachingSystemType.POWER_RUN: 0.5,
                CoachingSystemType.ZONE_BLOCKING: 0.6
            },
            'TE': {
                CoachingSystemType.WEST_COAST: 0.9,
                CoachingSystemType.BALANCED: 0.85,
                CoachingSystemType.POWER_RUN: 0.8,
                CoachingSystemType.SHORT_PASSING: 0.85,
                CoachingSystemType.ZONE_BLOCKING: 0.75,
                CoachingSystemType.VERTICAL_PASSING: 0.7,
                CoachingSystemType.SPREAD: 0.65,
                CoachingSystemType.AIR_RAID: 0.6
            }
        }
        
        # Adaptation timeline factors
        self.adaptation_timeline: Dict[AdaptationPhase, Dict[str, float]] = {
            AdaptationPhase.LEARNING: {
                'performance_modifier': 0.8,  # 20% performance reduction
                'consistency_modifier': 0.7,  # Less consistent
                'confidence_modifier': 0.6,   # Lower confidence
                'duration_games': 6
            },
            AdaptationPhase.ADJUSTING: {
                'performance_modifier': 0.9,  # 10% reduction
                'consistency_modifier': 0.85,
                'confidence_modifier': 0.75,
                'duration_games': 6
            },
            AdaptationPhase.ADAPTING: {
                'performance_modifier': 0.95,  # 5% reduction
                'consistency_modifier': 0.9,
                'confidence_modifier': 0.85,
                'duration_games': 4
            },
            AdaptationPhase.MASTERED: {
                'performance_modifier': 1.0,   # Full performance
                'consistency_modifier': 1.0,
                'confidence_modifier': 0.9,
                'duration_games': float('inf')
            },
            AdaptationPhase.STRUGGLING: {
                'performance_modifier': 0.7,   # Significant reduction
                'consistency_modifier': 0.6,
                'confidence_modifier': 0.5,
                'duration_games': float('inf')
            }
        }
    
    def analyze_player_adaptation(self, player_id: PlayerId, season: Season, week: Week) -> PlayerAdaptationProfile:
        """Analyze a player's adaptation to their current coaching system"""
        try:
            # Get player information
            player = self._get_player_info(player_id)
            if not player:
                return self._create_default_adaptation_profile(player_id)
            
            # Get team coaching information
            team_profile = self.analyze_team_coaching_system(player.team, season)
            
            # Determine current system type
            current_system = self._determine_player_system(player, team_profile)
            
            # Calculate system tenure
            system_tenure = self._calculate_system_tenure(player_id, player.team, season, week)
            
            # Determine adaptation phase
            adaptation_phase = self._determine_adaptation_phase(system_tenure, player_id, season)
            
            # Calculate adaptation score
            adaptation_score = self._calculate_adaptation_score(
                player, current_system, system_tenure, adaptation_phase, season
            )
            
            # Calculate adaptation trend
            adaptation_trend = self._calculate_adaptation_trend(player_id, season, week)
            
            # Analyze system fit factors
            system_fit_factors = self._analyze_system_fit_factors(player, current_system, team_profile)
            
            # Get historical adaptations
            historical_adaptations = self._get_historical_adaptations(player_id)
            
            # Predict peak performance timing
            predicted_peak = self._predict_peak_performance(adaptation_phase, adaptation_trend, adaptation_score)
            
            # Calculate confidence
            confidence = self._calculate_adaptation_confidence(
                adaptation_score, system_tenure, adaptation_trend, len(historical_adaptations)
            )
            
            return PlayerAdaptationProfile(
                player_id=player_id,
                current_system_type=current_system,
                adaptation_phase=adaptation_phase,
                adaptation_score=adaptation_score,
                system_tenure=system_tenure,
                adaptation_trend=adaptation_trend,
                system_fit_factors=system_fit_factors,
                historical_adaptations=historical_adaptations,
                predicted_peak_performance=predicted_peak,
                confidence=confidence
            )
            
        except Exception as e:
            self.logger.error(f"Error analyzing player adaptation for {player_id}: {e}")
            return self._create_default_adaptation_profile(player_id)
    
    def analyze_team_coaching_system(self, team_code: TeamCode, season: Season) -> TeamCoachingProfile:
        """Analyze team's coaching system and stability"""
        try:
            # Get coaching changes
            recent_changes = self._get_recent_coaching_changes(team_code, season)
            
            # Determine current systems
            head_coach_system, offensive_system = self._determine_team_systems(team_code, season, recent_changes)
            
            # Calculate system stability
            system_stability = self._calculate_system_stability(recent_changes, season)
            
            # Get team players and their adaptation scores
            team_players = self.db_manager.safe_find_team_players(team_code)
            player_adaptation_scores: Dict[PlayerId, float] = {}
            
            for player in team_players:
                adaptation_profile = self.analyze_player_adaptation(player.id, season, 1)
                player_adaptation_scores[player.id] = adaptation_profile.adaptation_score
            
            # Calculate overall system effectiveness
            system_effectiveness = self._calculate_system_effectiveness(
                player_adaptation_scores, system_stability, recent_changes
            )
            
            return TeamCoachingProfile(
                team_code=team_code,
                season=season,
                head_coach_system=head_coach_system,
                offensive_system=offensive_system,
                system_stability=system_stability,
                player_adaptation_scores=player_adaptation_scores,
                system_effectiveness=system_effectiveness,
                recent_changes=recent_changes
            )
            
        except Exception as e:
            self.logger.error(f"Error analyzing team coaching system for {team_code}: {e}")
            return self._create_default_team_profile(team_code, season)
    
    def predict_adaptation_impact(self, player_id: PlayerId, season: Season, week: Week) -> Dict[str, float]:
        """Predict how coaching adaptation affects player performance"""
        try:
            adaptation_profile = self.analyze_player_adaptation(player_id, season, week)
            
            # Get base performance modifiers
            phase_modifiers = self.adaptation_timeline[adaptation_profile.adaptation_phase]
            
            # Calculate impact factors
            performance_impact = (
                phase_modifiers['performance_modifier'] * 0.4 +
                adaptation_profile.adaptation_score * 0.6
            )
            
            consistency_impact = (
                phase_modifiers['consistency_modifier'] * 0.3 +
                adaptation_profile.adaptation_score * 0.7
            )
            
            confidence_impact = phase_modifiers['confidence_modifier']
            
            # Apply trend adjustment
            trend_adjustment = adaptation_profile.adaptation_trend * 0.1
            performance_impact = min(1.2, max(0.6, performance_impact + trend_adjustment))
            
            return {
                'performance_multiplier': performance_impact,
                'consistency_multiplier': consistency_impact,
                'confidence_multiplier': confidence_impact,
                'adaptation_confidence': adaptation_profile.confidence,
                'weeks_to_mastery': self._estimate_weeks_to_mastery(adaptation_profile),
                'system_fit_score': adaptation_profile.adaptation_score
            }
            
        except Exception as e:
            self.logger.error(f"Error predicting adaptation impact for {player_id}: {e}")
            return self._get_default_impact()
    
    def analyze_coaching_change_impact(self, team_code: TeamCode, season: Season, 
                                     change_type: str = "head_coach") -> Dict[str, Any]:
        """Analyze the impact of coaching changes on team performance"""
        try:
            # Get recent coaching changes
            changes = self._get_recent_coaching_changes(team_code, season)
            
            if not changes:
                return {'impact_magnitude': 0.0, 'affected_players': [], 'adaptation_timeline': {}}
            
            # Find the specific change
            target_change = None
            for change in changes:
                if change.change_type == change_type:
                    target_change = change
                    break
            
            if not target_change:
                return {'impact_magnitude': 0.0, 'affected_players': [], 'adaptation_timeline': {}}
            
            # Get affected players
            team_players = self.db_manager.safe_find_team_players(team_code)
            affected_players: List[Dict[str, Any]] = []
            
            for player in team_players:
                adaptation_profile = self.analyze_player_adaptation(player.id, season, 1)
                
                # Calculate change impact for this player
                position_affinity = self.position_system_affinity.get(player.position, {})
                old_fit = position_affinity.get(target_change.previous_system_type, 0.7)
                new_fit = position_affinity.get(target_change.new_system_type, 0.7)
                
                fit_change = new_fit - old_fit
                impact_magnitude = abs(fit_change) * target_change.impact_magnitude
                
                affected_players.append({
                    'player_id': player.id,
                    'player_name': player.name,
                    'position': player.position,
                    'fit_change': fit_change,
                    'impact_magnitude': impact_magnitude,
                    'adaptation_phase': adaptation_profile.adaptation_phase.value,
                    'expected_adaptation_weeks': self._estimate_weeks_to_mastery(adaptation_profile)
                })
            
            # Sort by impact magnitude
            affected_players.sort(key=lambda x: abs(x['impact_magnitude']), reverse=True)
            
            # Create adaptation timeline
            adaptation_timeline = self._create_adaptation_timeline(target_change, affected_players)
            
            return {
                'impact_magnitude': target_change.impact_magnitude,
                'affected_players': affected_players[:10],  # Top 10 most affected
                'adaptation_timeline': adaptation_timeline,
                'change_details': {
                    'change_type': target_change.change_type,
                    'new_system': target_change.new_system_type.value,
                    'previous_system': target_change.previous_system_type.value if target_change.previous_system_type else None,
                    'change_date': target_change.change_date.isoformat() if target_change.change_date else None
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing coaching change impact for {team_code}: {e}")
            return {'impact_magnitude': 0.0, 'affected_players': [], 'adaptation_timeline': {}}
    
    # Helper methods for complex calculations
    def _get_player_info(self, player_id: PlayerId) -> Optional[Player]:
        """Get player information"""
        try:
            def get_player(session):
                return session.query(Player).filter(Player.id == player_id).first()
            
            return self.db_manager.execute_readonly(get_player)
        except Exception:
            return None
    
    def _determine_player_system(self, player: Player, team_profile: TeamCoachingProfile) -> CoachingSystemType:
        """Determine which system affects the player most"""
        if player.position in ['QB', 'RB', 'WR', 'TE']:
            return team_profile.offensive_system
        else:
            return team_profile.head_coach_system
    
    def _calculate_system_tenure(self, player_id: PlayerId, team_code: TeamCode, season: Season, week: Week) -> int:
        """Calculate how many games player has been in current system"""
        try:
            # Get transaction history to find when player joined team
            def get_transactions(session):
                return session.query(TransactionLog).filter(
                    TransactionLog.player_id == player_id,
                    TransactionLog.new_team == team_code
                ).order_by(TransactionLog.timestamp.desc()).first()
            
            transaction = self.db_manager.execute_readonly(get_transactions)
            
            if transaction:
                # Calculate games since joining team
                games_since_joining = ((season - 2020) * 17) + week  # Approximate
                return min(games_since_joining, 40)  # Cap at reasonable number
            else:
                # Assume player has been with team for a while
                return 20  # Default to veteran status
                
        except Exception:
            return 10  # Default moderate tenure
    
    def _determine_adaptation_phase(self, system_tenure: int, player_id: PlayerId, season: Season) -> AdaptationPhase:
        """Determine current adaptation phase"""
        if system_tenure < 6:
            return AdaptationPhase.LEARNING
        elif system_tenure < 12:
            return AdaptationPhase.ADJUSTING
        elif system_tenure < 16:
            return AdaptationPhase.ADAPTING
        else:
            # Check if player is struggling based on recent performance
            recent_stats = self.queries.get_recent_player_stats(player_id, limit=4)
            if recent_stats and len(recent_stats) >= 3:
                fantasy_points = [getattr(stat, 'fantasy_points', 0) for stat in recent_stats]
                avg_performance = np.mean(fantasy_points)
                if avg_performance < 5:  # Struggling threshold
                    return AdaptationPhase.STRUGGLING
            
            return AdaptationPhase.MASTERED
    
    def _calculate_adaptation_score(self, player: Player, system_type: CoachingSystemType, 
                                  tenure: int, phase: AdaptationPhase, season: Season) -> float:
        """Calculate player's adaptation score to current system"""
        # Base system fit
        position_affinity = self.position_system_affinity.get(player.position, {})
        base_fit = position_affinity.get(system_type, 0.7)
        
        # Tenure adjustment
        tenure_modifier = min(tenure / 16, 1.0)  # Reaches 1.0 at 16 games
        
        # Phase modifier
        phase_modifier = self.adaptation_timeline[phase]['performance_modifier']
        
        # Experience adjustment
        experience_years = player.experience_years or 1
        experience_modifier = min(1.0 + (experience_years - 1) * 0.02, 1.2)  # Up to 20% boost for veterans
        
        adaptation_score = base_fit * tenure_modifier * phase_modifier * experience_modifier
        
        return min(max(adaptation_score, 0.0), 1.0)
    
    def _calculate_adaptation_trend(self, player_id: PlayerId, season: Season, week: Week) -> float:
        """Calculate adaptation trend (positive = improving)"""
        try:
            recent_stats = self.queries.get_recent_player_stats(player_id, limit=6)
            if not recent_stats or len(recent_stats) < 3:
                return 0.0
            
            fantasy_points = [getattr(stat, 'fantasy_points', 0) for stat in recent_stats]
            
            # Calculate linear trend
            weeks = list(range(len(fantasy_points)))
            correlation = np.corrcoef(weeks, fantasy_points)[0, 1]
            
            return correlation if not np.isnan(correlation) else 0.0
            
        except Exception:
            return 0.0
    
    def _analyze_system_fit_factors(self, player: Player, system_type: CoachingSystemType, 
                                  team_profile: TeamCoachingProfile) -> Dict[str, float]:
        """Analyze specific factors affecting system fit"""
        factors: Dict[str, float] = {}
        
        # Position-specific system affinity
        position_affinity = self.position_system_affinity.get(player.position, {})
        factors['position_fit'] = position_affinity.get(system_type, 0.7)
        
        # Experience factor
        experience_years = player.experience_years or 1
        factors['experience_advantage'] = min(experience_years / 10, 1.0)
        
        # System stability factor
        factors['system_stability'] = team_profile.system_stability
        
        # Age factor (prime years vs. learning ability)
        if player.age:
            if 24 <= player.age <= 29:
                factors['age_adaptability'] = 1.0  # Prime years
            elif player.age < 24:
                factors['age_adaptability'] = 0.9  # Young, still learning
            else:
                factors['age_adaptability'] = max(0.6, 1.0 - (player.age - 29) * 0.05)  # Declining adaptability
        else:
            factors['age_adaptability'] = 0.8  # Default
        
        return factors
    
    def _get_historical_adaptations(self, player_id: PlayerId) -> List[Dict[str, Any]]:
        """Get player's history of system adaptations"""
        try:
            # Get transaction history showing team changes
            def get_transaction_history(session):
                return session.query(TransactionLog).filter(
                    TransactionLog.player_id == player_id
                ).order_by(TransactionLog.timestamp.desc()).limit(5).all()
            
            transactions = self.db_manager.execute_readonly(get_transaction_history)
            
            adaptations = []
            for transaction in transactions:
                adaptation = {
                    'team': transaction.new_team,
                    'date': transaction.timestamp.isoformat() if transaction.timestamp else None,
                    'type': transaction.transaction_type,
                    'success_estimate': 0.7  # Would need more complex analysis for real data
                }
                adaptations.append(adaptation)
            
            return adaptations
            
        except Exception:
            return []
    
    def _predict_peak_performance(self, phase: AdaptationPhase, trend: float, score: float) -> float:
        """Predict when player will reach peak performance in system"""
        if phase == AdaptationPhase.MASTERED:
            return 1.0
        elif phase == AdaptationPhase.STRUGGLING:
            return 0.6
        else:
            # Calculate based on current progress and trend
            base_potential = score + (trend * 0.3)
            return min(max(base_potential, 0.5), 1.0)
    
    def _calculate_adaptation_confidence(self, score: float, tenure: int, trend: float, 
                                       history_count: int) -> float:
        """Calculate confidence in adaptation analysis"""
        confidence = 0.5  # Base confidence
        
        # Higher confidence with more tenure data
        confidence += min(tenure / 20, 0.2)
        
        # Higher confidence with clear trends
        confidence += abs(trend) * 0.1
        
        # Higher confidence with adaptation history
        confidence += min(history_count * 0.05, 0.15)
        
        # Lower confidence for edge cases
        if score < 0.3 or score > 0.9:
            confidence -= 0.1
        
        return min(max(confidence, 0.2), 0.9)
    
    def _get_recent_coaching_changes(self, team_code: TeamCode, season: Season) -> List[CoachingChange]:
        """Get recent coaching changes for team - placeholder"""
        # This would analyze team news and transaction logs for coaching changes
        # For now, return mock data
        return []
    
    def _determine_team_systems(self, team_code: TeamCode, season: Season, 
                               changes: List[CoachingChange]) -> Tuple[CoachingSystemType, CoachingSystemType]:
        """Determine team's coaching systems - placeholder"""
        # This would analyze team characteristics and coaching staff
        # For now, return balanced systems
        return CoachingSystemType.BALANCED, CoachingSystemType.BALANCED
    
    def _calculate_system_stability(self, changes: List[CoachingChange], season: Season) -> float:
        """Calculate system stability score"""
        if not changes:
            return 0.9  # High stability if no recent changes
        
        # Reduce stability based on recency and magnitude of changes
        stability = 1.0
        for change in changes:
            recency_factor = max(0, 1.0 - (season - 2020) * 0.1)  # More impact for recent changes
            stability -= change.impact_magnitude * recency_factor * 0.3
        
        return max(stability, 0.1)
    
    def _calculate_system_effectiveness(self, player_scores: Dict[PlayerId, float], 
                                      stability: float, changes: List[CoachingChange]) -> float:
        """Calculate overall system effectiveness"""
        if not player_scores:
            return 0.5
        
        avg_adaptation = np.mean(list(player_scores.values()))
        effectiveness = avg_adaptation * 0.7 + stability * 0.3
        
        return min(max(effectiveness, 0.0), 1.0)
    
    def _estimate_weeks_to_mastery(self, profile: PlayerAdaptationProfile) -> int:
        """Estimate weeks until player masters the system"""
        if profile.adaptation_phase == AdaptationPhase.MASTERED:
            return 0
        elif profile.adaptation_phase == AdaptationPhase.STRUGGLING:
            return 20  # Long road ahead
        else:
            base_weeks = {
                AdaptationPhase.LEARNING: 12,
                AdaptationPhase.ADJUSTING: 8,
                AdaptationPhase.ADAPTING: 4
            }
            
            weeks = base_weeks.get(profile.adaptation_phase, 8)
            
            # Adjust based on trend
            if profile.adaptation_trend > 0:
                weeks = int(weeks * 0.8)  # Faster if improving
            elif profile.adaptation_trend < -0.1:
                weeks = int(weeks * 1.3)  # Slower if declining
            
            return max(weeks, 1)
    
    def _create_adaptation_timeline(self, change: CoachingChange, players: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create timeline for team adaptation to coaching change"""
        timeline = {
            'immediate_impact': 'First 4 weeks: Learning new system, reduced performance',
            'adjustment_period': 'Weeks 5-10: Players adjust, inconsistent performance',
            'stabilization': 'Weeks 11-16: System stabilizes, performance normalizes',
            'mastery': 'Season 2+: Full mastery of system, optimal performance'
        }
        
        return timeline
    
    def _get_default_impact(self) -> Dict[str, float]:
        """Get default adaptation impact values"""
        return {
            'performance_multiplier': 1.0,
            'consistency_multiplier': 1.0,
            'confidence_multiplier': 0.8,
            'adaptation_confidence': 0.5,
            'weeks_to_mastery': 8,
            'system_fit_score': 0.7
        }
    
    def _create_default_adaptation_profile(self, player_id: PlayerId) -> PlayerAdaptationProfile:
        """Create default adaptation profile when analysis fails"""
        return PlayerAdaptationProfile(
            player_id=player_id,
            current_system_type=CoachingSystemType.BALANCED,
            adaptation_phase=AdaptationPhase.ADAPTING,
            adaptation_score=0.7,
            system_tenure=10,
            adaptation_trend=0.0,
            system_fit_factors={'default': 0.7},
            historical_adaptations=[],
            predicted_peak_performance=0.8,
            confidence=0.5
        )
    
    def _create_default_team_profile(self, team_code: TeamCode, season: Season) -> TeamCoachingProfile:
        """Create default team coaching profile"""
        return TeamCoachingProfile(
            team_code=team_code,
            season=season,
            head_coach_system=CoachingSystemType.BALANCED,
            offensive_system=CoachingSystemType.BALANCED,
            system_stability=0.8,
            player_adaptation_scores={},
            system_effectiveness=0.7,
            recent_changes=[]
        )


# Convenience functions
def get_player_adaptation_impact(player_id: PlayerId, season: Season, week: Week) -> Dict[str, float]:
    """Get player's coaching adaptation impact for predictions"""
    model = CoachingAdaptationModel()
    return model.predict_adaptation_impact(player_id, season, week)


def analyze_coaching_change_impact(team_code: TeamCode, season: Season, change_type: str = "head_coach") -> Dict[str, Any]:
    """Analyze the impact of coaching changes"""
    model = CoachingAdaptationModel()
    return model.analyze_coaching_change_impact(team_code, season, change_type)


__all__ = [
    'CoachingAdaptationModel', 'PlayerAdaptationProfile', 'TeamCoachingProfile', 
    'CoachingSystemType', 'AdaptationPhase', 'CoachingChange',
    'get_player_adaptation_impact', 'analyze_coaching_change_impact'
]