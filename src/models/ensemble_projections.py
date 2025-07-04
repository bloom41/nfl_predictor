#!/usr/bin/env python3
"""
Ensemble Projection System
Combines multiple models with weighted historical performance like Yahoo's ATC
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)

class ProjectionSource(Enum):
    """Different projection sources for ensemble"""
    INTERNAL_ML = "internal_ml"
    ENHANCED_PREDICTOR = "enhanced_predictor"
    SIMPLE_PREDICTOR = "simple_predictor"
    HISTORICAL_AVERAGE = "historical_average"
    REGRESSION_MODEL = "regression_model"
    EXPERT_CONSENSUS = "expert_consensus"

@dataclass
class ProjectionResult:
    """Individual projection result"""
    player_id: int
    player_name: str
    position: str
    source: ProjectionSource
    projected_points: float
    confidence: float
    week: int
    season: int
    
    # Additional projection details
    floor: Optional[float] = None
    ceiling: Optional[float] = None
    boom_probability: Optional[float] = None
    bust_probability: Optional[float] = None

@dataclass
class EnsembleProjection:
    """Final ensemble projection result"""
    player_id: int
    player_name: str
    position: str
    week: int
    season: int
    
    # Ensemble results
    consensus_projection: float
    weighted_projection: float
    confidence_score: float
    
    # Projection ranges
    floor_projection: float
    ceiling_projection: float
    boom_probability: float  # Probability of 150%+ of projection
    bust_probability: float  # Probability of 50%- of projection
    
    # Source details
    source_count: int
    source_weights: Dict[str, float]
    individual_projections: List[ProjectionResult]

class EnsembleProjectionSystem:
    """
    Advanced ensemble projection system inspired by Yahoo's ATC methodology
    Combines multiple projection sources with historical performance weighting
    """
    
    def __init__(self):
        """Initialize ensemble projection system"""
        self.logger = logging.getLogger(__name__)
        
        # Historical performance tracking for each source
        self.source_performance: Dict[ProjectionSource, Dict[str, List[float]]] = {}
        
        # Initialize performance tracking
        for source in ProjectionSource:
            self.source_performance[source] = {
                'accuracy_history': [],
                'mae_history': [],
                'position_accuracy': {}
            }
        
        # Default weights (updated based on historical performance)
        self.default_weights = {
            ProjectionSource.ENHANCED_PREDICTOR: 0.30,
            ProjectionSource.INTERNAL_ML: 0.25,
            ProjectionSource.REGRESSION_MODEL: 0.20,
            ProjectionSource.SIMPLE_PREDICTOR: 0.15,
            ProjectionSource.HISTORICAL_AVERAGE: 0.10,
            ProjectionSource.EXPERT_CONSENSUS: 0.00  # Placeholder for future implementation
        }
        
        self.logger.info("Ensemble Projection System initialized")
    
    def generate_ensemble_projection(self, player_id: int, player_name: str, 
                                   position: str, week: int, season: int = 2024) -> EnsembleProjection:
        """
        Generate ensemble projection for a player
        
        Args:
            player_id: Player identifier
            player_name: Player name
            position: Player position
            week: Week number
            season: Season year
            
        Returns:
            EnsembleProjection with weighted consensus
        """
        try:
            # Collect projections from all available sources
            individual_projections = self._collect_individual_projections(
                player_id, player_name, position, week, season
            )
            
            if not individual_projections:
                self.logger.warning(f"No projections available for {player_name}")
                return self._create_fallback_projection(player_id, player_name, position, week, season)
            
            # Calculate dynamic weights based on historical performance
            source_weights = self._calculate_dynamic_weights(position, individual_projections)
            
            # Generate consensus projection
            consensus_projection = self._calculate_consensus_projection(individual_projections)
            
            # Generate weighted projection
            weighted_projection = self._calculate_weighted_projection(
                individual_projections, source_weights
            )
            
            # Calculate confidence score
            confidence_score = self._calculate_ensemble_confidence(
                individual_projections, source_weights
            )
            
            # Calculate floor and ceiling projections
            floor_projection, ceiling_projection = self._calculate_projection_range(
                individual_projections, weighted_projection
            )
            
            # Calculate boom/bust probabilities
            boom_probability, bust_probability = self._calculate_boom_bust_probabilities(
                individual_projections, weighted_projection
            )
            
            ensemble_projection = EnsembleProjection(
                player_id=player_id,
                player_name=player_name,
                position=position,
                week=week,
                season=season,
                consensus_projection=consensus_projection,
                weighted_projection=weighted_projection,
                confidence_score=confidence_score,
                floor_projection=floor_projection,
                ceiling_projection=ceiling_projection,
                boom_probability=boom_probability,
                bust_probability=bust_probability,
                source_count=len(individual_projections),
                source_weights={source.value: weight for source, weight in source_weights.items()},
                individual_projections=individual_projections
            )
            
            self.logger.debug(f"Generated ensemble projection for {player_name}: {weighted_projection:.1f} pts")
            return ensemble_projection
            
        except Exception as e:
            self.logger.error(f"Error generating ensemble projection for {player_name}: {e}")
            return self._create_fallback_projection(player_id, player_name, position, week, season)
    
    def _collect_individual_projections(self, player_id: int, player_name: str, 
                                      position: str, week: int, season: int) -> List[ProjectionResult]:
        """Collect projections from all available sources"""
        projections = []
        
        try:
            # Enhanced Predictor System
            try:
                sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
                from enhanced_predictor_system import EnhancedPredictorSystem
                
                enhanced_predictor = EnhancedPredictorSystem('half_ppr')
                rankings = enhanced_predictor.get_enhanced_rankings(position, season, week, 100)
                
                for ranking in rankings:
                    if getattr(ranking, 'player_name', '') == player_name:
                        projections.append(ProjectionResult(
                            player_id=player_id,
                            player_name=player_name,
                            position=position,
                            source=ProjectionSource.ENHANCED_PREDICTOR,
                            projected_points=getattr(ranking, 'final_prediction', 0),
                            confidence=getattr(ranking, 'confidence', 0.75),
                            week=week,
                            season=season
                        ))
                        break
            except Exception as e:
                self.logger.debug(f"Enhanced predictor not available: {e}")
            
            # Simple Predictor System
            try:
                from src.utils.simple_predictor import SimplePredictor
                
                simple_predictor = SimplePredictor()
                rankings = simple_predictor.get_position_rankings(position, season, week, 100)
                
                for ranking in rankings:
                    if getattr(ranking, 'player_name', '') == player_name:
                        projections.append(ProjectionResult(
                            player_id=player_id,
                            player_name=player_name,
                            position=position,
                            source=ProjectionSource.SIMPLE_PREDICTOR,
                            projected_points=getattr(ranking, 'predicted_fantasy_points', 0),
                            confidence=0.70,  # Default confidence
                            week=week,
                            season=season
                        ))
                        break
            except Exception as e:
                self.logger.debug(f"Simple predictor not available: {e}")
            
            # Historical Average (fallback)
            historical_avg = self._calculate_historical_average(player_name, position)
            if historical_avg > 0:
                projections.append(ProjectionResult(
                    player_id=player_id,
                    player_name=player_name,
                    position=position,
                    source=ProjectionSource.HISTORICAL_AVERAGE,
                    projected_points=historical_avg,
                    confidence=0.60,
                    week=week,
                    season=season
                ))
            
        except Exception as e:
            self.logger.error(f"Error collecting projections: {e}")
        
        return projections
    
    def _calculate_dynamic_weights(self, position: str, 
                                 projections: List[ProjectionResult]) -> Dict[ProjectionSource, float]:
        """Calculate dynamic weights based on historical performance"""
        weights = {}
        
        try:
            available_sources = [proj.source for proj in projections]
            
            for source in available_sources:
                # Get historical accuracy for this source and position
                position_accuracy = self.source_performance[source]['position_accuracy'].get(position, 0.75)
                recent_mae = np.mean(self.source_performance[source]['mae_history'][-10:]) if self.source_performance[source]['mae_history'] else 5.0
                
                # Calculate weight based on accuracy (higher accuracy = higher weight)
                # Normalize MAE to weight (lower MAE = higher weight)
                accuracy_weight = position_accuracy
                mae_weight = max(0.1, 1.0 - (recent_mae / 20.0))  # Assume max reasonable MAE is 20
                
                # Combine accuracy and MAE into final weight
                final_weight = (accuracy_weight * 0.7) + (mae_weight * 0.3)
                weights[source] = final_weight
            
            # Normalize weights to sum to 1.0
            total_weight = sum(weights.values())
            if total_weight > 0:
                weights = {source: weight / total_weight for source, weight in weights.items()}
            else:
                # Fallback to equal weights
                equal_weight = 1.0 / len(available_sources)
                weights = {source: equal_weight for source in available_sources}
                
        except Exception as e:
            self.logger.error(f"Error calculating dynamic weights: {e}")
            # Fallback to default weights
            available_sources = [proj.source for proj in projections]
            equal_weight = 1.0 / len(available_sources)
            weights = {source: equal_weight for source in available_sources}
        
        return weights
    
    def _calculate_consensus_projection(self, projections: List[ProjectionResult]) -> float:
        """Calculate simple consensus (mean) projection"""
        if not projections:
            return 0.0
        
        return np.mean([proj.projected_points for proj in projections])
    
    def _calculate_weighted_projection(self, projections: List[ProjectionResult], 
                                     weights: Dict[ProjectionSource, float]) -> float:
        """Calculate weighted projection based on source performance"""
        if not projections:
            return 0.0
        
        weighted_sum = 0.0
        total_weight = 0.0
        
        for proj in projections:
            weight = weights.get(proj.source, 0.0)
            weighted_sum += proj.projected_points * weight
            total_weight += weight
        
        return weighted_sum / total_weight if total_weight > 0 else 0.0
    
    def _calculate_ensemble_confidence(self, projections: List[ProjectionResult], 
                                     weights: Dict[ProjectionSource, float]) -> float:
        """Calculate confidence score for ensemble projection"""
        if not projections:
            return 0.0
        
        # Base confidence on source agreement and individual confidences
        projection_values = [proj.projected_points for proj in projections]
        confidence_values = [proj.confidence for proj in projections]
        
        # Agreement factor (lower variance = higher confidence)
        if len(projection_values) > 1:
            variance = np.var(projection_values)
            max_reasonable_variance = 100.0  # Assume max reasonable variance
            agreement_factor = max(0.1, 1.0 - (variance / max_reasonable_variance))
        else:
            agreement_factor = 0.8
        
        # Weighted average of individual confidences
        weighted_confidence = 0.0
        total_weight = 0.0
        
        for proj in projections:
            weight = weights.get(proj.source, 0.0)
            weighted_confidence += proj.confidence * weight
            total_weight += weight
        
        avg_confidence = weighted_confidence / total_weight if total_weight > 0 else 0.75
        
        # Combine agreement and confidence
        final_confidence = (agreement_factor * 0.4) + (avg_confidence * 0.6)
        
        return min(1.0, max(0.1, final_confidence))
    
    def _calculate_projection_range(self, projections: List[ProjectionResult], 
                                  weighted_projection: float) -> Tuple[float, float]:
        """Calculate floor and ceiling projections"""
        if not projections:
            return 0.0, 0.0
        
        projection_values = [proj.projected_points for proj in projections]
        
        # Floor: Use minimum projection or 70% of weighted projection, whichever is higher
        floor = max(min(projection_values), weighted_projection * 0.7)
        
        # Ceiling: Use maximum projection or 140% of weighted projection, whichever is lower
        ceiling = min(max(projection_values), weighted_projection * 1.4)
        
        return floor, ceiling
    
    def _calculate_boom_bust_probabilities(self, projections: List[ProjectionResult], 
                                         weighted_projection: float) -> Tuple[float, float]:
        """Calculate boom and bust probabilities"""
        if not projections or weighted_projection <= 0:
            return 0.3, 0.3  # Default probabilities
        
        # Boom: Probability of exceeding 150% of projection
        # Bust: Probability of falling below 50% of projection
        
        # Base probabilities on projection variance and confidence
        projection_values = [proj.projected_points for proj in projections]
        confidence_values = [proj.confidence for proj in projections]
        
        if len(projection_values) > 1:
            cv = np.std(projection_values) / np.mean(projection_values)  # Coefficient of variation
        else:
            cv = 0.3  # Default variability
        
        avg_confidence = np.mean(confidence_values)
        
        # Higher variability = higher boom/bust probabilities
        # Lower confidence = higher boom/bust probabilities
        base_volatility = cv + (1.0 - avg_confidence) * 0.5
        
        boom_probability = min(0.6, max(0.1, base_volatility * 0.8))
        bust_probability = min(0.6, max(0.1, base_volatility * 0.9))
        
        return boom_probability, bust_probability
    
    def _calculate_historical_average(self, player_name: str, position: str) -> float:
        """Calculate historical average for fallback projection"""
        # This would typically query a database of historical performance
        # For now, return position-based defaults
        position_defaults = {
            'QB': 20.0,
            'RB': 12.0,
            'WR': 10.0,
            'TE': 8.0
        }
        
        return position_defaults.get(position, 0.0)
    
    def _create_fallback_projection(self, player_id: int, player_name: str, 
                                  position: str, week: int, season: int) -> EnsembleProjection:
        """Create fallback projection when no sources are available"""
        historical_avg = self._calculate_historical_average(player_name, position)
        
        return EnsembleProjection(
            player_id=player_id,
            player_name=player_name,
            position=position,
            week=week,
            season=season,
            consensus_projection=historical_avg,
            weighted_projection=historical_avg,
            confidence_score=0.5,
            floor_projection=historical_avg * 0.7,
            ceiling_projection=historical_avg * 1.3,
            boom_probability=0.3,
            bust_probability=0.3,
            source_count=1,
            source_weights={'historical_average': 1.0},
            individual_projections=[]
        )
    
    def update_source_performance(self, source: ProjectionSource, position: str, 
                                actual_points: float, predicted_points: float) -> None:
        """Update historical performance tracking for a source"""
        try:
            mae = abs(actual_points - predicted_points)
            accuracy = 1.0 - min(1.0, mae / max(1.0, actual_points))
            
            # Update overall performance
            self.source_performance[source]['mae_history'].append(mae)
            self.source_performance[source]['accuracy_history'].append(accuracy)
            
            # Update position-specific performance
            if position not in self.source_performance[source]['position_accuracy']:
                self.source_performance[source]['position_accuracy'][position] = []
            
            position_accuracies = self.source_performance[source]['position_accuracy'][position]
            if isinstance(position_accuracies, list):
                position_accuracies.append(accuracy)
                # Keep only recent performance (last 50 predictions)
                if len(position_accuracies) > 50:
                    position_accuracies = position_accuracies[-50:]
                
                # Update with average
                self.source_performance[source]['position_accuracy'][position] = np.mean(position_accuracies)
            
            # Keep only recent performance
            if len(self.source_performance[source]['mae_history']) > 100:
                self.source_performance[source]['mae_history'] = self.source_performance[source]['mae_history'][-100:]
            
            if len(self.source_performance[source]['accuracy_history']) > 100:
                self.source_performance[source]['accuracy_history'] = self.source_performance[source]['accuracy_history'][-100:]
            
            self.logger.debug(f"Updated performance for {source.value} - {position}: MAE={mae:.2f}, Accuracy={accuracy:.3f}")
            
        except Exception as e:
            self.logger.error(f"Error updating source performance: {e}")

if __name__ == "__main__":
    print("🔧 ENSEMBLE PROJECTION SYSTEM TEST")
    print("=" * 40)
    
    ensemble = EnsembleProjectionSystem()
    
    # Test ensemble projection
    test_players = [
        (1, "Cooper Kupp", "WR"),
        (2, "Josh Allen", "QB"),
        (3, "Christian McCaffrey", "RB")
    ]
    
    for player_id, player_name, position in test_players:
        print(f"\n📊 Testing: {player_name} ({position})")
        print("-" * 30)
        
        projection = ensemble.generate_ensemble_projection(
            player_id, player_name, position, 1, 2024
        )
        
        print(f"Weighted Projection: {projection.weighted_projection:.1f} pts")
        print(f"Consensus Projection: {projection.consensus_projection:.1f} pts")
        print(f"Confidence: {projection.confidence_score:.1%}")
        print(f"Range: {projection.floor_projection:.1f} - {projection.ceiling_projection:.1f} pts")
        print(f"Boom Probability: {projection.boom_probability:.1%}")
        print(f"Bust Probability: {projection.bust_probability:.1%}")
        print(f"Sources: {projection.source_count}")
    
    print("\n✅ Ensemble Projection System test completed!")