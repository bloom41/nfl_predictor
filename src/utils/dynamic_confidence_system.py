#!/usr/bin/env python3
"""
Dynamic Confidence Scoring System
Advanced confidence calculations based on data quality, player consistency, and model reliability
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
import statistics
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)

class ConfidenceFactors(Enum):
    """Factors that influence prediction confidence"""
    DATA_QUALITY = "data_quality"
    PLAYER_CONSISTENCY = "player_consistency"
    MODEL_ACCURACY = "model_accuracy"
    SAMPLE_SIZE = "sample_size"
    RECENCY = "recency"
    INJURY_STATUS = "injury_status"
    USAGE_STABILITY = "usage_stability"
    MATCHUP_CLARITY = "matchup_clarity"

@dataclass
class ConfidenceMetrics:
    """Metrics used to calculate confidence scores"""
    # Data quality metrics
    games_with_data: int
    data_completeness: float  # 0-1
    data_source_reliability: float  # 0-1
    
    # Player consistency metrics
    fantasy_point_variance: float
    usage_consistency: float  # 0-1
    
    # Model performance metrics
    historical_accuracy: float  # 0-1
    position_model_strength: float  # 0-1
    recent_model_performance: float  # 0-1
    
    # Optional fields with defaults
    target_consistency: Optional[float] = None
    snap_consistency: Optional[float] = None
    weeks_since_injury: Optional[int] = None
    role_changes_recent: int = 0
    coaching_changes: int = 0

class DynamicConfidenceSystem:
    """
    Advanced confidence scoring system that adapts based on multiple factors
    Follows KISS principle while providing sophisticated analysis
    """
    
    def __init__(self):
        """Initialize the dynamic confidence system"""
        self.logger = logging.getLogger(__name__)
        
        # Confidence factor weights (must sum to 1.0)
        self.factor_weights = {
            ConfidenceFactors.DATA_QUALITY: 0.20,
            ConfidenceFactors.PLAYER_CONSISTENCY: 0.25,
            ConfidenceFactors.MODEL_ACCURACY: 0.20,
            ConfidenceFactors.SAMPLE_SIZE: 0.10,
            ConfidenceFactors.RECENCY: 0.08,
            ConfidenceFactors.INJURY_STATUS: 0.07,
            ConfidenceFactors.USAGE_STABILITY: 0.06,
            ConfidenceFactors.MATCHUP_CLARITY: 0.04
        }
        
        # Position-specific adjustment factors
        self.position_reliability = {
            'QB': 0.85,  # More predictable
            'RB': 0.70,  # Injury/usage dependent
            'WR': 0.75,  # Target dependent
            'TE': 0.72   # Volatile position
        }
        
        # Historical model performance tracking
        self.model_performance_history: Dict[str, List[float]] = {}
        
        self.logger.info("Dynamic Confidence System initialized")
    
    def calculate_prediction_confidence(self, player_id: int, position: str, 
                                      metrics: ConfidenceMetrics,
                                      base_confidence: float = 0.75) -> Tuple[float, Dict[str, float]]:
        """
        Calculate dynamic confidence score for a prediction
        
        Args:
            player_id: Player identifier
            position: Player position
            metrics: Confidence metrics for the player
            base_confidence: Starting confidence level
            
        Returns:
            Tuple of (final_confidence, factor_breakdown)
        """
        try:
            if not (0.0 <= base_confidence <= 1.0):
                raise ValueError(f"Invalid base confidence: {base_confidence}")
            
            self.logger.debug(f"Calculating confidence for player {player_id}")
            
            # Calculate individual factor scores
            factor_scores = {}
            
            factor_scores[ConfidenceFactors.DATA_QUALITY] = self._calculate_data_quality_score(metrics)
            factor_scores[ConfidenceFactors.PLAYER_CONSISTENCY] = self._calculate_consistency_score(metrics)
            factor_scores[ConfidenceFactors.MODEL_ACCURACY] = self._calculate_model_accuracy_score(position, metrics)
            factor_scores[ConfidenceFactors.SAMPLE_SIZE] = self._calculate_sample_size_score(metrics)
            factor_scores[ConfidenceFactors.RECENCY] = self._calculate_recency_score(metrics)
            factor_scores[ConfidenceFactors.INJURY_STATUS] = self._calculate_injury_score(metrics)
            factor_scores[ConfidenceFactors.USAGE_STABILITY] = self._calculate_usage_stability_score(metrics)
            factor_scores[ConfidenceFactors.MATCHUP_CLARITY] = self._calculate_matchup_clarity_score(metrics)
            
            # Calculate weighted confidence score
            weighted_score = sum(
                self.factor_weights[factor] * score 
                for factor, score in factor_scores.items()
            )
            
            # Apply position-specific adjustment
            position_adjustment = self.position_reliability.get(position, 0.75)
            
            # Combine with base confidence
            final_confidence = (base_confidence * 0.4) + (weighted_score * 0.4) + (position_adjustment * 0.2)
            
            # Ensure confidence stays within valid bounds
            final_confidence = max(0.1, min(1.0, final_confidence))
            
            # Create factor breakdown for transparency
            factor_breakdown = {factor.value: score for factor, score in factor_scores.items()}
            factor_breakdown['position_adjustment'] = position_adjustment
            factor_breakdown['base_confidence'] = base_confidence
            
            self.logger.debug(f"Confidence calculated: {final_confidence:.3f}")
            return final_confidence, factor_breakdown
            
        except Exception as e:
            self.logger.error(f"Error calculating confidence for player {player_id}: {e}")
            return base_confidence, {}
    
    def _calculate_data_quality_score(self, metrics: ConfidenceMetrics) -> float:
        """Calculate data quality factor score"""
        try:
            # Combine data completeness and source reliability
            completeness_score = metrics.data_completeness
            reliability_score = metrics.data_source_reliability
            
            # Games with data factor
            games_factor = min(1.0, metrics.games_with_data / 8.0)  # Optimal at 8+ games
            
            return (completeness_score * 0.4 + reliability_score * 0.4 + games_factor * 0.2)
            
        except Exception as e:
            self.logger.warning(f"Error calculating data quality score: {e}")
            return 0.5
    
    def _calculate_consistency_score(self, metrics: ConfidenceMetrics) -> float:
        """Calculate player consistency factor score"""
        try:
            # Fantasy point variance (lower variance = higher consistency)
            if metrics.fantasy_point_variance <= 0:
                variance_score = 1.0
            else:
                # Normalize variance score (assuming typical variance around 25-100)
                variance_score = max(0.0, 1.0 - (metrics.fantasy_point_variance / 100.0))
            
            # Usage consistency
            usage_score = metrics.usage_consistency
            
            # Optional target and snap consistency
            target_score = metrics.target_consistency if metrics.target_consistency else 0.75
            snap_score = metrics.snap_consistency if metrics.snap_consistency else 0.75
            
            return (variance_score * 0.4 + usage_score * 0.3 + target_score * 0.2 + snap_score * 0.1)
            
        except Exception as e:
            self.logger.warning(f"Error calculating consistency score: {e}")
            return 0.5
    
    def _calculate_model_accuracy_score(self, position: str, metrics: ConfidenceMetrics) -> float:
        """Calculate model accuracy factor score"""
        try:
            # Historical model accuracy
            historical_score = metrics.historical_accuracy
            
            # Position-specific model strength
            position_score = metrics.position_model_strength
            
            # Recent performance
            recent_score = metrics.recent_model_performance
            
            # Weight recent performance more heavily
            return (historical_score * 0.3 + position_score * 0.3 + recent_score * 0.4)
            
        except Exception as e:
            self.logger.warning(f"Error calculating model accuracy score: {e}")
            return 0.5
    
    def _calculate_sample_size_score(self, metrics: ConfidenceMetrics) -> float:
        """Calculate sample size adequacy score"""
        try:
            # More games = higher confidence, with diminishing returns
            optimal_games = 10
            sample_score = min(1.0, metrics.games_with_data / optimal_games)
            
            # Apply logarithmic scaling for diminishing returns
            import math
            if metrics.games_with_data > 0:
                sample_score = math.log(metrics.games_with_data + 1) / math.log(optimal_games + 1)
            
            return min(1.0, sample_score)
            
        except Exception as e:
            self.logger.warning(f"Error calculating sample size score: {e}")
            return 0.5
    
    def _calculate_recency_score(self, metrics: ConfidenceMetrics) -> float:
        """Calculate recency factor score (more recent data = higher confidence)"""
        try:
            # This would be based on how recent the training data is
            # For now, assume data is reasonably recent
            return 0.8  # Default to good recency
            
        except Exception as e:
            self.logger.warning(f"Error calculating recency score: {e}")
            return 0.5
    
    def _calculate_injury_score(self, metrics: ConfidenceMetrics) -> float:
        """Calculate injury status factor score"""
        try:
            if metrics.weeks_since_injury is None:
                return 1.0  # No recent injury
            
            weeks_since = metrics.weeks_since_injury
            
            if weeks_since >= 8:
                return 1.0  # Fully recovered
            elif weeks_since >= 4:
                return 0.85  # Mostly recovered
            elif weeks_since >= 2:
                return 0.7   # Recently returned
            else:
                return 0.4   # Very recent injury
                
        except Exception as e:
            self.logger.warning(f"Error calculating injury score: {e}")
            return 0.75
    
    def _calculate_usage_stability_score(self, metrics: ConfidenceMetrics) -> float:
        """Calculate usage stability factor score"""
        try:
            # Recent role changes reduce confidence
            if metrics.role_changes_recent == 0:
                role_score = 1.0
            elif metrics.role_changes_recent == 1:
                role_score = 0.8
            else:
                role_score = 0.6
            
            # Coaching changes can affect usage
            if metrics.coaching_changes == 0:
                coaching_score = 1.0
            else:
                coaching_score = 0.7
            
            return (role_score * 0.7 + coaching_score * 0.3)
            
        except Exception as e:
            self.logger.warning(f"Error calculating usage stability score: {e}")
            return 0.75
    
    def _calculate_matchup_clarity_score(self, metrics: ConfidenceMetrics) -> float:
        """Calculate matchup clarity factor score"""
        try:
            # This would be based on how clear/predictable the matchup is
            # For now, return a reasonable default
            return 0.75
            
        except Exception as e:
            self.logger.warning(f"Error calculating matchup clarity score: {e}")
            return 0.5
    
    def adjust_confidence_for_context(self, base_confidence: float, 
                                    context_factors: Dict[str, Any]) -> float:
        """
        Adjust confidence based on contextual factors
        
        Args:
            base_confidence: Starting confidence level
            context_factors: Additional context (weather, news, etc.)
            
        Returns:
            Adjusted confidence score
        """
        try:
            adjusted_confidence = base_confidence
            
            # Weather impact
            if 'weather_severity' in context_factors:
                severity = context_factors['weather_severity']
                if severity == 'severe':
                    adjusted_confidence *= 0.85
                elif severity == 'moderate':
                    adjusted_confidence *= 0.92
            
            # Recent news impact
            if 'news_impact' in context_factors:
                news_impact = context_factors['news_impact']
                if abs(news_impact) > 1.5:  # Significant news
                    adjusted_confidence *= 0.9
            
            # Last-minute status changes
            if 'status_uncertainty' in context_factors:
                if context_factors['status_uncertainty']:
                    adjusted_confidence *= 0.8
            
            return max(0.1, min(1.0, adjusted_confidence))
            
        except Exception as e:
            self.logger.warning(f"Error adjusting confidence for context: {e}")
            return base_confidence
    
    def get_confidence_explanation(self, factor_breakdown: Dict[str, float]) -> str:
        """Generate human-readable confidence explanation"""
        try:
            lines = []
            lines.append("🎯 CONFIDENCE BREAKDOWN")
            lines.append("-" * 25)
            
            # Sort factors by impact
            sorted_factors = sorted(factor_breakdown.items(), key=lambda x: x[1], reverse=True)
            
            for factor_name, score in sorted_factors:
                if factor_name in ['position_adjustment', 'base_confidence']:
                    continue
                
                # Convert score to grade
                if score >= 0.9:
                    grade = "Excellent"
                elif score >= 0.8:
                    grade = "Good"
                elif score >= 0.7:
                    grade = "Fair"
                elif score >= 0.6:
                    grade = "Poor"
                else:
                    grade = "Very Poor"
                
                lines.append(f"{factor_name.replace('_', ' ').title()}: {grade} ({score:.2f})")
            
            # Key insights
            lines.append("")
            lines.append("💡 KEY INSIGHTS:")
            
            data_quality = factor_breakdown.get('data_quality', 0.5)
            consistency = factor_breakdown.get('player_consistency', 0.5)
            model_accuracy = factor_breakdown.get('model_accuracy', 0.5)
            
            if data_quality >= 0.8:
                lines.append("✅ High-quality data available")
            elif data_quality < 0.6:
                lines.append("⚠️ Limited data quality")
            
            if consistency >= 0.8:
                lines.append("✅ Player shows consistent performance")
            elif consistency < 0.6:
                lines.append("⚠️ Player performance is volatile")
            
            if model_accuracy >= 0.8:
                lines.append("✅ Model performs well for this scenario")
            elif model_accuracy < 0.6:
                lines.append("⚠️ Model uncertainty for this prediction")
            
            return "\n".join(lines)
            
        except Exception as e:
            self.logger.error(f"Error generating confidence explanation: {e}")
            return "Confidence explanation unavailable"
    
    def update_model_performance(self, position: str, actual_accuracy: float) -> None:
        """Update model performance tracking for future confidence calculations"""
        try:
            if position not in self.model_performance_history:
                self.model_performance_history[position] = []
            
            self.model_performance_history[position].append(actual_accuracy)
            
            # Keep only recent performance (last 50 predictions)
            if len(self.model_performance_history[position]) > 50:
                self.model_performance_history[position] = self.model_performance_history[position][-50:]
            
            self.logger.debug(f"Updated model performance for {position}: {actual_accuracy}")
            
        except Exception as e:
            self.logger.error(f"Error updating model performance: {e}")

def create_sample_confidence_metrics(player_id: int, position: str) -> ConfidenceMetrics:
    """Create sample confidence metrics for testing"""
    # Generate realistic sample data based on position
    if position == 'QB':
        return ConfidenceMetrics(
            games_with_data=12,
            data_completeness=0.95,
            data_source_reliability=0.9,
            fantasy_point_variance=35.0,
            usage_consistency=0.85,
            target_consistency=None,
            snap_consistency=0.92,
            historical_accuracy=0.78,
            position_model_strength=0.85,
            recent_model_performance=0.82,
            weeks_since_injury=None,
            role_changes_recent=0,
            coaching_changes=0
        )
    elif position == 'RB':
        return ConfidenceMetrics(
            games_with_data=10,
            data_completeness=0.88,
            data_source_reliability=0.9,
            fantasy_point_variance=55.0,
            usage_consistency=0.72,
            target_consistency=0.68,
            snap_consistency=0.75,
            historical_accuracy=0.72,
            position_model_strength=0.70,
            recent_model_performance=0.74,
            weeks_since_injury=6,
            role_changes_recent=1,
            coaching_changes=0
        )
    else:  # WR/TE
        return ConfidenceMetrics(
            games_with_data=11,
            data_completeness=0.92,
            data_source_reliability=0.9,
            fantasy_point_variance=45.0,
            usage_consistency=0.78,
            target_consistency=0.75,
            snap_consistency=0.82,
            historical_accuracy=0.75,
            position_model_strength=0.75,
            recent_model_performance=0.77,
            weeks_since_injury=None,
            role_changes_recent=0,
            coaching_changes=0
        )

if __name__ == "__main__":
    print("🎯 DYNAMIC CONFIDENCE SYSTEM TEST")
    print("=" * 40)
    
    # Test the confidence system
    confidence_system = DynamicConfidenceSystem()
    
    # Test different player scenarios
    test_players = [
        (1, "QB", "Elite QB with consistent data"),
        (2, "RB", "Injury-prone RB with usage changes"),
        (3, "WR", "Reliable WR with good consistency")
    ]
    
    for player_id, position, description in test_players:
        print(f"\n📊 Testing: {description}")
        print("-" * 30)
        
        # Create sample metrics
        metrics = create_sample_confidence_metrics(player_id, position)
        
        # Calculate confidence
        confidence, breakdown = confidence_system.calculate_prediction_confidence(
            player_id, position, metrics, 0.75
        )
        
        print(f"Final Confidence: {confidence:.1%}")
        print()
        print(confidence_system.get_confidence_explanation(breakdown))
    
    print("\n✅ Dynamic Confidence System test completed!")