"""
Adaptive Prediction System
Integrates coaching adaptation analysis with prediction models for enhanced accuracy
"""
from typing import Dict, List, Optional, Tuple, Any, Union
import numpy as np
import logging
from dataclasses import dataclass

from src.utils.type_hint_utility import PlayerId, Season, Week, TeamCode, Position, FantasyPoints
from src.models.coaching_adaptation_model import CoachingAdaptationModel, get_player_adaptation_impact
from src.models.team_chemistry_model import get_team_chemistry_impact
from src.models.prediction_model import NFLPredictionModel
from src.utils.unified_database_operations import DatabaseSessionManager
from src.database.models import Player


@dataclass
class AdaptivePrediction:
    """Prediction enhanced with coaching adaptation and team chemistry"""
    player_id: PlayerId
    player_name: str
    team: TeamCode
    position: Position
    base_prediction: Dict[str, float]
    chemistry_adjusted_prediction: Dict[str, float]
    adaptation_adjusted_prediction: Dict[str, float]
    final_prediction: Dict[str, float]
    adaptation_factors: Dict[str, float]
    chemistry_factors: Dict[str, float]
    overall_confidence: float
    adaptation_insights: List[str]
    risk_factors: List[str]
    upside_factors: List[str]


class AdaptivePredictionSystem:
    """Complete adaptive prediction system with chemistry and coaching analysis"""
    
    def __init__(self, position: Position = 'QB') -> None:
        self.position: Position = position
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.base_predictor: NFLPredictionModel = NFLPredictionModel(position)
        self.coaching_model: CoachingAdaptationModel = CoachingAdaptationModel()
        self.db_manager: DatabaseSessionManager = DatabaseSessionManager()
        
        # Integration weights for different factors
        self.integration_weights: Dict[str, float] = {
            'base_prediction': 0.5,
            'team_chemistry': 0.25,
            'coaching_adaptation': 0.25
        }
        
        # Position-specific adaptation importance
        self.position_adaptation_importance: Dict[Position, float] = {
            'QB': 0.35,  # QBs most affected by system changes
            'RB': 0.25,  # RBs moderately affected
            'WR': 0.30,  # WRs significantly affected by offensive system
            'TE': 0.28,  # TEs affected by system versatility needs
            'K': 0.10,   # Kickers least affected
            'DEF': 0.20  # Defense moderately affected
        }
    
    def predict_with_full_adaptation(self, player_id: PlayerId, season: Season, week: Week) -> Optional[AdaptivePrediction]:
        """Make comprehensive prediction with all adaptive factors"""
        try:
            # Get base prediction
            base_prediction = self.base_predictor.predict_player_performance(player_id, season, week)
            if not base_prediction:
                self.logger.warning(f"No base prediction available for player {player_id}")
                return None
            
            # Get player info
            player = self._get_player_info(player_id)
            if not player:
                self.logger.warning(f"Player {player_id} not found")
                return None
            
            # Get team chemistry impact
            chemistry_impact = get_team_chemistry_impact(player.team, season, week)
            
            # Get coaching adaptation impact
            adaptation_impact = get_player_adaptation_impact(player_id, season, week)
            
            # Apply chemistry adjustments
            chemistry_adjusted = self._apply_chemistry_adjustments(
                base_prediction['predictions'], chemistry_impact, player.position
            )
            
            # Apply adaptation adjustments
            adaptation_adjusted = self._apply_adaptation_adjustments(
                chemistry_adjusted, adaptation_impact, player.position
            )
            
            # Create final integrated prediction
            final_prediction = self._integrate_all_factors(
                base_prediction['predictions'], chemistry_adjusted, adaptation_adjusted, 
                chemistry_impact, adaptation_impact, player.position
            )
            
            # Calculate enhanced confidence
            overall_confidence = self._calculate_integrated_confidence(
                base_prediction['confidence'], chemistry_impact, adaptation_impact, player.position
            )
            
            # Generate insights and risk factors
            adaptation_insights = self._generate_adaptation_insights(adaptation_impact, player.position)
            risk_factors = self._identify_risk_factors(chemistry_impact, adaptation_impact, player)
            upside_factors = self._identify_upside_factors(chemistry_impact, adaptation_impact, player)
            
            return AdaptivePrediction(
                player_id=player_id,
                player_name=player.name,
                team=player.team,
                position=player.position,
                base_prediction=base_prediction['predictions'],
                chemistry_adjusted_prediction=chemistry_adjusted,
                adaptation_adjusted_prediction=adaptation_adjusted,
                final_prediction=final_prediction,
                adaptation_factors=adaptation_impact,
                chemistry_factors=chemistry_impact,
                overall_confidence=overall_confidence,
                adaptation_insights=adaptation_insights,
                risk_factors=risk_factors,
                upside_factors=upside_factors
            )
            
        except Exception as e:
            self.logger.error(f"Error making adaptive prediction for player {player_id}: {e}")
            return None
    
    def predict_team_adaptive(self, team_code: TeamCode, season: Season, week: Week, 
                             top_n: int = 15) -> List[AdaptivePrediction]:
        """Make adaptive predictions for entire team"""
        try:
            self.logger.info(f"Making adaptive predictions for {team_code}")
            
            # Get team players
            team_players = self.db_manager.safe_find_team_players(team_code)
            if not team_players:
                self.logger.warning(f"No players found for team {team_code}")
                return []
            
            adaptive_predictions: List[AdaptivePrediction] = []
            
            for player in team_players:
                # Filter by position if predictor is position-specific
                if self.position and player.position != self.position:
                    continue
                
                prediction = self.predict_with_full_adaptation(player.id, season, week)
                if prediction:
                    adaptive_predictions.append(prediction)
            
            # Sort by final fantasy points prediction
            adaptive_predictions.sort(
                key=lambda x: x.final_prediction.get('target_fantasy_points', 0),
                reverse=True
            )
            
            return adaptive_predictions[:top_n]
            
        except Exception as e:
            self.logger.error(f"Error making team adaptive predictions for {team_code}: {e}")
            return []
    
    def analyze_adaptation_opportunities(self, team_code: TeamCode, season: Season, week: Week) -> Dict[str, Any]:
        """Analyze team's adaptation opportunities and risks"""
        try:
            # Get team coaching profile
            team_profile = self.coaching_model.analyze_team_coaching_system(team_code, season)
            
            # Get team chemistry impact
            chemistry_impact = get_team_chemistry_impact(team_code, season, week)
            
            # Get team players
            team_players = self.db_manager.safe_find_team_players(team_code)
            
            player_analyses: List[Dict[str, Any]] = []
            
            for player in team_players[:20]:  # Analyze top 20 players
                adaptation_impact = get_player_adaptation_impact(player.id, season, week)
                
                player_analyses.append({
                    'player_id': player.id,
                    'player_name': player.name,
                    'position': player.position,
                    'adaptation_score': adaptation_impact.get('system_fit_score', 0.7),
                    'weeks_to_mastery': adaptation_impact.get('weeks_to_mastery', 8),
                    'performance_impact': adaptation_impact.get('performance_multiplier', 1.0) - 1.0,
                    'adaptation_confidence': adaptation_impact.get('adaptation_confidence', 0.5)
                })
            
            # Sort by adaptation opportunities
            player_analyses.sort(key=lambda x: x['adaptation_score'], reverse=True)
            
            # Identify team-wide patterns
            avg_adaptation = np.mean([p['adaptation_score'] for p in player_analyses])
            adaptation_spread = np.std([p['adaptation_score'] for p in player_analyses])
            
            struggling_players = [p for p in player_analyses if p['adaptation_score'] < 0.5]
            excelling_players = [p for p in player_analyses if p['adaptation_score'] > 0.8]
            
            return {
                'team_adaptation_summary': {
                    'average_adaptation_score': avg_adaptation,
                    'adaptation_consistency': 1.0 - adaptation_spread,  # Lower spread = more consistent
                    'system_stability': team_profile.system_stability,
                    'overall_chemistry': chemistry_impact.get('chemistry_confidence', 0.5)
                },
                'struggling_adaptations': struggling_players[:5],
                'excelling_adaptations': excelling_players[:5],
                'team_opportunities': self._identify_team_opportunities(
                    team_profile, chemistry_impact, player_analyses
                ),
                'team_risks': self._identify_team_risks(
                    team_profile, chemistry_impact, player_analyses
                ),
                'coaching_effectiveness': team_profile.system_effectiveness
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing adaptation opportunities for {team_code}: {e}")
            return {}
    
    def _apply_chemistry_adjustments(self, base_predictions: Dict[str, float], 
                                   chemistry_impact: Dict[str, float], position: Position) -> Dict[str, float]:
        """Apply team chemistry adjustments to predictions"""
        adjusted = base_predictions.copy()
        
        chemistry_multiplier = chemistry_impact.get('overall_chemistry_multiplier', 1.0)
        coaching_multiplier = chemistry_impact.get('coaching_fit_multiplier', 1.0)
        
        # Combine chemistry factors
        overall_chemistry_adjustment = (chemistry_multiplier + coaching_multiplier) / 2
        
        # Apply position-specific adjustments
        if position == 'QB':
            adjusted['target_passing_yards'] *= overall_chemistry_adjustment
            adjusted['target_passing_tds'] *= overall_chemistry_adjustment
            adjusted['target_rushing_yards'] *= (0.5 + overall_chemistry_adjustment * 0.5)
            
        elif position == 'RB':
            adjusted['target_rushing_yards'] *= overall_chemistry_adjustment
            adjusted['target_rushing_tds'] *= overall_chemistry_adjustment
            adjusted['target_receiving_yards'] *= (0.7 + overall_chemistry_adjustment * 0.3)
            
        elif position in ['WR', 'TE']:
            adjusted['target_receiving_yards'] *= overall_chemistry_adjustment
            adjusted['target_receiving_tds'] *= overall_chemistry_adjustment
        
        # Recalculate fantasy points
        adjusted['target_fantasy_points'] = self._calculate_fantasy_points(adjusted)
        
        return adjusted
    
    def _apply_adaptation_adjustments(self, chemistry_adjusted: Dict[str, float], 
                                    adaptation_impact: Dict[str, float], position: Position) -> Dict[str, float]:
        """Apply coaching adaptation adjustments"""
        adjusted = chemistry_adjusted.copy()
        
        performance_multiplier = adaptation_impact.get('performance_multiplier', 1.0)
        consistency_multiplier = adaptation_impact.get('consistency_multiplier', 1.0)
        
        # Get position-specific adaptation importance
        adaptation_importance = self.position_adaptation_importance.get(position, 0.25)
        
        # Blend adaptation impact based on position importance
        effective_performance_multiplier = 1.0 + (performance_multiplier - 1.0) * adaptation_importance
        effective_consistency_multiplier = 1.0 + (consistency_multiplier - 1.0) * adaptation_importance
        
        # Apply to all stats with position-specific emphasis
        if position == 'QB':
            # QBs most affected by system adaptation
            adjusted['target_passing_yards'] *= effective_performance_multiplier
            adjusted['target_passing_tds'] *= effective_performance_multiplier
            adjusted['target_rushing_yards'] *= (0.8 + effective_performance_multiplier * 0.2)
            
        elif position == 'RB':
            # RBs moderately affected, mostly in rushing
            adjusted['target_rushing_yards'] *= effective_performance_multiplier
            adjusted['target_rushing_tds'] *= effective_performance_multiplier
            adjusted['target_receiving_yards'] *= (0.9 + effective_performance_multiplier * 0.1)
            
        elif position in ['WR', 'TE']:
            # Receivers significantly affected by offensive system
            adjusted['target_receiving_yards'] *= effective_performance_multiplier
            adjusted['target_receiving_tds'] *= effective_performance_multiplier
        
        # Apply consistency factor (affects variance, approximated here)
        consistency_adjustment = (effective_consistency_multiplier + 1.0) / 2
        for key in adjusted:
            if key.startswith('target_'):
                adjusted[key] *= consistency_adjustment
        
        # Recalculate fantasy points
        adjusted['target_fantasy_points'] = self._calculate_fantasy_points(adjusted)
        
        return adjusted
    
    def _integrate_all_factors(self, base: Dict[str, float], chemistry: Dict[str, float], 
                             adaptation: Dict[str, float], chemistry_impact: Dict[str, float],
                             adaptation_impact: Dict[str, float], position: Position) -> Dict[str, float]:
        """Create final integrated prediction from all factors"""
        final = {}
        
        # Weight the different prediction approaches
        base_weight = self.integration_weights['base_prediction']
        chemistry_weight = self.integration_weights['team_chemistry']
        adaptation_weight = self.integration_weights['coaching_adaptation']
        
        # Adjust weights based on confidence levels
        chemistry_confidence = chemistry_impact.get('chemistry_confidence', 0.5)
        adaptation_confidence = adaptation_impact.get('adaptation_confidence', 0.5)
        
        # Higher confidence gets more weight
        if chemistry_confidence > 0.7:
            chemistry_weight *= 1.2
        elif chemistry_confidence < 0.4:
            chemistry_weight *= 0.8
            
        if adaptation_confidence > 0.7:
            adaptation_weight *= 1.2
        elif adaptation_confidence < 0.4:
            adaptation_weight *= 0.8
        
        # Normalize weights
        total_weight = base_weight + chemistry_weight + adaptation_weight
        base_weight /= total_weight
        chemistry_weight /= total_weight
        adaptation_weight /= total_weight
        
        # Integrate predictions
        for key in base.keys():
            final[key] = (
                base[key] * base_weight +
                chemistry[key] * chemistry_weight +
                adaptation[key] * adaptation_weight
            )
        
        return final
    
    def _calculate_integrated_confidence(self, base_confidence: float, chemistry_impact: Dict[str, float],
                                       adaptation_impact: Dict[str, float], position: Position) -> float:
        """Calculate integrated confidence from all factors"""
        chemistry_confidence = chemistry_impact.get('chemistry_confidence', 0.5)
        adaptation_confidence = adaptation_impact.get('adaptation_confidence', 0.5)
        
        # Weight confidences
        weights = [0.5, 0.25, 0.25]  # base, chemistry, adaptation
        confidences = [base_confidence, chemistry_confidence, adaptation_confidence]
        
        # Adjust for position-specific importance
        adaptation_importance = self.position_adaptation_importance.get(position, 0.25)
        weights[2] *= (1.0 + adaptation_importance)  # Boost adaptation weight for affected positions
        
        # Normalize weights
        total_weight = sum(weights)
        weights = [w / total_weight for w in weights]
        
        integrated_confidence = sum(w * c for w, c in zip(weights, confidences))
        
        return min(max(integrated_confidence, 0.1), 0.95)
    
    def _generate_adaptation_insights(self, adaptation_impact: Dict[str, float], position: Position) -> List[str]:
        """Generate insights about player's adaptation"""
        insights: List[str] = []
        
        performance_multiplier = adaptation_impact.get('performance_multiplier', 1.0)
        weeks_to_mastery = adaptation_impact.get('weeks_to_mastery', 8)
        system_fit = adaptation_impact.get('system_fit_score', 0.7)
        
        # Performance impact insights
        if performance_multiplier > 1.1:
            insights.append(f"Strong system fit boosting performance by {(performance_multiplier-1)*100:.1f}%")
        elif performance_multiplier < 0.9:
            insights.append(f"System adaptation reducing performance by {(1-performance_multiplier)*100:.1f}%")
        
        # Adaptation timeline insights
        if weeks_to_mastery <= 2:
            insights.append("Already mastered current system")
        elif weeks_to_mastery <= 6:
            insights.append(f"Approaching system mastery ({weeks_to_mastery} weeks)")
        else:
            insights.append(f"Still adapting to system ({weeks_to_mastery} weeks to mastery)")
        
        # System fit insights
        if system_fit > 0.8:
            insights.append(f"Excellent fit for {position} in current system")
        elif system_fit < 0.5:
            insights.append(f"Poor system fit may limit {position} production")
        
        return insights[:4]
    
    def _identify_risk_factors(self, chemistry_impact: Dict[str, float], adaptation_impact: Dict[str, float], 
                             player: Player) -> List[str]:
        """Identify risk factors affecting predictions"""
        risks: List[str] = []
        
        # Chemistry risks
        chemistry_confidence = chemistry_impact.get('chemistry_confidence', 0.5)
        if chemistry_confidence < 0.4:
            risks.append("Poor team chemistry may impact performance")
        
        # Adaptation risks
        performance_multiplier = adaptation_impact.get('performance_multiplier', 1.0)
        if performance_multiplier < 0.85:
            risks.append("Coaching system adaptation struggles")
        
        weeks_to_mastery = adaptation_impact.get('weeks_to_mastery', 8)
        if weeks_to_mastery > 12:
            risks.append("Extended adaptation period expected")
        
        # Age-related adaptation risks
        if player.age and player.age > 30:
            adaptation_confidence = adaptation_impact.get('adaptation_confidence', 0.5)
            if adaptation_confidence < 0.6:
                risks.append("Age may slow system adaptation")
        
        return risks[:3]
    
    def _identify_upside_factors(self, chemistry_impact: Dict[str, float], adaptation_impact: Dict[str, float], 
                               player: Player) -> List[str]:
        """Identify upside factors boosting predictions"""
        upside: List[str] = []
        
        # Chemistry upside
        chemistry_confidence = chemistry_impact.get('chemistry_confidence', 0.5)
        if chemistry_confidence > 0.7:
            upside.append("Strong team chemistry provides performance boost")
        
        # Adaptation upside
        performance_multiplier = adaptation_impact.get('performance_multiplier', 1.0)
        if performance_multiplier > 1.1:
            upside.append("Excellent system fit enhances production")
        
        weeks_to_mastery = adaptation_impact.get('weeks_to_mastery', 8)
        if weeks_to_mastery <= 4:
            upside.append("Mastering system, peak performance expected")
        
        # Experience upside
        if player.experience_years and player.experience_years >= 5:
            adaptation_confidence = adaptation_impact.get('adaptation_confidence', 0.5)
            if adaptation_confidence > 0.7:
                upside.append("Veteran experience aids system mastery")
        
        return upside[:3]
    
    def _identify_team_opportunities(self, team_profile, chemistry_impact: Dict[str, float], 
                                   player_analyses: List[Dict[str, Any]]) -> List[str]:
        """Identify team-wide adaptation opportunities"""
        opportunities: List[str] = []
        
        avg_adaptation = np.mean([p['adaptation_score'] for p in player_analyses])
        if avg_adaptation > 0.7:
            opportunities.append("Strong overall system adaptation across roster")
        
        improving_players = [p for p in player_analyses if p['weeks_to_mastery'] <= 4]
        if len(improving_players) >= 3:
            opportunities.append(f"{len(improving_players)} players approaching system mastery")
        
        if team_profile.system_stability > 0.8:
            opportunities.append("Stable coaching system allows for continued development")
        
        return opportunities[:3]
    
    def _identify_team_risks(self, team_profile, chemistry_impact: Dict[str, float], 
                           player_analyses: List[Dict[str, Any]]) -> List[str]:
        """Identify team-wide adaptation risks"""
        risks: List[str] = []
        
        struggling_count = len([p for p in player_analyses if p['adaptation_score'] < 0.5])
        if struggling_count >= 3:
            risks.append(f"{struggling_count} players struggling with system adaptation")
        
        if team_profile.system_stability < 0.6:
            risks.append("Low system stability may hinder player development")
        
        long_adaptation_players = [p for p in player_analyses if p['weeks_to_mastery'] > 12]
        if len(long_adaptation_players) >= 2:
            risks.append(f"{len(long_adaptation_players)} players need extended adaptation time")
        
        return risks[:3]
    
    def _calculate_fantasy_points(self, predictions: Dict[str, float]) -> float:
        """Calculate fantasy points from individual stat predictions"""
        return (
            predictions.get('target_passing_yards', 0) * 0.04 +
            predictions.get('target_passing_tds', 0) * 4 +
            predictions.get('target_rushing_yards', 0) * 0.1 +
            predictions.get('target_rushing_tds', 0) * 6 +
            predictions.get('target_receiving_yards', 0) * 0.1 +
            predictions.get('target_receiving_tds', 0) * 6
        )
    
    def _get_player_info(self, player_id: PlayerId) -> Optional[Player]:
        """Get player information from database"""
        try:
            def get_player(session):
                return session.query(Player).filter(Player.id == player_id).first()
            
            return self.db_manager.execute_readonly(get_player)
        except Exception as e:
            self.logger.error(f"Error getting player info for {player_id}: {e}")
            return None


# Convenience functions
def predict_with_full_adaptation(player_id: PlayerId, season: Season, week: Week, 
                                position: Optional[Position] = None) -> Optional[AdaptivePrediction]:
    """Convenience function for comprehensive adaptive prediction"""
    if not position:
        db_manager = DatabaseSessionManager()
        try:
            def get_player(session):
                return session.query(Player).filter(Player.id == player_id).first()
            
            player = db_manager.execute_readonly(get_player)
            position = player.position if player else 'QB'
        except:
            position = 'QB'
    
    system = AdaptivePredictionSystem(position)
    return system.predict_with_full_adaptation(player_id, season, week)


def analyze_team_adaptation(team_code: TeamCode, season: Season, week: Week) -> Dict[str, Any]:
    """Analyze team's adaptation opportunities and risks"""
    system = AdaptivePredictionSystem()
    return system.analyze_adaptation_opportunities(team_code, season, week)


__all__ = [
    'AdaptivePredictionSystem', 'AdaptivePrediction',
    'predict_with_full_adaptation', 'analyze_team_adaptation'
]