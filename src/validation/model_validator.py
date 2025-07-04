"""
Model Validation System
Tests prediction accuracy against real 2024 NFL data
"""
from typing import Dict, List, Optional, Tuple, Any, Union
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from src.models.comprehensive_prediction_system import ComprehensivePredictionSystem
from src.models.prediction_model import NFLPredictionModel
from src.utils.type_hint_utility import PlayerId, Season, Week, TeamCode, Position
from src.utils.unified_database_operations import DatabaseSessionManager
from src.database.models import Player, ActualResults, Prediction, PredictionAccuracy


class ValidationMetric(Enum):
    """Types of validation metrics"""
    MEAN_ABSOLUTE_ERROR = "mae"
    ROOT_MEAN_SQUARE_ERROR = "rmse"
    MEAN_ABSOLUTE_PERCENTAGE_ERROR = "mape"
    ACCURACY_WITHIN_5 = "within_5_points"
    ACCURACY_WITHIN_10 = "within_10_points"
    CORRELATION = "correlation"
    DIRECTIONAL_ACCURACY = "directional_accuracy"


@dataclass
class ValidationResult:
    """Single validation result"""
    player_id: PlayerId
    player_name: str
    position: Position
    season: Season
    week: Week
    predicted_fp: float
    actual_fp: float
    error: float
    absolute_error: float
    percentage_error: float
    within_5_points: bool
    within_10_points: bool
    prediction_confidence: float
    model_version: str


@dataclass
class ValidationSummary:
    """Summary of validation results"""
    total_predictions: int
    position: Optional[Position]
    season: Season
    week_range: Tuple[Week, Week]
    
    # Accuracy metrics
    mae: float
    rmse: float
    mape: float
    within_5_pct: float
    within_10_pct: float
    correlation: float
    directional_accuracy: float
    
    # Performance by confidence
    high_confidence_mae: float
    medium_confidence_mae: float
    low_confidence_mae: float
    
    # Best and worst predictions
    best_predictions: List[ValidationResult]
    worst_predictions: List[ValidationResult]
    
    # Model insights
    overall_grade: str
    strengths: List[str]
    weaknesses: List[str]
    recommendations: List[str]


class ModelValidator:
    """Validates prediction models against actual results"""
    
    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)
        self.db_manager = DatabaseSessionManager()
        
        # Initialize prediction systems
        self.comprehensive_system = ComprehensivePredictionSystem()
        self.base_models = {
            'QB': NFLPredictionModel('QB'),
            'RB': NFLPredictionModel('RB'),
            'WR': NFLPredictionModel('WR'),
            'TE': NFLPredictionModel('TE')
        }
        
        # Validation thresholds
        self.accuracy_thresholds = {
            'excellent': {'mae': 3.0, 'within_10': 0.90},
            'good': {'mae': 5.0, 'within_10': 0.80},
            'fair': {'mae': 7.0, 'within_10': 0.70},
            'poor': {'mae': 10.0, 'within_10': 0.60}
        }
        
        # Confidence levels
        self.confidence_levels = {
            'high': 0.75,
            'medium': 0.60,
            'low': 0.45
        }
    
    def validate_2024_season(self, start_week: Week = 1, end_week: Week = 18, 
                           position: Optional[Position] = None) -> ValidationSummary:
        """Validate model performance against 2024 season data"""
        self.logger.info(f"Validating 2024 season data (weeks {start_week}-{end_week})")
        
        try:
            # Collect all validation results
            all_results: List[ValidationResult] = []
            
            for week in range(start_week, end_week + 1):
                week_results = self._validate_week(2024, week, position)
                all_results.extend(week_results)
                
                if week % 4 == 0:  # Log progress every 4 weeks
                    self.logger.info(f"Validated through Week {week}, {len(all_results)} total predictions")
            
            # Generate comprehensive summary
            summary = self._generate_validation_summary(all_results, 2024, (start_week, end_week), position)
            
            # Store validation results
            self._store_validation_results(all_results)
            
            self.logger.info(f"Validation complete: {len(all_results)} predictions, MAE: {summary.mae:.2f}")
            return summary
            
        except Exception as e:
            self.logger.error(f"Error validating 2024 season: {e}")
            raise
    
    def validate_week(self, season: Season, week: Week, position: Optional[Position] = None) -> ValidationSummary:
        """Validate model performance for a specific week"""
        self.logger.info(f"Validating {season} Week {week}")
        
        try:
            results = self._validate_week(season, week, position)
            summary = self._generate_validation_summary(results, season, (week, week), position)
            
            self.logger.info(f"Week {week} validation: {len(results)} predictions, MAE: {summary.mae:.2f}")
            return summary
            
        except Exception as e:
            self.logger.error(f"Error validating week {week}: {e}")
            raise
    
    def _validate_week(self, season: Season, week: Week, position: Optional[Position] = None) -> List[ValidationResult]:
        """Validate predictions for a single week"""
        try:
            # Get actual results for this week
            def get_actual_results(session):
                query = session.query(ActualResults).filter(
                    ActualResults.season == season,
                    ActualResults.week == week
                )
                if position:
                    # Join with Player to filter by position
                    query = query.join(Player, ActualResults.player_id == Player.id).filter(
                        Player.position == position
                    )
                return query.all()
            
            actual_results = self.db_manager.execute_readonly(get_actual_results)
            
            if not actual_results:
                self.logger.warning(f"No actual results found for {season} Week {week}")
                return []
            
            validation_results: List[ValidationResult] = []
            
            # Generate predictions and compare
            for actual in actual_results:
                try:
                    # Get comprehensive prediction
                    prediction = self.comprehensive_system.predict_comprehensive(
                        actual.player_id, season, week
                    )
                    
                    if not prediction:
                        continue
                    
                    # Calculate validation metrics
                    predicted_fp = prediction.final_prediction.get('target_fantasy_points', 0)
                    actual_fp = actual.actual_fantasy_points or 0
                    
                    error = predicted_fp - actual_fp
                    abs_error = abs(error)
                    pct_error = (abs_error / max(actual_fp, 1)) * 100  # Avoid division by zero
                    
                    validation_result = ValidationResult(
                        player_id=actual.player_id,
                        player_name=prediction.player_name,
                        position=prediction.position,
                        season=season,
                        week=week,
                        predicted_fp=predicted_fp,
                        actual_fp=actual_fp,
                        error=error,
                        absolute_error=abs_error,
                        percentage_error=pct_error,
                        within_5_points=abs_error <= 5.0,
                        within_10_points=abs_error <= 10.0,
                        prediction_confidence=prediction.overall_confidence,
                        model_version="comprehensive_v1.0"
                    )
                    
                    validation_results.append(validation_result)
                    
                except Exception as e:
                    self.logger.warning(f"Error validating player {actual.player_id}: {e}")
                    continue
            
            return validation_results
            
        except Exception as e:
            self.logger.error(f"Error validating week {week}: {e}")
            return []
    
    def _generate_validation_summary(self, results: List[ValidationResult], season: Season, 
                                   week_range: Tuple[Week, Week], position: Optional[Position]) -> ValidationSummary:
        """Generate comprehensive validation summary"""
        try:
            if not results:
                return self._create_empty_summary(season, week_range, position)
            
            # Calculate basic metrics
            mae = np.mean([r.absolute_error for r in results])
            rmse = np.sqrt(np.mean([r.error ** 2 for r in results]))
            mape = np.mean([r.percentage_error for r in results])
            within_5_pct = np.mean([r.within_5_points for r in results]) * 100
            within_10_pct = np.mean([r.within_10_points for r in results]) * 100
            
            # Calculate correlation
            predicted_values = [r.predicted_fp for r in results]
            actual_values = [r.actual_fp for r in results]
            correlation = np.corrcoef(predicted_values, actual_values)[0, 1] if len(results) > 1 else 0
            
            # Calculate directional accuracy
            directional_accuracy = self._calculate_directional_accuracy(results)
            
            # Performance by confidence level
            high_conf_results = [r for r in results if r.prediction_confidence >= self.confidence_levels['high']]
            medium_conf_results = [r for r in results if self.confidence_levels['medium'] <= r.prediction_confidence < self.confidence_levels['high']]
            low_conf_results = [r for r in results if r.prediction_confidence < self.confidence_levels['medium']]
            
            high_confidence_mae = np.mean([r.absolute_error for r in high_conf_results]) if high_conf_results else 0
            medium_confidence_mae = np.mean([r.absolute_error for r in medium_conf_results]) if medium_conf_results else 0
            low_confidence_mae = np.mean([r.absolute_error for r in low_conf_results]) if low_conf_results else 0
            
            # Best and worst predictions
            sorted_results = sorted(results, key=lambda x: x.absolute_error)
            best_predictions = sorted_results[:5]
            worst_predictions = sorted_results[-5:]
            
            # Generate insights
            overall_grade = self._calculate_overall_grade(mae, within_10_pct)
            strengths = self._identify_strengths(results, mae, within_10_pct, correlation)
            weaknesses = self._identify_weaknesses(results, mae, within_10_pct)
            recommendations = self._generate_recommendations(results, mae, within_10_pct, correlation)
            
            return ValidationSummary(
                total_predictions=len(results),
                position=position,
                season=season,
                week_range=week_range,
                mae=mae,
                rmse=rmse,
                mape=mape,
                within_5_pct=within_5_pct,
                within_10_pct=within_10_pct,
                correlation=correlation,
                directional_accuracy=directional_accuracy,
                high_confidence_mae=high_confidence_mae,
                medium_confidence_mae=medium_confidence_mae,
                low_confidence_mae=low_confidence_mae,
                best_predictions=best_predictions,
                worst_predictions=worst_predictions,
                overall_grade=overall_grade,
                strengths=strengths,
                weaknesses=weaknesses,
                recommendations=recommendations
            )
            
        except Exception as e:
            self.logger.error(f"Error generating validation summary: {e}")
            return self._create_empty_summary(season, week_range, position)
    
    def _calculate_directional_accuracy(self, results: List[ValidationResult]) -> float:
        """Calculate directional accuracy (predicting over/under performance)"""
        if len(results) < 2:
            return 0.0
        
        # Calculate average actual performance
        avg_actual = np.mean([r.actual_fp for r in results])
        
        correct_directions = 0
        total_predictions = 0
        
        for result in results:
            predicted_vs_avg = result.predicted_fp - avg_actual
            actual_vs_avg = result.actual_fp - avg_actual
            
            # Both above average or both below average
            if (predicted_vs_avg > 0 and actual_vs_avg > 0) or (predicted_vs_avg < 0 and actual_vs_avg < 0):
                correct_directions += 1
            
            total_predictions += 1
        
        return (correct_directions / total_predictions) * 100 if total_predictions > 0 else 0
    
    def _calculate_overall_grade(self, mae: float, within_10_pct: float) -> str:
        """Calculate overall model grade"""
        if mae <= self.accuracy_thresholds['excellent']['mae'] and within_10_pct >= self.accuracy_thresholds['excellent']['within_10'] * 100:
            return 'A'
        elif mae <= self.accuracy_thresholds['good']['mae'] and within_10_pct >= self.accuracy_thresholds['good']['within_10'] * 100:
            return 'B'
        elif mae <= self.accuracy_thresholds['fair']['mae'] and within_10_pct >= self.accuracy_thresholds['fair']['within_10'] * 100:
            return 'C'
        elif mae <= self.accuracy_thresholds['poor']['mae'] and within_10_pct >= self.accuracy_thresholds['poor']['within_10'] * 100:
            return 'D'
        else:
            return 'F'
    
    def _identify_strengths(self, results: List[ValidationResult], mae: float, 
                          within_10_pct: float, correlation: float) -> List[str]:
        """Identify model strengths"""
        strengths = []
        
        if mae <= 4.0:
            strengths.append("Excellent overall accuracy (low MAE)")
        
        if within_10_pct >= 85:
            strengths.append("High percentage of predictions within 10 points")
        
        if correlation >= 0.7:
            strengths.append("Strong correlation with actual results")
        
        # Check high-confidence performance
        high_conf_results = [r for r in results if r.prediction_confidence >= 0.75]
        if high_conf_results:
            high_conf_mae = np.mean([r.absolute_error for r in high_conf_results])
            if high_conf_mae <= 3.5:
                strengths.append("Excellent accuracy on high-confidence predictions")
        
        # Check position-specific performance
        position_performance = {}
        for result in results:
            if result.position not in position_performance:
                position_performance[result.position] = []
            position_performance[result.position].append(result.absolute_error)
        
        for position, errors in position_performance.items():
            if np.mean(errors) <= 4.0:
                strengths.append(f"Strong {position} position predictions")
        
        if not strengths:
            strengths.append("Model shows consistent performance patterns")
        
        return strengths
    
    def _identify_weaknesses(self, results: List[ValidationResult], mae: float, within_10_pct: float) -> List[str]:
        """Identify model weaknesses"""
        weaknesses = []
        
        if mae >= 8.0:
            weaknesses.append("High overall prediction error")
        
        if within_10_pct <= 60:
            weaknesses.append("Low percentage of accurate predictions")
        
        # Check for systematic biases
        avg_error = np.mean([r.error for r in results])
        if abs(avg_error) >= 2.0:
            if avg_error > 0:
                weaknesses.append("Systematic over-prediction bias")
            else:
                weaknesses.append("Systematic under-prediction bias")
        
        # Check confidence calibration
        high_conf_results = [r for r in results if r.prediction_confidence >= 0.75]
        low_conf_results = [r for r in results if r.prediction_confidence < 0.5]
        
        if high_conf_results and low_conf_results:
            high_conf_mae = np.mean([r.absolute_error for r in high_conf_results])
            low_conf_mae = np.mean([r.absolute_error for r in low_conf_results])
            
            if high_conf_mae >= low_conf_mae:
                weaknesses.append("Poor confidence calibration")
        
        # Check for outliers
        outliers = [r for r in results if r.absolute_error >= 15.0]
        if len(outliers) / len(results) >= 0.1:
            weaknesses.append("High number of extreme prediction errors")
        
        if not weaknesses:
            weaknesses.append("Minor accuracy improvements needed")
        
        return weaknesses
    
    def _generate_recommendations(self, results: List[ValidationResult], mae: float, 
                                within_10_pct: float, correlation: float) -> List[str]:
        """Generate improvement recommendations"""
        recommendations = []
        
        if mae >= 6.0:
            recommendations.append("Improve feature engineering and model complexity")
        
        if within_10_pct <= 70:
            recommendations.append("Focus on reducing prediction variance")
        
        if correlation <= 0.6:
            recommendations.append("Investigate systematic prediction patterns")
        
        # Position-specific recommendations
        position_performance = {}
        for result in results:
            if result.position not in position_performance:
                position_performance[result.position] = []
            position_performance[result.position].append(result.absolute_error)
        
        for position, errors in position_performance.items():
            if np.mean(errors) >= 6.0:
                recommendations.append(f"Improve {position} position modeling")
        
        # Check prediction distribution
        large_errors = [r for r in results if r.absolute_error >= 10.0]
        if len(large_errors) / len(results) >= 0.2:
            recommendations.append("Implement outlier detection and handling")
        
        # Confidence-based recommendations
        high_conf_results = [r for r in results if r.prediction_confidence >= 0.75]
        if len(high_conf_results) / len(results) < 0.3:
            recommendations.append("Improve confidence estimation algorithms")
        
        if not recommendations:
            recommendations.append("Continue monitoring and fine-tuning model parameters")
        
        return recommendations
    
    def _store_validation_results(self, results: List[ValidationResult]) -> None:
        """Store validation results in database"""
        try:
            def store_results(session):
                stored_count = 0
                for result in results:
                    # Check if already exists
                    existing = session.query(PredictionAccuracy).filter(
                        PredictionAccuracy.player_id == result.player_id,
                        PredictionAccuracy.season == result.season,
                        PredictionAccuracy.week == result.week,
                        PredictionAccuracy.model_version == result.model_version
                    ).first()
                    
                    if existing:
                        # Update existing
                        existing.fantasy_points_error = result.error
                        existing.fantasy_points_abs_error = result.absolute_error
                        existing.fantasy_points_percent_error = result.percentage_error
                        existing.was_within_5_points = result.within_5_points
                        existing.was_within_10_points = result.within_10_points
                        existing.confidence_score = result.prediction_confidence
                    else:
                        # Create new
                        accuracy_record = PredictionAccuracy(
                            prediction_id=0,  # Would need to link to actual prediction
                            player_id=result.player_id,
                            season=result.season,
                            week=result.week,
                            fantasy_points_error=result.error,
                            fantasy_points_abs_error=result.absolute_error,
                            fantasy_points_percent_error=result.percentage_error,
                            was_within_5_points=result.within_5_points,
                            was_within_10_points=result.within_10_points,
                            model_version=result.model_version,
                            confidence_score=result.prediction_confidence,
                            accuracy_grade=self._calculate_individual_grade(result.absolute_error)
                        )
                        session.add(accuracy_record)
                    
                    stored_count += 1
                
                return stored_count
            
            count = self.db_manager.execute_with_session(store_results)
            self.logger.info(f"Stored {count} validation results")
            
        except Exception as e:
            self.logger.error(f"Error storing validation results: {e}")
    
    def _calculate_individual_grade(self, absolute_error: float) -> str:
        """Calculate grade for individual prediction"""
        if absolute_error <= 2.0:
            return 'A'
        elif absolute_error <= 4.0:
            return 'B'
        elif absolute_error <= 6.0:
            return 'C'
        elif absolute_error <= 10.0:
            return 'D'
        else:
            return 'F'
    
    def _create_empty_summary(self, season: Season, week_range: Tuple[Week, Week], 
                            position: Optional[Position]) -> ValidationSummary:
        """Create empty validation summary for cases with no data"""
        return ValidationSummary(
            total_predictions=0,
            position=position,
            season=season,
            week_range=week_range,
            mae=0.0,
            rmse=0.0,
            mape=0.0,
            within_5_pct=0.0,
            within_10_pct=0.0,
            correlation=0.0,
            directional_accuracy=0.0,
            high_confidence_mae=0.0,
            medium_confidence_mae=0.0,
            low_confidence_mae=0.0,
            best_predictions=[],
            worst_predictions=[],
            overall_grade='N/A',
            strengths=['No data available'],
            weaknesses=['Insufficient data for validation'],
            recommendations=['Collect more data before validation']
        )
    
    def compare_model_versions(self, season: Season, weeks: List[Week]) -> Dict[str, ValidationSummary]:
        """Compare different model versions"""
        try:
            comparison_results = {}
            
            # Test comprehensive system
            comprehensive_results = []
            for week in weeks:
                week_results = self._validate_week(season, week)
                comprehensive_results.extend(week_results)
            
            comparison_results['comprehensive'] = self._generate_validation_summary(
                comprehensive_results, season, (min(weeks), max(weeks)), None
            )
            
            # Could add comparisons with base models, simpler systems, etc.
            
            return comparison_results
            
        except Exception as e:
            self.logger.error(f"Error comparing model versions: {e}")
            return {}


# Convenience functions
def validate_current_season(position: Optional[Position] = None) -> ValidationSummary:
    """Validate current season performance"""
    validator = ModelValidator()
    current_week = min(18, max(1, (datetime.now() - datetime(2024, 9, 5)).days // 7 + 1))
    return validator.validate_2024_season(1, current_week, position)


def validate_recent_weeks(num_weeks: int = 4, position: Optional[Position] = None) -> ValidationSummary:
    """Validate recent weeks performance"""
    validator = ModelValidator()
    current_week = min(18, max(1, (datetime.now() - datetime(2024, 9, 5)).days // 7 + 1))
    start_week = max(1, current_week - num_weeks + 1)
    return validator.validate_2024_season(start_week, current_week, position)


__all__ = [
    'ModelValidator', 'ValidationResult', 'ValidationSummary', 'ValidationMetric',
    'validate_current_season', 'validate_recent_weeks'
]