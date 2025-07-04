#!/usr/bin/env python3
"""
Position-Specific Model Optimization
Implements recursive feature elimination and position-specific modeling like industry best practices
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Tuple
from sklearn.model_selection import KFold, cross_val_score
from sklearn.feature_selection import RFE, RFECV
from sklearn.linear_model import Ridge, ElasticNet, BayesianRidge
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from enum import Enum

logger = logging.getLogger(__name__)

class ModelType(Enum):
    """Different model types for position-specific optimization"""
    RIDGE_REGRESSION = "ridge_regression"
    BAYESIAN_RIDGE = "bayesian_ridge"
    ELASTIC_NET = "elastic_net"
    RANDOM_FOREST = "random_forest"
    GRADIENT_BOOSTING = "gradient_boosting"

@dataclass
class FeatureImportance:
    """Feature importance results"""
    feature_name: str
    importance_score: float
    rank: int
    selected: bool

@dataclass
class ModelPerformance:
    """Model performance metrics"""
    model_type: ModelType
    position: str
    mae: float
    rmse: float
    r2: float
    cv_score: float
    feature_count: int
    training_samples: int

@dataclass
class PositionModelResult:
    """Results for position-specific model"""
    position: str
    best_model_type: ModelType
    performance: ModelPerformance
    selected_features: List[str]
    feature_importances: List[FeatureImportance]
    model_object: Any
    scaler: StandardScaler

class PositionOptimizedModels:
    """
    Position-specific model optimization system
    Implements recursive feature elimination and cross-validation like industry leaders
    """
    
    def __init__(self):
        """Initialize position-optimized modeling system"""
        self.logger = logging.getLogger(__name__)
        
        # Position-specific models
        self.position_models: Dict[str, PositionModelResult] = {}
        
        # Feature sets for different positions
        self.position_features = {
            'QB': [
                'passing_yards', 'passing_tds', 'interceptions', 'completion_percentage',
                'rushing_yards', 'rushing_tds', 'attempts', 'sacks_taken',
                'red_zone_attempts', 'deep_ball_percentage', 'pressure_rate',
                'home_game', 'weather_score', 'opponent_def_rank', 'team_total_vegas'
            ],
            'RB': [
                'rushing_yards', 'rushing_tds', 'carries', 'targets', 'receptions',
                'receiving_yards', 'receiving_tds', 'fumbles', 'snap_percentage',
                'red_zone_carries', 'goal_line_carries', 'touches_per_game',
                'home_game', 'weather_score', 'opponent_def_rank', 'team_total_vegas'
            ],
            'WR': [
                'targets', 'receptions', 'receiving_yards', 'receiving_tds',
                'target_share', 'air_yards', 'yac', 'red_zone_targets',
                'snap_percentage', 'route_participation', 'depth_of_target',
                'home_game', 'weather_score', 'opponent_def_rank', 'team_total_vegas'
            ],
            'TE': [
                'targets', 'receptions', 'receiving_yards', 'receiving_tds',
                'target_share', 'air_yards', 'yac', 'red_zone_targets',
                'snap_percentage', 'blocking_snaps', 'route_participation',
                'home_game', 'weather_score', 'opponent_def_rank', 'team_total_vegas'
            ]
        }
        
        # Model configurations
        self.model_configs = {
            ModelType.RIDGE_REGRESSION: Ridge(alpha=1.0, random_state=42),
            ModelType.BAYESIAN_RIDGE: BayesianRidge(),
            ModelType.ELASTIC_NET: ElasticNet(alpha=1.0, l1_ratio=0.5, random_state=42),
            ModelType.RANDOM_FOREST: RandomForestRegressor(n_estimators=100, random_state=42),
            ModelType.GRADIENT_BOOSTING: GradientBoostingRegressor(n_estimators=100, random_state=42)
        }
        
        self.logger.info("Position-Optimized Models system initialized")
    
    def optimize_position_model(self, position: str, training_data: pd.DataFrame, 
                              target_column: str = 'fantasy_points') -> PositionModelResult:
        """
        Optimize model for specific position using recursive feature elimination
        
        Args:
            position: Position to optimize (QB, RB, WR, TE)
            training_data: Training dataset
            target_column: Target variable column name
            
        Returns:
            PositionModelResult with optimized model
        """
        try:
            self.logger.info(f"Optimizing model for {position}")
            
            # Prepare position-specific features
            available_features = [col for col in self.position_features[position] 
                                if col in training_data.columns]
            
            if len(available_features) < 3:
                raise ValueError(f"Insufficient features available for {position}: {available_features}")
            
            X = training_data[available_features].copy()
            y = training_data[target_column].copy()
            
            # Handle missing values
            X = X.fillna(X.mean())
            y = y.fillna(y.mean())
            
            # Scale features
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)
            X_scaled_df = pd.DataFrame(X_scaled, columns=available_features)
            
            self.logger.info(f"Training with {len(X)} samples and {len(available_features)} features")
            
            # Test all model types with feature selection
            best_performance = None
            best_model_result = None
            
            for model_type in ModelType:
                self.logger.debug(f"Testing {model_type.value} for {position}")
                
                # Perform recursive feature elimination with cross-validation
                model = self.model_configs[model_type]
                
                # Use RFECV for automatic feature selection
                cv = KFold(n_splits=5, shuffle=True, random_state=42)
                rfecv = RFECV(
                    estimator=model,
                    step=1,
                    cv=cv,
                    scoring='neg_mean_absolute_error',
                    n_jobs=-1
                )
                
                rfecv.fit(X_scaled_df, y)
                
                # Get selected features
                selected_features = [feat for feat, selected in zip(available_features, rfecv.support_) if selected]
                
                # Train final model with selected features
                X_selected = X_scaled_df[selected_features]
                final_model = self.model_configs[model_type]
                final_model.fit(X_selected, y)
                
                # Evaluate performance
                performance = self._evaluate_model_performance(
                    final_model, X_selected, y, model_type, position
                )
                
                # Check if this is the best model so far
                if best_performance is None or performance.mae < best_performance.mae:
                    best_performance = performance
                    
                    # Create feature importance list
                    feature_importances = self._get_feature_importances(
                        final_model, selected_features, model_type
                    )
                    
                    best_model_result = PositionModelResult(
                        position=position,
                        best_model_type=model_type,
                        performance=performance,
                        selected_features=selected_features,
                        feature_importances=feature_importances,
                        model_object=final_model,
                        scaler=scaler
                    )
            
            if best_model_result is None:
                raise ValueError(f"Failed to create model for {position}")
            
            # Store the best model
            self.position_models[position] = best_model_result
            
            self.logger.info(f"Optimized {position} model: {best_model_result.best_model_type.value} "
                           f"with MAE={best_performance.mae:.3f}, Features={len(best_model_result.selected_features)}")
            
            return best_model_result
            
        except Exception as e:
            self.logger.error(f"Error optimizing model for {position}: {e}")
            raise
    
    def _evaluate_model_performance(self, model, X, y, model_type: ModelType, 
                                  position: str) -> ModelPerformance:
        """Evaluate model performance using cross-validation"""
        try:
            # Cross-validation
            cv = KFold(n_splits=5, shuffle=True, random_state=42)
            cv_scores = cross_val_score(model, X, y, cv=cv, scoring='neg_mean_absolute_error')
            cv_score = -cv_scores.mean()
            
            # Full dataset metrics
            y_pred = model.predict(X)
            mae = mean_absolute_error(y, y_pred)
            rmse = np.sqrt(mean_squared_error(y, y_pred))
            r2 = r2_score(y, y_pred)
            
            return ModelPerformance(
                model_type=model_type,
                position=position,
                mae=mae,
                rmse=rmse,
                r2=r2,
                cv_score=cv_score,
                feature_count=X.shape[1],
                training_samples=X.shape[0]
            )
            
        except Exception as e:
            self.logger.error(f"Error evaluating model performance: {e}")
            raise
    
    def _get_feature_importances(self, model, features: List[str], 
                               model_type: ModelType) -> List[FeatureImportance]:
        """Extract feature importances from trained model"""
        try:
            importances = []
            
            if hasattr(model, 'feature_importances_'):
                # Tree-based models
                importance_values = model.feature_importances_
            elif hasattr(model, 'coef_'):
                # Linear models - use absolute coefficients
                importance_values = np.abs(model.coef_)
            else:
                # Fallback to equal importance
                importance_values = np.ones(len(features)) / len(features)
            
            # Create FeatureImportance objects
            for i, (feature, importance) in enumerate(zip(features, importance_values)):
                importances.append(FeatureImportance(
                    feature_name=feature,
                    importance_score=float(importance),
                    rank=i + 1,
                    selected=True
                ))
            
            # Sort by importance (descending)
            importances.sort(key=lambda x: x.importance_score, reverse=True)
            
            # Update ranks
            for i, importance in enumerate(importances):
                importance.rank = i + 1
            
            return importances
            
        except Exception as e:
            self.logger.error(f"Error getting feature importances: {e}")
            return []
    
    def predict_player_performance(self, position: str, player_features: Dict[str, float]) -> Tuple[float, float]:
        """
        Predict player performance using optimized position-specific model
        
        Args:
            position: Player position
            player_features: Dictionary of player feature values
            
        Returns:
            Tuple of (prediction, confidence)
        """
        try:
            if position not in self.position_models:
                raise ValueError(f"No optimized model available for {position}")
            
            model_result = self.position_models[position]
            
            # Prepare feature vector
            feature_vector = []
            missing_features = []
            
            for feature in model_result.selected_features:
                if feature in player_features:
                    feature_vector.append(player_features[feature])
                else:
                    # Use position-specific default
                    default_value = self._get_feature_default(feature, position)
                    feature_vector.append(default_value)
                    missing_features.append(feature)
            
            if missing_features:
                self.logger.debug(f"Using defaults for missing features: {missing_features}")
            
            # Scale features
            feature_array = np.array(feature_vector).reshape(1, -1)
            feature_array_scaled = model_result.scaler.transform(feature_array)
            
            # Make prediction
            prediction = model_result.model_object.predict(feature_array_scaled)[0]
            
            # Calculate confidence based on model performance and missing features
            base_confidence = 1.0 - (model_result.performance.mae / 20.0)  # Normalize by reasonable max MAE
            missing_penalty = len(missing_features) * 0.05  # 5% penalty per missing feature
            confidence = max(0.1, min(1.0, base_confidence - missing_penalty))
            
            return float(prediction), float(confidence)
            
        except Exception as e:
            self.logger.error(f"Error predicting player performance: {e}")
            return 0.0, 0.0
    
    def _get_feature_default(self, feature: str, position: str) -> float:
        """Get default value for missing feature"""
        # Position-specific defaults
        defaults = {
            'QB': {
                'passing_yards': 250.0, 'passing_tds': 1.5, 'interceptions': 1.0,
                'completion_percentage': 65.0, 'rushing_yards': 20.0, 'rushing_tds': 0.2,
                'attempts': 35.0, 'sacks_taken': 2.0, 'red_zone_attempts': 3.0,
                'deep_ball_percentage': 15.0, 'pressure_rate': 25.0
            },
            'RB': {
                'rushing_yards': 80.0, 'rushing_tds': 0.6, 'carries': 15.0,
                'targets': 3.0, 'receptions': 2.5, 'receiving_yards': 20.0,
                'receiving_tds': 0.1, 'fumbles': 0.2, 'snap_percentage': 60.0,
                'red_zone_carries': 2.0, 'goal_line_carries': 1.0, 'touches_per_game': 17.0
            },
            'WR': {
                'targets': 6.0, 'receptions': 4.0, 'receiving_yards': 60.0,
                'receiving_tds': 0.4, 'target_share': 15.0, 'air_yards': 80.0,
                'yac': 20.0, 'red_zone_targets': 1.0, 'snap_percentage': 70.0,
                'route_participation': 75.0, 'depth_of_target': 12.0
            },
            'TE': {
                'targets': 4.0, 'receptions': 3.0, 'receiving_yards': 40.0,
                'receiving_tds': 0.3, 'target_share': 12.0, 'air_yards': 50.0,
                'yac': 15.0, 'red_zone_targets': 1.5, 'snap_percentage': 80.0,
                'blocking_snaps': 20.0, 'route_participation': 65.0
            }
        }
        
        # Universal defaults
        universal_defaults = {
            'home_game': 0.5, 'weather_score': 0.0, 'opponent_def_rank': 16.0, 'team_total_vegas': 23.0
        }
        
        return defaults.get(position, {}).get(feature, universal_defaults.get(feature, 0.0))
    
    def get_model_summary(self, position: str) -> Dict[str, Any]:
        """Get summary of optimized model for position"""
        if position not in self.position_models:
            return {'error': f'No model available for {position}'}
        
        model_result = self.position_models[position]
        
        return {
            'position': position,
            'model_type': model_result.best_model_type.value,
            'performance': {
                'mae': model_result.performance.mae,
                'rmse': model_result.performance.rmse,
                'r2': model_result.performance.r2,
                'cv_score': model_result.performance.cv_score
            },
            'feature_count': len(model_result.selected_features),
            'selected_features': model_result.selected_features,
            'top_features': [
                {'name': fi.feature_name, 'importance': fi.importance_score}
                for fi in model_result.feature_importances[:5]
            ],
            'training_samples': model_result.performance.training_samples
        }
    
    def optimize_all_positions(self, training_data: Dict[str, pd.DataFrame]) -> Dict[str, PositionModelResult]:
        """Optimize models for all positions"""
        results = {}
        
        for position in ['QB', 'RB', 'WR', 'TE']:
            if position in training_data and not training_data[position].empty:
                try:
                    result = self.optimize_position_model(position, training_data[position])
                    results[position] = result
                except Exception as e:
                    self.logger.error(f"Failed to optimize {position} model: {e}")
        
        return results

# Sample data generator for testing
def generate_sample_training_data() -> Dict[str, pd.DataFrame]:
    """Generate sample training data for testing"""
    np.random.seed(42)
    
    data = {}
    
    # QB data
    qb_data = {
        'fantasy_points': np.random.normal(20, 8, 500),
        'passing_yards': np.random.normal(250, 80, 500),
        'passing_tds': np.random.normal(1.5, 1.2, 500),
        'interceptions': np.random.normal(1, 0.8, 500),
        'completion_percentage': np.random.normal(65, 10, 500),
        'rushing_yards': np.random.normal(20, 25, 500),
        'rushing_tds': np.random.normal(0.2, 0.5, 500),
        'home_game': np.random.binomial(1, 0.5, 500),
        'weather_score': np.random.normal(0, 1, 500),
        'opponent_def_rank': np.random.uniform(1, 32, 500)
    }
    data['QB'] = pd.DataFrame(qb_data)
    
    # WR data
    wr_data = {
        'fantasy_points': np.random.normal(12, 6, 800),
        'targets': np.random.normal(6, 4, 800),
        'receptions': np.random.normal(4, 3, 800),
        'receiving_yards': np.random.normal(60, 40, 800),
        'receiving_tds': np.random.normal(0.4, 0.6, 800),
        'target_share': np.random.normal(15, 8, 800),
        'snap_percentage': np.random.normal(70, 20, 800),
        'home_game': np.random.binomial(1, 0.5, 800),
        'weather_score': np.random.normal(0, 1, 800),
        'opponent_def_rank': np.random.uniform(1, 32, 800)
    }
    data['WR'] = pd.DataFrame(wr_data)
    
    return data

if __name__ == "__main__":
    print("🔧 POSITION-OPTIMIZED MODELS TEST")
    print("=" * 40)
    
    # Generate sample data
    training_data = generate_sample_training_data()
    
    # Initialize optimizer
    optimizer = PositionOptimizedModels()
    
    # Test position optimization
    for position in ['QB', 'WR']:
        print(f"\n📊 Optimizing {position} model")
        print("-" * 30)
        
        result = optimizer.optimize_position_model(position, training_data[position])
        
        print(f"Best Model: {result.best_model_type.value}")
        print(f"MAE: {result.performance.mae:.3f}")
        print(f"R²: {result.performance.r2:.3f}")
        print(f"Selected Features: {len(result.selected_features)}")
        print(f"Top Features: {[fi.feature_name for fi in result.feature_importances[:3]]}")
        
        # Test prediction
        sample_features = {feat: np.random.normal(0, 1) for feat in result.selected_features}
        prediction, confidence = optimizer.predict_player_performance(position, sample_features)
        print(f"Sample Prediction: {prediction:.1f} pts (confidence: {confidence:.1%})")
    
    print("\n✅ Position-Optimized Models test completed!")