"""
Comprehensive NFL Prediction System
Integrates all advanced modeling components for the most accurate predictions
"""
from typing import Dict, List, Optional, Tuple, Any, Union
import numpy as np
import logging
from dataclasses import dataclass

from src.utils.type_hint_utility import PlayerId, Season, Week, TeamCode, Position, FantasyPoints
from src.models.prediction_model import NFLPredictionModel
from src.models.team_chemistry_model import get_team_chemistry_impact
from src.models.coaching_adaptation_model import get_player_adaptation_impact
from src.models.salary_cap_analysis import SalaryCapAnalyzer
from src.utils.unified_database_operations import DatabaseSessionManager
from src.database.models import Player


@dataclass
class ComprehensivePrediction:
    """Complete prediction with all enhancement factors"""
    player_id: PlayerId
    player_name: str
    team: TeamCode
    position: Position
    
    # Prediction components
    base_prediction: Dict[str, float]
    chemistry_enhanced: Dict[str, float]
    adaptation_enhanced: Dict[str, float]
    contract_enhanced: Dict[str, float]
    final_prediction: Dict[str, float]
    
    # Enhancement factors
    chemistry_factors: Dict[str, float]
    adaptation_factors: Dict[str, float]
    contract_factors: Dict[str, float]
    
    # Confidence and reliability
    base_confidence: float
    enhancement_confidence: float
    overall_confidence: float
    prediction_range: Tuple[float, float]  # Min, max expected fantasy points
    
    # Insights and recommendations
    key_insights: List[str]
    risk_factors: List[str]
    upside_factors: List[str]
    value_assessment: str
    recommendation: str


class ComprehensivePredictionSystem:
    """Complete NFL prediction system with all enhancements"""
    
    def __init__(self, position: Position = 'QB') -> None:
        self.position: Position = position
        self.logger: logging.Logger = logging.getLogger(__name__)
        
        # Initialize all component models
        self.base_predictor: NFLPredictionModel = NFLPredictionModel(position)
        self.salary_analyzer: SalaryCapAnalyzer = SalaryCapAnalyzer()
        self.db_manager: DatabaseSessionManager = DatabaseSessionManager()
        
        # Integration weights (can be tuned based on validation)
        self.component_weights: Dict[str, float] = {
            'base_model': 0.45,      # Strong foundation
            'team_chemistry': 0.20,   # Significant team impact
            'coaching_adaptation': 0.20, # System fit matters
            'contract_motivation': 0.15  # Psychological factors
        }
        
        # Confidence thresholds
        self.confidence_thresholds: Dict[str, float] = {
            'high': 0.75,
            'medium': 0.60,
            'low': 0.45
        }
    
    def predict_comprehensive(self, player_id: PlayerId, season: Season, week: Week) -> Optional[ComprehensivePrediction]:
        """Generate comprehensive prediction with all enhancement factors"""
        try:
            self.logger.info(f"Generating comprehensive prediction for player {player_id}")
            
            # Get base prediction
            base_result = self.base_predictor.predict_player_performance(player_id, season, week)
            if not base_result:
                self.logger.warning(f"No base prediction available for player {player_id}")
                return None
            
            # Get player info
            player = self._get_player_info(player_id)
            if not player:
                self.logger.warning(f"Player {player_id} not found")
                return None
            
            # Get enhancement factors
            chemistry_impact = get_team_chemistry_impact(player.team, season, week)
            adaptation_impact = get_player_adaptation_impact(player_id, season, week)
            contract_impact = self.salary_analyzer.calculate_contract_performance_impact(player_id, season)
            
            # Apply enhancements progressively
            base_prediction = base_result['predictions']
            
            # Apply chemistry enhancement
            chemistry_enhanced = self._apply_chemistry_enhancement(
                base_prediction, chemistry_impact, player.position
            )
            
            # Apply adaptation enhancement
            adaptation_enhanced = self._apply_adaptation_enhancement(
                chemistry_enhanced, adaptation_impact, player.position
            )
            
            # Apply contract enhancement
            contract_enhanced = self._apply_contract_enhancement(
                adaptation_enhanced, contract_impact, player.position
            )
            
            # Create final integrated prediction
            final_prediction = self._create_final_prediction(
                base_prediction, chemistry_enhanced, adaptation_enhanced, contract_enhanced,
                chemistry_impact, adaptation_impact, contract_impact, player.position
            )
            
            # Calculate comprehensive confidence
            base_confidence = base_result['confidence']
            enhancement_confidence = self._calculate_enhancement_confidence(
                chemistry_impact, adaptation_impact, contract_impact
            )
            overall_confidence = self._calculate_overall_confidence(
                base_confidence, enhancement_confidence, player.position
            )
            
            # Calculate prediction range
            prediction_range = self._calculate_prediction_range(
                final_prediction.get('target_fantasy_points', 0), overall_confidence
            )
            
            # Generate insights and recommendations
            insights = self._generate_key_insights(
                player, chemistry_impact, adaptation_impact, contract_impact
            )
            risk_factors = self._identify_comprehensive_risks(
                player, chemistry_impact, adaptation_impact, contract_impact
            )
            upside_factors = self._identify_comprehensive_upside(
                player, chemistry_impact, adaptation_impact, contract_impact
            )
            
            # Value assessment and recommendation
            value_analysis = self.salary_analyzer.analyze_player_value(player_id, season, week)
            value_assessment = value_analysis.value_tier.value if value_analysis else "unknown"
            recommendation = self._generate_recommendation(
                final_prediction, overall_confidence, value_assessment, risk_factors, upside_factors
            )
            
            return ComprehensivePrediction(
                player_id=player_id,
                player_name=player.name,
                team=player.team,
                position=player.position,
                base_prediction=base_prediction,
                chemistry_enhanced=chemistry_enhanced,
                adaptation_enhanced=adaptation_enhanced,
                contract_enhanced=contract_enhanced,
                final_prediction=final_prediction,
                chemistry_factors=chemistry_impact,
                adaptation_factors=adaptation_impact,
                contract_factors=contract_impact,
                base_confidence=base_confidence,
                enhancement_confidence=enhancement_confidence,
                overall_confidence=overall_confidence,
                prediction_range=prediction_range,
                key_insights=insights,
                risk_factors=risk_factors,
                upside_factors=upside_factors,
                value_assessment=value_assessment,
                recommendation=recommendation
            )
            
        except Exception as e:
            self.logger.error(f"Error generating comprehensive prediction for player {player_id}: {e}")
            return None
    
    def predict_team_comprehensive(self, team_code: TeamCode, season: Season, week: Week, 
                                 top_n: int = 15) -> List[ComprehensivePrediction]:
        """Generate comprehensive predictions for entire team"""
        try:
            self.logger.info(f"Generating comprehensive team predictions for {team_code}")
            
            # Get team players
            team_players = self.db_manager.safe_find_team_players(team_code)
            if not team_players:
                self.logger.warning(f"No players found for team {team_code}")
                return []
            
            comprehensive_predictions: List[ComprehensivePrediction] = []
            
            for player in team_players:
                # Filter by position if specified
                if self.position and player.position != self.position:
                    continue
                
                prediction = self.predict_comprehensive(player.id, season, week)
                if prediction:
                    comprehensive_predictions.append(prediction)
            
            # Sort by final fantasy points prediction
            comprehensive_predictions.sort(
                key=lambda x: x.final_prediction.get('target_fantasy_points', 0),
                reverse=True
            )
            
            return comprehensive_predictions[:top_n]
            
        except Exception as e:
            self.logger.error(f"Error generating team comprehensive predictions for {team_code}: {e}")
            return []
    
    def compare_predictions(self, player_ids: List[PlayerId], season: Season, week: Week) -> List[Dict[str, Any]]:
        """Compare comprehensive predictions for multiple players"""
        try:
            comparisons: List[Dict[str, Any]] = []
            
            for player_id in player_ids:
                prediction = self.predict_comprehensive(player_id, season, week)
                if prediction:
                    comparisons.append({
                        'player_id': player_id,
                        'player_name': prediction.player_name,
                        'position': prediction.position,
                        'team': prediction.team,
                        'final_fantasy_points': prediction.final_prediction.get('target_fantasy_points', 0),
                        'confidence': prediction.overall_confidence,
                        'prediction_range': prediction.prediction_range,
                        'value_tier': prediction.value_assessment,
                        'recommendation': prediction.recommendation,
                        'key_insight': prediction.key_insights[0] if prediction.key_insights else "No insights",
                        'primary_risk': prediction.risk_factors[0] if prediction.risk_factors else "No major risks",
                        'primary_upside': prediction.upside_factors[0] if prediction.upside_factors else "Limited upside"
                    })
            
            # Sort by predicted fantasy points
            comparisons.sort(key=lambda x: x['final_fantasy_points'], reverse=True)
            
            return comparisons
            
        except Exception as e:
            self.logger.error(f"Error comparing predictions: {e}")
            return []
    
    def _apply_chemistry_enhancement(self, base_prediction: Dict[str, float], 
                                   chemistry_impact: Dict[str, float], position: Position) -> Dict[str, float]:
        """Apply team chemistry enhancements to predictions"""
        enhanced = base_prediction.copy()
        
        chemistry_multiplier = chemistry_impact.get('overall_chemistry_multiplier', 1.0)
        
        # Position-specific chemistry impact
        if position == 'QB':
            enhanced['target_passing_yards'] *= chemistry_multiplier
            enhanced['target_passing_tds'] *= chemistry_multiplier
            enhanced['target_rushing_yards'] *= (0.7 + chemistry_multiplier * 0.3)
        elif position == 'RB':
            enhanced['target_rushing_yards'] *= chemistry_multiplier
            enhanced['target_rushing_tds'] *= chemistry_multiplier
            enhanced['target_receiving_yards'] *= (0.8 + chemistry_multiplier * 0.2)
        elif position in ['WR', 'TE']:
            enhanced['target_receiving_yards'] *= chemistry_multiplier
            enhanced['target_receiving_tds'] *= chemistry_multiplier
        
        # Recalculate fantasy points
        enhanced['target_fantasy_points'] = self._calculate_fantasy_points(enhanced)
        
        return enhanced
    
    def _apply_adaptation_enhancement(self, chemistry_enhanced: Dict[str, float], 
                                    adaptation_impact: Dict[str, float], position: Position) -> Dict[str, float]:
        """Apply coaching adaptation enhancements"""
        enhanced = chemistry_enhanced.copy()
        
        performance_multiplier = adaptation_impact.get('performance_multiplier', 1.0)
        
        # Apply adaptation impact with position weighting
        for key in enhanced:
            if key.startswith('target_') and key != 'target_fantasy_points':
                enhanced[key] *= performance_multiplier
        
        # Recalculate fantasy points
        enhanced['target_fantasy_points'] = self._calculate_fantasy_points(enhanced)
        
        return enhanced
    
    def _apply_contract_enhancement(self, adaptation_enhanced: Dict[str, float], 
                                  contract_impact: Dict[str, float], position: Position) -> Dict[str, float]:
        """Apply contract motivation enhancements"""
        enhanced = adaptation_enhanced.copy()
        
        motivation_multiplier = contract_impact.get('performance_multiplier', 1.0)
        
        # Apply contract motivation impact
        for key in enhanced:
            if key.startswith('target_') and key != 'target_fantasy_points':
                enhanced[key] *= motivation_multiplier
        
        # Recalculate fantasy points
        enhanced['target_fantasy_points'] = self._calculate_fantasy_points(enhanced)
        
        return enhanced
    
    def _create_final_prediction(self, base: Dict[str, float], chemistry: Dict[str, float],
                               adaptation: Dict[str, float], contract: Dict[str, float],
                               chemistry_impact: Dict[str, float], adaptation_impact: Dict[str, float],
                               contract_impact: Dict[str, float], position: Position) -> Dict[str, float]:
        """Create final weighted prediction from all components"""
        final = {}
        
        # Adjust weights based on confidence in each component
        weights = self.component_weights.copy()
        
        # Boost chemistry weight if high confidence
        if chemistry_impact.get('chemistry_confidence', 0.5) > 0.7:
            weights['team_chemistry'] *= 1.2
        
        # Boost adaptation weight if high confidence
        if adaptation_impact.get('adaptation_confidence', 0.5) > 0.7:
            weights['coaching_adaptation'] *= 1.2
        
        # Normalize weights
        total_weight = sum(weights.values())
        for key in weights:
            weights[key] /= total_weight
        
        # Create weighted combination
        for key in base.keys():
            final[key] = (
                base[key] * weights['base_model'] +
                chemistry[key] * weights['team_chemistry'] +
                adaptation[key] * weights['coaching_adaptation'] +
                contract[key] * weights['contract_motivation']
            )
        
        return final
    
    def _calculate_enhancement_confidence(self, chemistry_impact: Dict[str, float], 
                                        adaptation_impact: Dict[str, float], 
                                        contract_impact: Dict[str, float]) -> float:
        """Calculate confidence in enhancement factors"""
        chemistry_conf = chemistry_impact.get('chemistry_confidence', 0.5)
        adaptation_conf = adaptation_impact.get('adaptation_confidence', 0.5)
        contract_conf = 0.7  # Assume moderate confidence in contract analysis
        
        # Weighted average confidence
        return (chemistry_conf * 0.4 + adaptation_conf * 0.4 + contract_conf * 0.2)
    
    def _calculate_overall_confidence(self, base_confidence: float, enhancement_confidence: float, 
                                    position: Position) -> float:
        """Calculate overall prediction confidence"""
        # Combine base and enhancement confidence
        combined_confidence = base_confidence * 0.6 + enhancement_confidence * 0.4
        
        # Position-specific adjustments (some positions more predictable)
        position_reliability = {
            'QB': 1.0,   # Most predictable
            'RB': 0.85,  # Injury risk
            'WR': 0.9,   # Somewhat predictable
            'TE': 0.88,  # Moderate variability
            'K': 0.95    # Very predictable
        }
        
        reliability_factor = position_reliability.get(position, 0.85)
        
        return min(combined_confidence * reliability_factor, 0.95)
    
    def _calculate_prediction_range(self, predicted_fp: float, confidence: float) -> Tuple[float, float]:
        """Calculate prediction range based on confidence"""
        # Higher confidence = narrower range
        range_factor = 1.0 - confidence  # 0.0 to 1.0
        range_width = predicted_fp * range_factor * 0.5  # Up to 50% range for low confidence
        
        min_fp = max(0, predicted_fp - range_width)
        max_fp = predicted_fp + range_width
        
        return (round(min_fp, 1), round(max_fp, 1))
    
    def _generate_key_insights(self, player: Player, chemistry_impact: Dict[str, float], 
                             adaptation_impact: Dict[str, float], contract_impact: Dict[str, float]) -> List[str]:
        """Generate key insights about the prediction"""
        insights: List[str] = []
        
        # Chemistry insights
        chemistry_conf = chemistry_impact.get('chemistry_confidence', 0.5)
        if chemistry_conf > 0.7:
            insights.append("Strong team chemistry provides significant performance boost")
        elif chemistry_conf < 0.4:
            insights.append("Poor team chemistry may limit upside potential")
        
        # Adaptation insights
        weeks_to_mastery = adaptation_impact.get('weeks_to_mastery', 8)
        if weeks_to_mastery <= 4:
            insights.append("Player mastering coaching system, expect peak performance")
        elif weeks_to_mastery > 12:
            insights.append("Player still adapting to system, performance may improve")
        
        # Contract insights
        motivation_factor = contract_impact.get('motivation_factor', 1.0)
        if motivation_factor > 1.1:
            insights.append("Contract situation provides strong performance motivation")
        elif motivation_factor < 0.95:
            insights.append("Contract security may reduce performance urgency")
        
        # Experience insights
        if player.experience_years and player.experience_years <= 3:
            insights.append("Young player with significant upside potential")
        elif player.experience_years and player.experience_years >= 8:
            insights.append("Veteran experience provides consistency and reliability")
        
        return insights[:4]  # Top 4 insights
    
    def _identify_comprehensive_risks(self, player: Player, chemistry_impact: Dict[str, float], 
                                    adaptation_impact: Dict[str, float], contract_impact: Dict[str, float]) -> List[str]:
        """Identify comprehensive risk factors"""
        risks: List[str] = []
        
        # Team chemistry risks
        if chemistry_impact.get('chemistry_confidence', 0.5) < 0.4:
            risks.append("Team chemistry concerns may impact performance")
        
        # Adaptation risks
        performance_multiplier = adaptation_impact.get('performance_multiplier', 1.0)
        if performance_multiplier < 0.9:
            risks.append("Coaching system adaptation struggles limiting production")
        
        # Contract risks
        if contract_impact.get('motivation_factor', 1.0) < 0.95:
            risks.append("Contract security may reduce competitive edge")
        
        # Age/experience risks
        if player.age and player.age > 30:
            risks.append("Age-related decline risk for veteran player")
        elif player.experience_years and player.experience_years <= 1:
            risks.append("Rookie inconsistency and learning curve")
        
        return risks[:3]  # Top 3 risks
    
    def _identify_comprehensive_upside(self, player: Player, chemistry_impact: Dict[str, float], 
                                     adaptation_impact: Dict[str, float], contract_impact: Dict[str, float]) -> List[str]:
        """Identify comprehensive upside factors"""
        upside: List[str] = []
        
        # Chemistry upside
        if chemistry_impact.get('chemistry_confidence', 0.5) > 0.7:
            upside.append("Excellent team chemistry enhances ceiling")
        
        # Adaptation upside
        performance_multiplier = adaptation_impact.get('performance_multiplier', 1.0)
        if performance_multiplier > 1.1:
            upside.append("Strong system fit provides performance edge")
        
        # Contract upside
        if contract_impact.get('motivation_factor', 1.0) > 1.1:
            upside.append("Contract motivation driving peak performance")
        
        # Age/experience upside
        if player.age and 24 <= player.age <= 28:
            upside.append("Player in prime age range for peak performance")
        elif player.experience_years and 2 <= player.experience_years <= 4:
            upside.append("Second contract motivation with developing skills")
        
        return upside[:3]  # Top 3 upside factors
    
    def _generate_recommendation(self, final_prediction: Dict[str, float], confidence: float, 
                               value_assessment: str, risks: List[str], upside: List[str]) -> str:
        """Generate overall recommendation"""
        fantasy_points = final_prediction.get('target_fantasy_points', 0)
        
        # Base recommendation on performance and confidence
        if fantasy_points >= 20 and confidence >= 0.75:
            base_rec = "STRONG START"
        elif fantasy_points >= 15 and confidence >= 0.65:
            base_rec = "SOLID START"
        elif fantasy_points >= 10 and confidence >= 0.55:
            base_rec = "FLEX OPTION"
        elif fantasy_points >= 8:
            base_rec = "DEEP LEAGUE PLAY"
        else:
            base_rec = "AVOID"
        
        # Adjust for value
        if value_assessment in ['elite_value', 'good_value']:
            if base_rec in ["FLEX OPTION", "DEEP LEAGUE PLAY"]:
                base_rec = "VALUE PLAY"
        elif value_assessment in ['poor_value', 'terrible_value']:
            if base_rec in ["STRONG START", "SOLID START"]:
                base_rec += " (EXPENSIVE)"
        
        # Adjust for risks and upside
        if len(upside) > len(risks):
            base_rec += " (UPSIDE)"
        elif len(risks) > len(upside):
            base_rec += " (RISKY)"
        
        return base_rec
    
    def _calculate_fantasy_points(self, predictions: Dict[str, float]) -> float:
        """Calculate fantasy points from stat predictions"""
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


# Convenience functions for easy access
def predict_player_comprehensive(player_id: PlayerId, season: Season, week: Week, 
                               position: Optional[Position] = None) -> Optional[ComprehensivePrediction]:
    """Generate comprehensive prediction for a single player"""
    if not position:
        db_manager = DatabaseSessionManager()
        try:
            def get_player(session):
                return session.query(Player).filter(Player.id == player_id).first()
            
            player = db_manager.execute_readonly(get_player)
            position = player.position if player else 'QB'
        except:
            position = 'QB'
    
    system = ComprehensivePredictionSystem(position)
    return system.predict_comprehensive(player_id, season, week)


def compare_players_comprehensive(player_ids: List[PlayerId], season: Season, week: Week) -> List[Dict[str, Any]]:
    """Compare comprehensive predictions for multiple players"""
    system = ComprehensivePredictionSystem()
    return system.compare_predictions(player_ids, season, week)


__all__ = [
    'ComprehensivePredictionSystem', 'ComprehensivePrediction',
    'predict_player_comprehensive', 'compare_players_comprehensive'
]