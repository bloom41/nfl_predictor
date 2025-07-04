"""
Chemistry-Enhanced NFL Predictions
Integrates team chemistry analysis with prediction models for improved accuracy
"""
from typing import Dict, List, Optional, Tuple, Any, Union
import numpy as np
import logging
from dataclasses import dataclass

from src.utils.type_hint_utility import PlayerId, Season, Week, TeamCode, Position, FantasyPoints
from src.models.team_chemistry_model import TeamChemistryModel, get_team_chemistry_impact
from src.models.prediction_model import NFLPredictionModel
from src.utils.unified_database_operations import DatabaseSessionManager
from src.database.models import Player


@dataclass
class ChemistryEnhancedPrediction:
    """Prediction enhanced with chemistry analysis"""
    player_id: PlayerId
    player_name: str
    team: TeamCode
    position: Position
    base_prediction: Dict[str, float]
    chemistry_adjusted_prediction: Dict[str, float]
    chemistry_multipliers: Dict[str, float]
    chemistry_confidence: float
    overall_confidence: float
    chemistry_factors: List[str]
    risk_adjustments: List[str]


class ChemistryEnhancedPredictor:
    """Enhanced predictor that incorporates team chemistry analysis"""
    
    def __init__(self, position: Position = 'QB') -> None:
        self.position: Position = position
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.base_predictor: NFLPredictionModel = NFLPredictionModel(position)
        self.chemistry_model: TeamChemistryModel = TeamChemistryModel()
        self.db_manager: DatabaseSessionManager = DatabaseSessionManager()
        
        # Chemistry impact weights by position
        self.position_chemistry_weights: Dict[Position, Dict[str, float]] = {
            'QB': {
                'receiver_chemistry': 0.25,
                'line_protection': 0.20,
                'coaching_fit': 0.20,
                'leadership': 0.15,
                'pressure_handling': 0.10,
                'team_chemistry': 0.10
            },
            'RB': {
                'line_chemistry': 0.30,
                'coaching_fit': 0.25,
                'workload_management': 0.20,
                'team_chemistry': 0.15,
                'leadership': 0.10
            },
            'WR': {
                'qb_chemistry': 0.35,
                'route_chemistry': 0.25,
                'coaching_fit': 0.20,
                'team_chemistry': 0.15,
                'leadership': 0.05
            },
            'TE': {
                'qb_chemistry': 0.30,
                'line_chemistry': 0.25,
                'coaching_fit': 0.20,
                'versatility_fit': 0.15,
                'team_chemistry': 0.10
            }
        }
    
    def predict_with_chemistry(self, player_id: PlayerId, season: Season, week: Week) -> Optional[ChemistryEnhancedPrediction]:
        """Make chemistry-enhanced prediction for a player"""
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
            
            # Get team chemistry analysis
            chemistry_profile = self.chemistry_model.analyze_team_chemistry(player.team, season, week)
            
            # Calculate chemistry multipliers
            chemistry_multipliers = self._calculate_chemistry_multipliers(
                player, chemistry_profile, season, week
            )
            
            # Apply chemistry adjustments
            adjusted_prediction = self._apply_chemistry_adjustments(
                base_prediction['predictions'], chemistry_multipliers, player.position
            )
            
            # Calculate enhanced confidence
            chemistry_confidence = chemistry_profile.overall_chemistry_score
            enhanced_confidence = self._calculate_enhanced_confidence(
                base_prediction['confidence'], chemistry_confidence, chemistry_multipliers
            )
            
            # Identify key chemistry factors
            chemistry_factors = self._identify_key_chemistry_factors(chemistry_profile, player.position)
            
            # Identify risk adjustments
            risk_adjustments = self._identify_risk_adjustments(chemistry_profile, player)
            
            return ChemistryEnhancedPrediction(
                player_id=player_id,
                player_name=player.name,
                team=player.team,
                position=player.position,
                base_prediction=base_prediction['predictions'],
                chemistry_adjusted_prediction=adjusted_prediction,
                chemistry_multipliers=chemistry_multipliers,
                chemistry_confidence=chemistry_confidence,
                overall_confidence=enhanced_confidence,
                chemistry_factors=chemistry_factors,
                risk_adjustments=risk_adjustments
            )
            
        except Exception as e:
            self.logger.error(f"Error making chemistry-enhanced prediction for player {player_id}: {e}")
            return None
    
    def predict_team_with_chemistry(self, team_code: TeamCode, season: Season, week: Week, 
                                  top_n: int = 15) -> List[ChemistryEnhancedPrediction]:
        """Make chemistry-enhanced predictions for entire team"""
        try:
            self.logger.info(f"Making chemistry-enhanced predictions for {team_code}")
            
            # Get team players
            team_players = self.db_manager.safe_find_team_players(team_code)
            if not team_players:
                self.logger.warning(f"No players found for team {team_code}")
                return []
            
            # Get team chemistry analysis once for efficiency
            chemistry_profile = self.chemistry_model.analyze_team_chemistry(team_code, season, week)
            
            enhanced_predictions: List[ChemistryEnhancedPrediction] = []
            
            for player in team_players:
                # Filter by position if predictor is position-specific
                if self.position and player.position != self.position:
                    continue
                
                prediction = self.predict_with_chemistry(player.id, season, week)
                if prediction:
                    enhanced_predictions.append(prediction)
            
            # Sort by chemistry-adjusted fantasy points
            enhanced_predictions.sort(
                key=lambda x: x.chemistry_adjusted_prediction.get('target_fantasy_points', 0),
                reverse=True
            )
            
            return enhanced_predictions[:top_n]
            
        except Exception as e:
            self.logger.error(f"Error making team chemistry predictions for {team_code}: {e}")
            return []
    
    def _calculate_chemistry_multipliers(self, player: Player, chemistry_profile, season: Season, week: Week) -> Dict[str, float]:
        """Calculate position-specific chemistry multipliers"""
        multipliers: Dict[str, float] = {}
        
        # Base multipliers
        multipliers['overall_chemistry'] = 0.8 + (chemistry_profile.overall_chemistry_score * 0.4)
        multipliers['coaching_fit'] = 0.9 + (chemistry_profile.coaching_system_fit * 0.2)
        
        # Position-specific chemistry factors
        if player.position == 'QB':
            multipliers.update(self._calculate_qb_chemistry_multipliers(player, chemistry_profile))
        elif player.position == 'RB':
            multipliers.update(self._calculate_rb_chemistry_multipliers(player, chemistry_profile))
        elif player.position in ['WR', 'TE']:
            multipliers.update(self._calculate_receiver_chemistry_multipliers(player, chemistry_profile))
        else:
            # Default multipliers for other positions
            multipliers['position_chemistry'] = 0.9 + (chemistry_profile.overall_chemistry_score * 0.2)
        
        # Risk penalty
        risk_count = len(chemistry_profile.risk_factors)
        multipliers['risk_penalty'] = max(0.85, 1.0 - (risk_count * 0.03))
        
        return multipliers
    
    def _calculate_qb_chemistry_multipliers(self, qb: Player, chemistry_profile) -> Dict[str, float]:
        """Calculate QB-specific chemistry multipliers"""
        multipliers: Dict[str, float] = {}
        
        # QB-receiver chemistry
        receiving_score = chemistry_profile.position_group_scores.get('receiving_corps', 0.5)
        multipliers['receiver_chemistry'] = 0.85 + (receiving_score * 0.3)
        
        # Protection chemistry (offensive line)
        protection_score = chemistry_profile.position_group_scores.get('offensive_line', 0.5)
        multipliers['protection_chemistry'] = 0.9 + (protection_score * 0.2)
        
        # Leadership impact (QBs benefit significantly from good leadership)
        leadership_score = chemistry_profile.position_group_scores.get('leadership', 0.5)
        multipliers['leadership_impact'] = 0.95 + (leadership_score * 0.1)
        
        return multipliers
    
    def _calculate_rb_chemistry_multipliers(self, rb: Player, chemistry_profile) -> Dict[str, float]:
        """Calculate RB-specific chemistry multipliers"""
        multipliers: Dict[str, float] = {}
        
        # Line chemistry (crucial for RBs)
        line_score = chemistry_profile.position_group_scores.get('offensive_line', 0.5)
        multipliers['line_chemistry'] = 0.8 + (line_score * 0.4)
        
        # Backfield chemistry
        backfield_score = chemistry_profile.position_group_scores.get('backfield', 0.5)
        multipliers['backfield_chemistry'] = 0.9 + (backfield_score * 0.2)
        
        return multipliers
    
    def _calculate_receiver_chemistry_multipliers(self, receiver: Player, chemistry_profile) -> Dict[str, float]:
        """Calculate receiver-specific chemistry multipliers"""
        multipliers: Dict[str, float] = {}
        
        # QB-receiver chemistry (most important for receivers)
        receiving_score = chemistry_profile.position_group_scores.get('receiving_corps', 0.5)
        multipliers['qb_chemistry'] = 0.75 + (receiving_score * 0.5)
        
        # Route running chemistry
        multipliers['route_chemistry'] = 0.85 + (receiving_score * 0.3)
        
        return multipliers
    
    def _apply_chemistry_adjustments(self, base_predictions: Dict[str, float], 
                                   multipliers: Dict[str, float], position: Position) -> Dict[str, float]:
        """Apply chemistry multipliers to base predictions"""
        adjusted_predictions = base_predictions.copy()
        
        # Get position-specific weights
        weights = self.position_chemistry_weights.get(position, {})
        
        # Calculate overall adjustment factor
        overall_adjustment = 1.0
        
        for factor, weight in weights.items():
            if factor in ['receiver_chemistry', 'qb_chemistry']:
                multiplier = multipliers.get('receiver_chemistry', multipliers.get('qb_chemistry', 1.0))
            elif factor in ['line_chemistry', 'line_protection']:
                multiplier = multipliers.get('line_chemistry', multipliers.get('protection_chemistry', 1.0))
            elif factor == 'coaching_fit':
                multiplier = multipliers.get('coaching_fit', 1.0)
            elif factor == 'leadership':
                multiplier = multipliers.get('leadership_impact', 1.0)
            elif factor == 'team_chemistry':
                multiplier = multipliers.get('overall_chemistry', 1.0)
            else:
                multiplier = 1.0
            
            overall_adjustment += (multiplier - 1.0) * weight
        
        # Apply risk penalty
        overall_adjustment *= multipliers.get('risk_penalty', 1.0)
        
        # Apply adjustments to relevant stats
        if position == 'QB':
            adjusted_predictions['target_passing_yards'] = base_predictions.get('target_passing_yards', 0) * overall_adjustment
            adjusted_predictions['target_passing_tds'] = base_predictions.get('target_passing_tds', 0) * overall_adjustment
            # QBs also get some rushing benefit from good chemistry
            rushing_adjustment = 0.7 + (overall_adjustment - 1.0) * 0.3  # Less impact on rushing
            adjusted_predictions['target_rushing_yards'] = base_predictions.get('target_rushing_yards', 0) * rushing_adjustment
            adjusted_predictions['target_rushing_tds'] = base_predictions.get('target_rushing_tds', 0) * rushing_adjustment
            
        elif position == 'RB':
            adjusted_predictions['target_rushing_yards'] = base_predictions.get('target_rushing_yards', 0) * overall_adjustment
            adjusted_predictions['target_rushing_tds'] = base_predictions.get('target_rushing_tds', 0) * overall_adjustment
            # RBs also get receiving benefit from good chemistry
            receiving_adjustment = 0.8 + (overall_adjustment - 1.0) * 0.2
            adjusted_predictions['target_receiving_yards'] = base_predictions.get('target_receiving_yards', 0) * receiving_adjustment
            adjusted_predictions['target_receiving_tds'] = base_predictions.get('target_receiving_tds', 0) * receiving_adjustment
            
        elif position in ['WR', 'TE']:
            adjusted_predictions['target_receiving_yards'] = base_predictions.get('target_receiving_yards', 0) * overall_adjustment
            adjusted_predictions['target_receiving_tds'] = base_predictions.get('target_receiving_tds', 0) * overall_adjustment
            
        # Recalculate fantasy points based on adjusted stats
        adjusted_predictions['target_fantasy_points'] = self._calculate_fantasy_points(adjusted_predictions)
        
        return adjusted_predictions
    
    def _calculate_fantasy_points(self, predictions: Dict[str, float]) -> float:
        """Calculate fantasy points from individual stat predictions"""
        # Standard fantasy scoring
        fantasy_points = (
            predictions.get('target_passing_yards', 0) * 0.04 +  # 1 pt per 25 yards
            predictions.get('target_passing_tds', 0) * 4 +
            predictions.get('target_rushing_yards', 0) * 0.1 +   # 1 pt per 10 yards
            predictions.get('target_rushing_tds', 0) * 6 +
            predictions.get('target_receiving_yards', 0) * 0.1 + # 1 pt per 10 yards
            predictions.get('target_receiving_tds', 0) * 6
        )
        
        return max(0, fantasy_points)
    
    def _calculate_enhanced_confidence(self, base_confidence: float, chemistry_confidence: float, 
                                     multipliers: Dict[str, float]) -> float:
        """Calculate enhanced confidence incorporating chemistry factors"""
        # Base confidence adjustment
        chemistry_boost = (chemistry_confidence - 0.5) * 0.2  # Max ±0.1 adjustment
        
        # Stability from chemistry (more stable chemistry = higher confidence)
        stability_boost = 0
        if chemistry_confidence > 0.7:
            stability_boost = 0.05
        elif chemistry_confidence < 0.3:
            stability_boost = -0.05
        
        # Risk penalty on confidence
        risk_penalty = (1.0 - multipliers.get('risk_penalty', 1.0)) * 0.5
        
        enhanced_confidence = base_confidence + chemistry_boost + stability_boost - risk_penalty
        
        return min(max(enhanced_confidence, 0.1), 0.95)
    
    def _identify_key_chemistry_factors(self, chemistry_profile, position: Position) -> List[str]:
        """Identify key chemistry factors affecting the player"""
        factors: List[str] = []
        
        # Overall chemistry level
        if chemistry_profile.overall_chemistry_score > 0.7:
            factors.append("Strong overall team chemistry")
        elif chemistry_profile.overall_chemistry_score < 0.4:
            factors.append("Weak team chemistry concerns")
        
        # Position-specific factors
        if position == 'QB':
            receiving_score = chemistry_profile.position_group_scores.get('receiving_corps', 0.5)
            if receiving_score > 0.7:
                factors.append("Excellent QB-receiver chemistry")
            elif receiving_score < 0.4:
                factors.append("QB-receiver chemistry concerns")
                
        elif position == 'RB':
            line_score = chemistry_profile.position_group_scores.get('offensive_line', 0.5)
            if line_score > 0.7:
                factors.append("Strong offensive line chemistry")
            elif line_score < 0.4:
                factors.append("Offensive line chemistry issues")
        
        # Coaching system fit
        if chemistry_profile.coaching_system_fit > 0.7:
            factors.append("Strong coaching system fit")
        elif chemistry_profile.coaching_system_fit < 0.4:
            factors.append("Coaching system adaptation needed")
        
        # Key partnerships
        if chemistry_profile.key_partnerships:
            top_partnership = chemistry_profile.key_partnerships[0]
            if top_partnership.chemistry_score > 0.8:
                factors.append(f"Elite {top_partnership.factor_type.value} chemistry")
        
        return factors[:4]  # Limit to top 4 factors
    
    def _identify_risk_adjustments(self, chemistry_profile, player: Player) -> List[str]:
        """Identify risk-based adjustments made to predictions"""
        adjustments: List[str] = []
        
        # Direct risk factors from chemistry analysis
        if len(chemistry_profile.risk_factors) > 2:
            adjustments.append(f"Multiple chemistry risks ({len(chemistry_profile.risk_factors)})")
        
        # Position-specific risks
        if player.position == 'QB' and chemistry_profile.overall_chemistry_score < 0.4:
            adjustments.append("QB performance risk from poor team chemistry")
        
        if player.position == 'RB':
            line_score = chemistry_profile.position_group_scores.get('offensive_line', 0.5)
            if line_score < 0.4:
                adjustments.append("RB production risk from weak line chemistry")
        
        # Opportunity adjustments (positive)
        if len(chemistry_profile.improvement_opportunities) > 2:
            adjustments.append(f"Upside from {len(chemistry_profile.improvement_opportunities)} chemistry improvements")
        
        return adjustments[:3]  # Limit to top 3 adjustments
    
    def _get_player_info(self, player_id: PlayerId) -> Optional[Player]:
        """Get player information from database"""
        try:
            def get_player(session):
                return session.query(Player).filter(Player.id == player_id).first()
            
            return self.db_manager.execute_readonly(get_player)
        except Exception as e:
            self.logger.error(f"Error getting player info for {player_id}: {e}")
            return None


# Convenience functions for easy integration
def predict_player_with_chemistry(player_id: PlayerId, season: Season, week: Week, 
                                position: Optional[Position] = None) -> Optional[ChemistryEnhancedPrediction]:
    """Convenience function for single player chemistry-enhanced prediction"""
    if not position:
        # Try to get position from database
        db_manager = DatabaseSessionManager()
        try:
            def get_player(session):
                return session.query(Player).filter(Player.id == player_id).first()
            
            player = db_manager.execute_readonly(get_player)
            position = player.position if player else 'QB'
        except:
            position = 'QB'  # Default fallback
    
    predictor = ChemistryEnhancedPredictor(position)
    return predictor.predict_with_chemistry(player_id, season, week)


def predict_team_with_chemistry(team_code: TeamCode, season: Season, week: Week, 
                               position: Optional[Position] = None) -> List[ChemistryEnhancedPrediction]:
    """Convenience function for team chemistry-enhanced predictions"""
    predictor = ChemistryEnhancedPredictor(position or 'QB')
    return predictor.predict_team_with_chemistry(team_code, season, week)


__all__ = [
    'ChemistryEnhancedPredictor', 'ChemistryEnhancedPrediction',
    'predict_player_with_chemistry', 'predict_team_with_chemistry'
]