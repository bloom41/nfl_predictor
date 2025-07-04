#!/usr/bin/env python3
"""
Boom/Bust Analysis System
Advanced probability modeling for boom and bust scenarios like Yahoo Fantasy Plus
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Tuple
from scipy import stats
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score
from sklearn.preprocessing import StandardScaler
from enum import Enum

logger = logging.getLogger(__name__)

class OutcomeType(Enum):
    """Different outcome types for analysis"""
    BOOM = "boom"      # 150%+ of projection
    BUST = "bust"      # 50%- of projection
    NORMAL = "normal"  # Between 50% and 150%

@dataclass
class BoomBustProbability:
    """Boom/bust probability results"""
    player_id: int
    player_name: str
    position: str
    week: int
    
    # Projections
    base_projection: float
    floor_projection: float
    ceiling_projection: float
    
    # Probabilities
    boom_probability: float     # P(score >= 150% of projection)
    bust_probability: float     # P(score <= 50% of projection)
    normal_probability: float   # P(50% < score < 150%)
    
    # Detailed analysis
    volatility_score: float     # 0-1, higher = more volatile
    consistency_score: float    # 0-1, higher = more consistent
    upside_potential: float     # Expected value in boom scenarios
    downside_risk: float        # Expected value in bust scenarios
    
    # Contributing factors
    injury_risk_factor: float
    matchup_factor: float
    usage_stability_factor: float
    weather_factor: float
    game_script_factor: float

@dataclass
class HistoricalOutcome:
    """Historical performance outcome"""
    player_id: int
    week: int
    season: int
    actual_points: float
    projected_points: float
    outcome_type: OutcomeType
    
    # Context factors
    injury_status: Optional[str] = None
    opponent_rank: Optional[int] = None
    home_game: Optional[bool] = None
    weather_conditions: Optional[str] = None

class BoomBustAnalyzer:
    """
    Advanced boom/bust analysis system inspired by Yahoo Fantasy Plus
    Provides detailed probability modeling for player performance ranges
    """
    
    def __init__(self):
        """Initialize boom/bust analyzer"""
        self.logger = logging.getLogger(__name__)
        
        # Historical data for analysis
        self.historical_outcomes: List[HistoricalOutcome] = []
        
        # Position-specific volatility patterns
        self.position_volatility = {
            'QB': 0.35,  # Quarterbacks are generally consistent
            'RB': 0.55,  # Running backs have high volatility
            'WR': 0.50,  # Wide receivers are moderately volatile
            'TE': 0.45   # Tight ends are somewhat volatile
        }
        
        # Machine learning models for outcome prediction
        self.boom_models: Dict[str, RandomForestClassifier] = {}
        self.bust_models: Dict[str, RandomForestClassifier] = {}
        
        # Feature scalers
        self.scalers: Dict[str, StandardScaler] = {}
        
        self.logger.info("Boom/Bust Analyzer initialized")
    
    def analyze_boom_bust_probability(self, player_id: int, player_name: str, position: str,
                                    base_projection: float, week: int,
                                    player_context: Dict[str, Any]) -> BoomBustProbability:
        """
        Analyze boom/bust probabilities for a player
        
        Args:
            player_id: Player identifier
            player_name: Player name
            position: Player position
            base_projection: Base fantasy point projection
            week: Week number
            player_context: Additional context (injury, matchup, etc.)
            
        Returns:
            BoomBustProbability analysis
        """
        try:
            self.logger.debug(f"Analyzing boom/bust for {player_name}")
            
            # Calculate volatility score
            volatility_score = self._calculate_volatility_score(player_id, position, player_context)
            
            # Calculate consistency score
            consistency_score = 1.0 - volatility_score
            
            # Calculate contributing factors
            factors = self._calculate_contributing_factors(player_context, position)
            
            # Calculate probabilities using multiple methods
            boom_prob, bust_prob = self._calculate_probabilities(
                player_id, position, base_projection, volatility_score, factors
            )
            
            normal_prob = max(0.0, 1.0 - boom_prob - bust_prob)
            
            # Calculate floor and ceiling projections
            floor_projection, ceiling_projection = self._calculate_projection_range(
                base_projection, volatility_score, position
            )
            
            # Calculate upside/downside expectations
            upside_potential = ceiling_projection * boom_prob
            downside_risk = floor_projection * bust_prob
            
            return BoomBustProbability(
                player_id=player_id,
                player_name=player_name,
                position=position,
                week=week,
                base_projection=base_projection,
                floor_projection=floor_projection,
                ceiling_projection=ceiling_projection,
                boom_probability=boom_prob,
                bust_probability=bust_prob,
                normal_probability=normal_prob,
                volatility_score=volatility_score,
                consistency_score=consistency_score,
                upside_potential=upside_potential,
                downside_risk=downside_risk,
                injury_risk_factor=factors['injury_risk'],
                matchup_factor=factors['matchup'],
                usage_stability_factor=factors['usage_stability'],
                weather_factor=factors['weather'],
                game_script_factor=factors['game_script']
            )
            
        except Exception as e:
            self.logger.error(f"Error analyzing boom/bust for {player_name}: {e}")
            return self._create_default_analysis(player_id, player_name, position, base_projection, week)
    
    def _calculate_volatility_score(self, player_id: int, position: str, 
                                  context: Dict[str, Any]) -> float:
        """Calculate player volatility score"""
        try:
            # Start with position baseline
            base_volatility = self.position_volatility.get(position, 0.5)
            
            # Adjust based on historical performance if available
            historical_volatility = self._get_historical_volatility(player_id)
            if historical_volatility is not None:
                # Weight historical data more heavily
                base_volatility = (base_volatility * 0.3) + (historical_volatility * 0.7)
            
            # Adjust for contextual factors
            adjustments = 0.0
            
            # Injury status increases volatility
            injury_status = context.get('injury_status', 'healthy')
            if injury_status in ['questionable', 'doubtful']:
                adjustments += 0.15
            elif injury_status == 'probable':
                adjustments += 0.05
            
            # New team/role increases volatility
            if context.get('new_team', False):
                adjustments += 0.10
            
            if context.get('role_change', False):
                adjustments += 0.08
            
            # Weather conditions
            weather_severity = context.get('weather_severity', 'none')
            if weather_severity == 'severe':
                adjustments += 0.12
            elif weather_severity == 'moderate':
                adjustments += 0.06
            
            # Rookie status
            if context.get('rookie', False):
                adjustments += 0.20
            
            # Prime time games (more variance)
            if context.get('prime_time', False):
                adjustments += 0.05
            
            final_volatility = base_volatility + adjustments
            return min(0.9, max(0.1, final_volatility))
            
        except Exception as e:
            self.logger.error(f"Error calculating volatility score: {e}")
            return self.position_volatility.get(position, 0.5)
    
    def _get_historical_volatility(self, player_id: int) -> Optional[float]:
        """Get historical volatility for player"""
        try:
            player_outcomes = [outcome for outcome in self.historical_outcomes 
                             if outcome.player_id == player_id]
            
            if len(player_outcomes) < 5:
                return None
            
            # Calculate coefficient of variation from historical data
            actual_points = [outcome.actual_points for outcome in player_outcomes]
            if len(actual_points) < 5:
                return None
            
            mean_points = np.mean(actual_points)
            std_points = np.std(actual_points)
            
            if mean_points <= 0:
                return None
            
            cv = std_points / mean_points
            
            # Normalize to 0-1 scale (assuming max reasonable CV is 1.5)
            normalized_volatility = min(1.0, cv / 1.5)
            
            return normalized_volatility
            
        except Exception as e:
            self.logger.error(f"Error calculating historical volatility: {e}")
            return None
    
    def _calculate_contributing_factors(self, context: Dict[str, Any], position: str) -> Dict[str, float]:
        """Calculate individual contributing factors"""
        factors = {}
        
        # Injury risk factor
        injury_status = context.get('injury_status', 'healthy')
        injury_risk_map = {
            'healthy': 0.0,
            'probable': 0.2,
            'questionable': 0.5,
            'doubtful': 0.8,
            'out': 1.0
        }
        factors['injury_risk'] = injury_risk_map.get(injury_status, 0.0)
        
        # Matchup factor (easier matchup = lower bust risk, higher boom potential)
        opponent_rank = context.get('opponent_def_rank', 16)
        # Scale 1-32 to -0.5 to +0.5 (lower rank = easier matchup = negative factor)
        factors['matchup'] = (opponent_rank - 16.5) / 32.0
        
        # Usage stability factor
        target_share_change = context.get('target_share_change', 0.0)
        snap_count_change = context.get('snap_count_change', 0.0)
        usage_instability = abs(target_share_change) + abs(snap_count_change)
        factors['usage_stability'] = min(1.0, usage_instability / 0.5)
        
        # Weather factor
        weather_severity = context.get('weather_severity', 'none')
        weather_map = {'none': 0.0, 'mild': 0.1, 'moderate': 0.3, 'severe': 0.6}
        factors['weather'] = weather_map.get(weather_severity, 0.0)
        
        # Game script factor
        team_total = context.get('team_total_vegas', 23.0)
        # Higher team totals favor passing games, lower totals favor running
        if position in ['QB', 'WR', 'TE']:
            # Higher totals are better for passing positions
            factors['game_script'] = max(-0.3, min(0.3, (team_total - 23.0) / 20.0))
        else:  # RB
            # Lower totals (game control) better for RBs
            factors['game_script'] = max(-0.3, min(0.3, (23.0 - team_total) / 20.0))
        
        return factors
    
    def _calculate_probabilities(self, player_id: int, position: str, base_projection: float,
                               volatility_score: float, factors: Dict[str, float]) -> Tuple[float, float]:
        """Calculate boom and bust probabilities"""
        try:
            # Method 1: Statistical approach using normal distribution
            boom_threshold = base_projection * 1.5
            bust_threshold = base_projection * 0.5
            
            # Estimate standard deviation from volatility and position
            estimated_std = base_projection * volatility_score * 0.8
            
            # Use normal distribution to estimate probabilities
            if estimated_std > 0:
                boom_prob_stat = 1 - stats.norm.cdf(boom_threshold, base_projection, estimated_std)
                bust_prob_stat = stats.norm.cdf(bust_threshold, base_projection, estimated_std)
            else:
                boom_prob_stat = 0.1
                bust_prob_stat = 0.1
            
            # Method 2: Factor-based adjustments
            boom_adjustment = 0.0
            bust_adjustment = 0.0
            
            # Injury increases bust risk, decreases boom potential
            injury_impact = factors['injury_risk']
            bust_adjustment += injury_impact * 0.3
            boom_adjustment -= injury_impact * 0.2
            
            # Matchup effects
            matchup_impact = factors['matchup']
            # Easier matchups (negative matchup factor) increase boom, decrease bust
            boom_adjustment -= matchup_impact * 0.15
            bust_adjustment += matchup_impact * 0.15
            
            # Weather impact
            weather_impact = factors['weather']
            bust_adjustment += weather_impact * 0.2
            boom_adjustment -= weather_impact * 0.1
            
            # Usage instability increases both boom and bust risk
            usage_impact = factors['usage_stability']
            boom_adjustment += usage_impact * 0.1
            bust_adjustment += usage_impact * 0.2
            
            # Apply adjustments
            final_boom_prob = max(0.05, min(0.6, boom_prob_stat + boom_adjustment))
            final_bust_prob = max(0.05, min(0.6, bust_prob_stat + bust_adjustment))
            
            # Ensure probabilities are reasonable
            if final_boom_prob + final_bust_prob > 0.8:
                # Scale down proportionally
                scale_factor = 0.8 / (final_boom_prob + final_bust_prob)
                final_boom_prob *= scale_factor
                final_bust_prob *= scale_factor
            
            return final_boom_prob, final_bust_prob
            
        except Exception as e:
            self.logger.error(f"Error calculating probabilities: {e}")
            # Return position-based defaults
            defaults = {
                'QB': (0.25, 0.20),
                'RB': (0.35, 0.30),
                'WR': (0.30, 0.25),
                'TE': (0.25, 0.25)
            }
            return defaults.get(position, (0.25, 0.25))
    
    def _calculate_projection_range(self, base_projection: float, volatility_score: float, 
                                  position: str) -> Tuple[float, float]:
        """Calculate floor and ceiling projections"""
        try:
            # Position-specific multipliers
            position_multipliers = {
                'QB': {'floor': 0.6, 'ceiling': 1.8},
                'RB': {'floor': 0.3, 'ceiling': 2.2},
                'WR': {'floor': 0.4, 'ceiling': 2.0},
                'TE': {'floor': 0.5, 'ceiling': 1.8}
            }
            
            multipliers = position_multipliers.get(position, {'floor': 0.5, 'ceiling': 1.8})
            
            # Adjust based on volatility
            volatility_adjustment = volatility_score * 0.3
            
            floor_multiplier = multipliers['floor'] + volatility_adjustment
            ceiling_multiplier = multipliers['ceiling'] + (volatility_adjustment * 1.5)
            
            floor_projection = base_projection * floor_multiplier
            ceiling_projection = base_projection * ceiling_multiplier
            
            return floor_projection, ceiling_projection
            
        except Exception as e:
            self.logger.error(f"Error calculating projection range: {e}")
            return base_projection * 0.6, base_projection * 1.8
    
    def _create_default_analysis(self, player_id: int, player_name: str, position: str,
                               base_projection: float, week: int) -> BoomBustProbability:
        """Create default analysis when calculation fails"""
        defaults = {
            'QB': {'boom': 0.25, 'bust': 0.20, 'volatility': 0.35},
            'RB': {'boom': 0.35, 'bust': 0.30, 'volatility': 0.55},
            'WR': {'boom': 0.30, 'bust': 0.25, 'volatility': 0.50},
            'TE': {'boom': 0.25, 'bust': 0.25, 'volatility': 0.45}
        }
        
        pos_defaults = defaults.get(position, {'boom': 0.25, 'bust': 0.25, 'volatility': 0.5})
        
        return BoomBustProbability(
            player_id=player_id,
            player_name=player_name,
            position=position,
            week=week,
            base_projection=base_projection,
            floor_projection=base_projection * 0.6,
            ceiling_projection=base_projection * 1.8,
            boom_probability=pos_defaults['boom'],
            bust_probability=pos_defaults['bust'],
            normal_probability=1.0 - pos_defaults['boom'] - pos_defaults['bust'],
            volatility_score=pos_defaults['volatility'],
            consistency_score=1.0 - pos_defaults['volatility'],
            upside_potential=base_projection * 1.8 * pos_defaults['boom'],
            downside_risk=base_projection * 0.6 * pos_defaults['bust'],
            injury_risk_factor=0.0,
            matchup_factor=0.0,
            usage_stability_factor=0.0,
            weather_factor=0.0,
            game_script_factor=0.0
        )
    
    def add_historical_outcome(self, outcome: HistoricalOutcome) -> None:
        """Add historical outcome for analysis"""
        try:
            self.historical_outcomes.append(outcome)
            
            # Keep only recent outcomes (last 1000)
            if len(self.historical_outcomes) > 1000:
                self.historical_outcomes = self.historical_outcomes[-1000:]
                
        except Exception as e:
            self.logger.error(f"Error adding historical outcome: {e}")
    
    def get_player_boom_bust_history(self, player_id: int) -> Dict[str, Any]:
        """Get boom/bust history for a player"""
        try:
            player_outcomes = [outcome for outcome in self.historical_outcomes 
                             if outcome.player_id == player_id]
            
            if not player_outcomes:
                return {'error': 'No historical data available'}
            
            total_games = len(player_outcomes)
            boom_games = len([o for o in player_outcomes if o.outcome_type == OutcomeType.BOOM])
            bust_games = len([o for o in player_outcomes if o.outcome_type == OutcomeType.BUST])
            normal_games = total_games - boom_games - bust_games
            
            return {
                'total_games': total_games,
                'boom_rate': boom_games / total_games,
                'bust_rate': bust_games / total_games,
                'normal_rate': normal_games / total_games,
                'boom_games': boom_games,
                'bust_games': bust_games,
                'normal_games': normal_games,
                'avg_boom_score': np.mean([o.actual_points for o in player_outcomes 
                                         if o.outcome_type == OutcomeType.BOOM]) if boom_games > 0 else 0,
                'avg_bust_score': np.mean([o.actual_points for o in player_outcomes 
                                         if o.outcome_type == OutcomeType.BUST]) if bust_games > 0 else 0
            }
            
        except Exception as e:
            self.logger.error(f"Error getting player history: {e}")
            return {'error': str(e)}

if __name__ == "__main__":
    print("🎯 BOOM/BUST ANALYZER TEST")
    print("=" * 40)
    
    analyzer = BoomBustAnalyzer()
    
    # Test boom/bust analysis
    test_players = [
        (1, "Cooper Kupp", "WR", 18.5),
        (2, "Josh Allen", "QB", 22.3),
        (3, "Christian McCaffrey", "RB", 16.8),
        (4, "Travis Kelce", "TE", 14.2)
    ]
    
    for player_id, player_name, position, projection in test_players:
        print(f"\n📊 Analyzing: {player_name} ({position}) - {projection:.1f} projected")
        print("-" * 50)
        
        # Test with different context scenarios
        contexts = [
            {'injury_status': 'healthy', 'opponent_def_rank': 25, 'weather_severity': 'none'},
            {'injury_status': 'questionable', 'opponent_def_rank': 5, 'weather_severity': 'moderate'}
        ]
        
        for i, context in enumerate(contexts):
            scenario = "Favorable" if i == 0 else "Challenging"
            print(f"\n{scenario} Scenario:")
            
            analysis = analyzer.analyze_boom_bust_probability(
                player_id, player_name, position, projection, 1, context
            )
            
            print(f"  Boom Probability: {analysis.boom_probability:.1%}")
            print(f"  Bust Probability: {analysis.bust_probability:.1%}")
            print(f"  Normal Probability: {analysis.normal_probability:.1%}")
            print(f"  Volatility Score: {analysis.volatility_score:.2f}")
            print(f"  Floor-Ceiling: {analysis.floor_projection:.1f} - {analysis.ceiling_projection:.1f}")
            print(f"  Upside Potential: {analysis.upside_potential:.1f}")
            print(f"  Downside Risk: {analysis.downside_risk:.1f}")
    
    print("\n✅ Boom/Bust Analyzer test completed!")