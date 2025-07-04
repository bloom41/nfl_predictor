from typing import Dict, List, Optional, Union, Tuple, Any
import pandas as pd
import numpy as np
import pickle
import logging
import json
from datetime import datetime
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import xgboost as xgb
import lightgbm as lgb
from src.database.database import db
from src.database.models import Prediction, ModelMetadata, Player
from src.data_processing.feature_engineering import FeatureEngineer

# Import our type aliases
from src.utils.type_hint_utility import PlayerId, Season, Week, Position, FantasyPoints

class NFLPredictionModel:
    def __init__(self, position: Position = 'QB') -> None:
        self.position: Position = position
        self.models: Dict[str, Any] = {}
        self.scalers: Dict[str, StandardScaler] = {}
        self.feature_columns: List[str] = []
        self.target_columns: List[str] = [
            'target_passing_yards', 'target_passing_tds', 'target_rushing_yards',
            'target_rushing_tds', 'target_receiving_yards', 'target_receiving_tds',
            'target_fantasy_points'
        ]
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.feature_engineer: FeatureEngineer = FeatureEngineer()
        self.label_encoders: Dict[str, LabelEncoder] = {}
        
        # Auto-load existing models
        self._auto_load_models()
        
    def _auto_load_models(self) -> None:
        """Automatically load existing models for the position"""
        import os
        model_filepath: str = f"models/{self.position}_model_2024.pkl"
        
        if os.path.exists(model_filepath):
            try:
                self.load_model(model_filepath)
                self.logger.info(f"Auto-loaded {self.position} model from {model_filepath}")
            except Exception as e:
                self.logger.warning(f"Failed to auto-load {self.position} model: {e}")
        else:
            self.logger.info(f"No existing model found for {self.position} at {model_filepath}")
        
    def prepare_data(self, season: Season) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame]]:
        """Prepare training data for the model"""
        self.logger.info(f"Preparing data for {self.position} position")
        
        # Get training data
        df: pd.DataFrame = self.feature_engineer.prepare_training_data(season, self.position)
        
        if df.empty:
            self.logger.error("No training data available")
            return None, None
            
        # Handle categorical variables
        categorical_columns: List[str] = ['team', 'position']
        self.label_encoders = {}
        for col in categorical_columns:
            if col in df.columns:
                le: LabelEncoder = LabelEncoder()
                df[col] = le.fit_transform(df[col].astype(str))
                self.label_encoders[col] = le
                
        # Separate features and targets
        feature_columns: List[str] = [col for col in df.columns if not col.startswith('target_')]
        self.feature_columns = feature_columns
        
        X: pd.DataFrame = df[feature_columns].fillna(0)
        y: pd.DataFrame = df[self.target_columns].fillna(0)
        
        return X, y
        
    def train_models(self, season: Season) -> bool:
        """Train prediction models for different metrics"""
        X, y = self.prepare_data(season)
        
        if X is None or y is None:
            self.logger.error("Could not prepare training data")
            return False
            
        self.logger.info(f"Training on {len(X)} samples with {len(X.columns)} features")
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        # Scale features
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        self.scalers['main'] = scaler
        
        # Train models for each target metric
        model_performance: Dict[str, Dict[str, float]] = {}
        
        for target_col in self.target_columns:
            if target_col not in y.columns:
                continue
                
            self.logger.info(f"Training model for {target_col}")
            
            y_train_target = y_train[target_col]
            y_test_target = y_test[target_col]
            
            # Try different algorithms
            models_to_try: Dict[str, Any] = {
                'xgboost': xgb.XGBRegressor(
                    n_estimators=100,
                    max_depth=6,
                    learning_rate=0.1,
                    random_state=42,
                    n_jobs=-1
                ),
                'lightgbm': lgb.LGBMRegressor(
                    n_estimators=100,
                    max_depth=6,
                    learning_rate=0.1,
                    random_state=42,
                    n_jobs=-1,
                    verbose=-1
                ),
                'random_forest': RandomForestRegressor(
                    n_estimators=100,
                    max_depth=10,
                    random_state=42,
                    n_jobs=-1
                ),
                'gradient_boosting': GradientBoostingRegressor(
                    n_estimators=100,
                    max_depth=6,
                    learning_rate=0.1,
                    random_state=42
                )
            }
            
            best_model: Optional[Any] = None
            best_score: float = float('inf')
            best_model_name: Optional[str] = None
            
            for model_name, model in models_to_try.items():
                try:
                    # Train model
                    model.fit(X_train_scaled, y_train_target)
                    
                    # Evaluate
                    y_pred = model.predict(X_test_scaled)
                    mae = mean_absolute_error(y_test_target, y_pred)
                    
                    if mae < best_score:
                        best_score = mae
                        best_model = model
                        best_model_name = model_name
                        
                except Exception as e:
                    self.logger.error(f"Error training {model_name} for {target_col}: {e}")
                    continue
                    
            if best_model is not None:
                self.models[target_col] = best_model
                
                # Calculate detailed performance metrics
                y_pred: np.ndarray = best_model.predict(X_test_scaled)
                performance: Dict[str, Union[float, str]] = {
                    'mae': mean_absolute_error(y_test_target, y_pred),
                    'mse': mean_squared_error(y_test_target, y_pred),
                    'r2': r2_score(y_test_target, y_pred),
                    'model_type': best_model_name
                }
                model_performance[target_col] = performance
                
                self.logger.info(f"Best model for {target_col}: {best_model_name} (MAE: {performance['mae']:.2f})")
                
        # Save model metadata
        self._save_model_metadata(model_performance, season)
        
        return len(self.models) > 0
        
    def predict_player_performance(self, player_id: PlayerId, season: Season, week: Week) -> Optional[Dict[str, Any]]:
        """Predict performance for a specific player and week"""
        if not self.models:
            self.logger.error("No trained models available")
            return None
            
        # Create features for the player
        features: Optional[Dict[str, Any]] = self.feature_engineer.create_player_features(player_id, season, week)
        if not features:
            self.logger.error(f"Could not create features for player {player_id}")
            return None
            
        # Add sentiment features
        sentiment_features: Dict[str, Any] = self.feature_engineer.create_sentiment_features(player_id)
        features.update(sentiment_features)
        
        # Add matchup features (simplified)
        matchup_features: Dict[str, Any] = self.feature_engineer.create_matchup_features('', '', week)
        features.update(matchup_features)
        
        # Prepare feature vector
        feature_vector: List[float] = []
        for col in self.feature_columns:
            if col in features:
                value = features[col]
                # Handle categorical encoding
                if col in self.label_encoders:
                    try:
                        value = self.label_encoders[col].transform([str(value)])[0]
                    except ValueError:
                        # Handle unseen categories
                        value = 0
                feature_vector.append(value)
            else:
                feature_vector.append(0)  # Default value for missing features
                
        X: np.ndarray = np.array(feature_vector).reshape(1, -1)
        
        # Scale features
        if 'main' in self.scalers:
            X_scaled: np.ndarray = self.scalers['main'].transform(X)
        else:
            X_scaled = X
            
        # Make predictions
        predictions: Dict[str, float] = {}
        confidence_scores: List[float] = []
        
        for target_col, model in self.models.items():
            try:
                pred = model.predict(X_scaled)[0]
                predictions[target_col] = max(0, pred)  # Ensure non-negative predictions
                
                # Calculate confidence (simplified)
                if hasattr(model, 'predict_proba'):
                    confidence = 0.8  # Default for probabilistic models
                else:
                    confidence = 0.7  # Default for deterministic models
                confidence_scores.append(confidence)
                
            except Exception as e:
                self.logger.error(f"Error predicting {target_col}: {e}")
                predictions[target_col] = 0
                confidence_scores.append(0.5)
                
        # Overall confidence
        avg_confidence: float = np.mean(confidence_scores) if confidence_scores else 0.5
        
        return {
            'player_id': player_id,
            'season': season,
            'week': week,
            'predictions': predictions,
            'confidence': avg_confidence
        }
        
    def predict_top_performers(self, season: Season, week: Week, position: Optional[Position] = None, top_n: int = 20) -> List[Dict[str, Any]]:
        """Predict top performers for a given week"""
        session = db.get_session()
        
        try:
            # Get all players for the position
            query = session.query(Player)
            if position:
                query = query.filter(Player.position == position)
            elif self.position:
                query = query.filter(Player.position == self.position)
                
            players = query.all()
            
            predictions: List[Dict[str, Any]] = []
            
            for player in players:
                pred: Optional[Dict[str, Any]] = self.predict_player_performance(player.id, season, week)
                if pred and pred['predictions'].get('target_fantasy_points', 0) > 0:
                    predictions.append({
                        'player_id': player.id,
                        'player_name': player.name,
                        'team': player.team,
                        'position': player.position,
                        'predicted_fantasy_points': pred['predictions'].get('target_fantasy_points', 0),
                        'predicted_passing_yards': pred['predictions'].get('target_passing_yards', 0),
                        'predicted_passing_tds': pred['predictions'].get('target_passing_tds', 0),
                        'predicted_rushing_yards': pred['predictions'].get('target_rushing_yards', 0),
                        'predicted_rushing_tds': pred['predictions'].get('target_rushing_tds', 0),
                        'predicted_receiving_yards': pred['predictions'].get('target_receiving_yards', 0),
                        'predicted_receiving_tds': pred['predictions'].get('target_receiving_tds', 0),
                        'confidence': pred['confidence']
                    })
                    
            # Sort by predicted fantasy points
            predictions.sort(key=lambda x: x['predicted_fantasy_points'], reverse=True)
            
            return predictions[:top_n]
            
        except Exception as e:
            self.logger.error(f"Error predicting top performers: {e}")
            return []
        finally:
            db.close_session(session)
            
    def save_predictions_to_db(self, predictions_list: List[Dict[str, Any]]) -> None:
        """Save predictions to database"""
        session = db.get_session()
        
        try:
            for pred_data in predictions_list:
                prediction = Prediction(
                    player_id=pred_data['player_id'],
                    season=pred_data.get('season', 2025),
                    week=pred_data.get('week', 1),
                    predicted_passing_yards=pred_data.get('predicted_passing_yards', 0),
                    predicted_passing_tds=pred_data.get('predicted_passing_tds', 0),
                    predicted_rushing_yards=pred_data.get('predicted_rushing_yards', 0),
                    predicted_rushing_tds=pred_data.get('predicted_rushing_tds', 0),
                    predicted_receiving_yards=pred_data.get('predicted_receiving_yards', 0),
                    predicted_receiving_tds=pred_data.get('predicted_receiving_tds', 0),
                    predicted_fantasy_points=pred_data.get('predicted_fantasy_points', 0),
                    confidence_score=pred_data.get('confidence', 0.5),
                    model_version=f"{self.position}_v1.0"
                )
                session.add(prediction)
                
            session.commit()
            self.logger.info(f"Saved {len(predictions_list)} predictions to database")
            
        except Exception as e:
            session.rollback()
            self.logger.error(f"Error saving predictions: {e}")
        finally:
            db.close_session(session)
            
    def _save_model_metadata(self, performance: Dict[str, Dict[str, Union[float, str]]], season: Season) -> None:
        """Save model training metadata"""
        session = db.get_session()
        
        try:
            metadata = ModelMetadata(
                model_name=f"NFL_{self.position}_Predictor",
                version="v1.0",
                training_date=datetime.utcnow(),
                accuracy_score=np.mean([p['r2'] for p in performance.values()]),
                feature_importance=json.dumps({
                    'feature_count': len(self.feature_columns),
                    'target_metrics': list(performance.keys()),
                    'performance': performance
                })
            )
            session.add(metadata)
            session.commit()
            
        except Exception as e:
            session.rollback()
            self.logger.error(f"Error saving model metadata: {e}")
        finally:
            db.close_session(session)
            
    def save_model(self, filepath: str) -> None:
        """Save trained model to file"""
        model_data: Dict[str, Any] = {
            'models': self.models,
            'scalers': self.scalers,
            'feature_columns': self.feature_columns,
            'position': self.position,
            'label_encoders': getattr(self, 'label_encoders', {})
        }
        
        try:
            with open(filepath, 'wb') as f:
                pickle.dump(model_data, f)
            self.logger.info(f"Model saved to {filepath}")
        except Exception as e:
            self.logger.error(f"Error saving model: {e}")
            
    def train_models_with_params(self, season, optimized_params=None):
        """Train models with optimized parameters from feedback loop"""
        try:
            # Prepare training data
            X, y = self.prepare_data(season)
            if X is None or y is None:
                return False
                
            # Use optimized parameters if provided
            base_params = optimized_params or {}
            
            # Train models with feedback-enhanced parameters
            algorithms = {
                'RandomForest': RandomForestRegressor(
                    random_state=42,
                    n_estimators=base_params.get('n_estimators', 200),
                    max_depth=base_params.get('max_depth', 12),
                    min_samples_split=base_params.get('min_samples_split', 5)
                ),
                'XGBoost': xgb.XGBRegressor(
                    random_state=42,
                    n_estimators=base_params.get('n_estimators', 200),
                    max_depth=base_params.get('max_depth', 8),
                    learning_rate=base_params.get('learning_rate', 0.1)
                ),
                'LightGBM': lgb.LGBMRegressor(
                    random_state=42,
                    n_estimators=base_params.get('n_estimators', 200),
                    max_depth=base_params.get('max_depth', 10),
                    learning_rate=base_params.get('learning_rate', 0.1),
                    verbose=-1
                )
            }
            
            # Train ensemble with optimized parameters
            best_models = {}
            for target_col in self.target_columns:
                if target_col not in y.columns:
                    continue
                    
                y_target = y[target_col]
                best_score = float('inf')
                best_model = None
                
                for name, algorithm in algorithms.items():
                    try:
                        # Train model
                        algorithm.fit(X, y_target)
                        
                        # Cross-validation score
                        cv_scores = cross_val_score(
                            algorithm, X, y_target, cv=3, 
                            scoring='neg_mean_absolute_error'
                        )
                        avg_score = -cv_scores.mean()
                        
                        if avg_score < best_score:
                            best_score = avg_score
                            best_model = algorithm
                            
                    except Exception as e:
                        self.logger.warning(f"Error training {name} for {target_col}: {e}")
                        continue
                        
                if best_model is not None:
                    best_models[target_col] = best_model
                    self.logger.info(f"Best model for {target_col}: {type(best_model).__name__} (MAE: {best_score:.2f})")
                    
            if best_models:
                self.models = best_models
                
                # Save model with feedback version
                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M")
                model_path = f"models/{self.position}_model_feedback_{timestamp}.pkl"
                self.save_model(model_path)
                
                return True
                
            return False
            
        except Exception as e:
            self.logger.error(f"Error training models with params: {e}")
            return False
            
    def apply_confidence_calibration(self, base_confidence, position=None):
        """Apply learned confidence calibration"""
        try:
            import json
            import os
            
            calibration_file = f"models/confidence_calibration_{position or self.position}.json"
            
            if not os.path.exists(calibration_file):
                return base_confidence
                
            with open(calibration_file, 'r') as f:
                calibration_map = json.load(f)
                
            # Find appropriate calibration bin
            for bin_range, calibrated_value in calibration_map.items():
                bin_start, bin_end = map(float, bin_range.split('-'))
                if bin_start <= base_confidence < bin_end:
                    # Blend original and calibrated confidence
                    alpha = 0.7  # Weight for calibrated confidence
                    return alpha * calibrated_value + (1 - alpha) * base_confidence
                    
            return base_confidence
            
        except Exception as e:
            self.logger.error(f"Error applying confidence calibration: {e}")
            return base_confidence
            
    def predict_with_feedback_enhancements(self, player_id, season, week):
        """Make predictions using feedback-enhanced model"""
        try:
            # Get base prediction
            base_prediction = self.predict_player_performance(player_id, season, week)
            
            if not base_prediction:
                return None
                
            # Apply confidence calibration
            calibrated_confidence = self.apply_confidence_calibration(
                base_prediction['confidence'], self.position
            )
            
            # Load feature weights if available
            feature_weights = self._load_feature_weights(season)
            
            # Apply feature weight adjustments to prediction
            if feature_weights:
                adjusted_predictions = self._apply_feature_weights(
                    base_prediction['predictions'], feature_weights, player_id, season, week
                )
                base_prediction['predictions'] = adjusted_predictions
                
            # Apply breaking news adjustments
            news_adjusted_prediction = self._apply_breaking_news_adjustments(
                base_prediction, player_id, season, week
            )
            
            news_adjusted_prediction['confidence'] = calibrated_confidence
            news_adjusted_prediction['model_version'] = 'v2.0_feedback_enhanced'
            
            return news_adjusted_prediction
            
        except Exception as e:
            self.logger.error(f"Error in feedback-enhanced prediction: {e}")
            return self.predict_player_performance(player_id, season, week)
            
    def _load_feature_weights(self, season):
        """Load learned feature weights"""
        try:
            import json
            import os
            
            weights_file = f"models/feature_weights_{self.position}_{season}.json"
            
            if os.path.exists(weights_file):
                with open(weights_file, 'r') as f:
                    return json.load(f)
                    
            return None
            
        except Exception as e:
            self.logger.error(f"Error loading feature weights: {e}")
            return None
            
    def _apply_feature_weights(self, predictions, weights, player_id, season, week):
        """Apply learned feature weights to adjust predictions"""
        try:
            # Get player features to understand risk factors
            features = self.feature_engineer.create_player_features(player_id, season, week)
            
            if not features:
                return predictions
                
            adjusted_predictions = predictions.copy()
            
            # Apply injury risk weight
            injury_risk = features.get('injury_risk_score', 0.1)
            if injury_risk > 0.3:  # High injury risk
                injury_weight = weights.get('injury_risk_weight', 1.0)
                fantasy_points = adjusted_predictions.get('target_fantasy_points', 0)
                adjusted_predictions['target_fantasy_points'] = fantasy_points * (2 - injury_weight)
                
            # Apply workload weight
            workload_risk = features.get('avg_snap_percentage', 50) / 100
            if workload_risk > 0.8:  # High workload
                workload_weight = weights.get('workload_weight', 1.0)
                fantasy_points = adjusted_predictions.get('target_fantasy_points', 0)
                adjusted_predictions['target_fantasy_points'] = fantasy_points * workload_weight
                
            # Apply consistency weight
            consistency = features.get('consistency_score', 0.5)
            if consistency < 0.3:  # Low consistency
                consistency_weight = weights.get('consistency_weight', 1.0)
                fantasy_points = adjusted_predictions.get('target_fantasy_points', 0)
                adjusted_predictions['target_fantasy_points'] = fantasy_points * (2 - consistency_weight)
                
            return adjusted_predictions
            
        except Exception as e:
            self.logger.error(f"Error applying feature weights: {e}")
            return predictions
            
    def _apply_breaking_news_adjustments(self, prediction, player_id, season, week):
        """Apply breaking news adjustments to predictions"""
        try:
            from src.monitoring.breaking_news_monitor import BreakingNewsMonitor
            
            # Check for recent breaking news affecting this player
            news_monitor = BreakingNewsMonitor()
            update_recommendations = news_monitor.check_prediction_updates_needed(season, week)
            
            adjusted_prediction = prediction.copy()
            
            # Find news affecting this specific player
            for recommendation in update_recommendations:
                for affected_player in recommendation['affected_players']:
                    if affected_player['player_id'] == player_id:
                        # Apply news impact
                        impact_magnitude = recommendation['impact_magnitude']
                        
                        # Adjust fantasy points
                        original_fp = adjusted_prediction['predictions'].get('target_fantasy_points', 0)
                        adjusted_fp = original_fp * (1 + impact_magnitude)
                        adjusted_fp = max(0, min(50, adjusted_fp))  # Bounds check
                        
                        adjusted_prediction['predictions']['target_fantasy_points'] = adjusted_fp
                        
                        # Adjust confidence based on news urgency
                        if recommendation['urgency'] == 'high':
                            confidence_penalty = 0.15
                        elif recommendation['urgency'] == 'medium':
                            confidence_penalty = 0.10
                        else:
                            confidence_penalty = 0.05
                            
                        adjusted_prediction['confidence'] = max(0.1, 
                            adjusted_prediction['confidence'] - confidence_penalty)
                        
                        # Mark as news-adjusted
                        adjusted_prediction['model_version'] = f"{adjusted_prediction.get('model_version', 'v2.0')}_news_adjusted"
                        
                        self.logger.info(f"Applied breaking news adjustment to player {player_id}: "
                                       f"FP: {original_fp:.1f} → {adjusted_fp:.1f}")
                        break
                        
            return adjusted_prediction
            
        except Exception as e:
            self.logger.error(f"Error applying breaking news adjustments: {e}")
            return prediction
            
    def load_model(self, filepath: str) -> bool:
        """Load trained model from file"""
        try:
            with open(filepath, 'rb') as f:
                model_data: Dict[str, Any] = pickle.load(f)
                
            self.models = model_data['models']
            self.scalers = model_data['scalers']
            self.feature_columns = model_data['feature_columns']
            self.position = model_data['position']
            self.label_encoders = model_data.get('label_encoders', {})
            
            self.logger.info(f"Model loaded from {filepath}")
            return True
        except Exception as e:
            self.logger.error(f"Error loading model: {e}")
            return False