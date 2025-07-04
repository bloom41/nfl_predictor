"""
Optimized prediction model with batch processing and performance improvements
"""
import pandas as pd
import numpy as np
import pickle
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import mean_absolute_error, r2_score
import xgboost as xgb
from sqlalchemy import func
from src.database.database_v2 import db_manager, db_session
from src.database.models import Prediction, ModelMetadata, Player, PlayerStats
from src.data_processing.feature_engineering import FeatureEngineer

logger = logging.getLogger(__name__)

class OptimizedNFLPredictionModel:
    """
    Optimized prediction model with batch processing, connection pooling,
    and performance improvements
    """
    
    def __init__(self, position: str = 'QB'):
        self.position = position
        self.models = {}
        self.scalers = {}
        self.feature_columns = []
        self.target_columns = [
            'target_passing_yards', 'target_passing_tds', 'target_rushing_yards',
            'target_rushing_tds', 'target_receiving_yards', 'target_receiving_tds',
            'target_fantasy_points'
        ]
        self.logger = logging.getLogger(f"{__name__}.{position}")
        self.feature_engineer = FeatureEngineer()
        
        # Performance optimizations
        self._feature_cache = {}
        self._player_cache = {}
        
        # Auto-load existing models
        self._auto_load_models()
    
    def _auto_load_models(self):
        """Automatically load existing models for the position"""
        import os
        model_filepath = f"models/{self.position}_model_2024.pkl"
        
        if os.path.exists(model_filepath):
            try:
                self.load_model(model_filepath)
                self.logger.info(f"Auto-loaded {self.position} model from {model_filepath}")
            except Exception as e:
                self.logger.warning(f"Failed to auto-load {self.position} model: {e}")
        else:
            self.logger.info(f"No existing model found for {self.position}")
    
    def load_model(self, filepath: str) -> bool:
        """Load trained model from file"""
        try:
            with open(filepath, 'rb') as f:
                model_data = pickle.load(f)
                
            self.models = model_data.get('models', {})
            self.scalers = model_data.get('scalers', {})
            self.feature_columns = model_data.get('feature_columns', [])
            
            if hasattr(model_data, 'label_encoders'):
                self.label_encoders = model_data.get('label_encoders', {})
            
            self.logger.info(f"Model loaded from {filepath}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error loading model: {e}")
            return False
    
    def predict_batch_players(self, player_ids: List[int], season: int, week: int) -> List[Dict[str, Any]]:
        """
        Predict performance for multiple players in a single batch operation
        Significantly reduces database queries and improves performance
        """
        if not player_ids:
            return []
        
        try:
            # Batch fetch all required data in a single query
            batch_data = self._fetch_batch_player_data(player_ids, season, week)
            
            if not batch_data:
                self.logger.warning("No batch data available for prediction")
                return []
            
            # Prepare features for all players at once
            features_df = self._prepare_batch_features(batch_data, season, week)
            
            if features_df.empty:
                self.logger.warning("No features could be prepared for batch")
                return []
            
            # Make batch predictions
            batch_predictions = self._make_batch_predictions(features_df)
            
            # Format results
            results = []
            for idx, row in features_df.iterrows():
                player_id = int(row['player_id'])
                player_data = batch_data.get(player_id, {})
                
                predictions = {}
                confidence_scores = []
                
                for target in self.target_columns:
                    if target in batch_predictions:
                        pred_value = batch_predictions[target][idx]
                        predictions[target] = float(pred_value)
                        confidence_scores.append(0.8)  # Model confidence
                
                avg_confidence = np.mean(confidence_scores) if confidence_scores else 0.5
                
                results.append({
                    'player_id': player_id,
                    'player_name': player_data.get('name', 'Unknown'),
                    'team': player_data.get('team', 'UNK'),
                    'position': player_data.get('position', self.position),
                    'season': season,
                    'week': week,
                    'predictions': predictions,
                    'confidence': avg_confidence
                })
            
            self.logger.info(f"Generated batch predictions for {len(results)} players")
            return results
            
        except Exception as e:
            self.logger.error(f"Error in batch prediction: {e}")
            return []
    
    def _fetch_batch_player_data(self, player_ids: List[int], season: int, week: int) -> Dict[int, Dict[str, Any]]:
        """
        Fetch all required player data in a single database query
        """
        def query_func(session):
            # Batch fetch players with their recent stats
            query = session.query(
                Player.id,
                Player.name,
                Player.team,
                Player.position,
                Player.age,
                Player.experience_years,
                PlayerStats.season,
                PlayerStats.week,
                PlayerStats.passing_yards,
                PlayerStats.passing_tds,
                PlayerStats.interceptions,
                PlayerStats.rushing_yards,
                PlayerStats.rushing_tds,
                PlayerStats.receiving_yards,
                PlayerStats.receiving_tds,
                PlayerStats.receptions,
                PlayerStats.fantasy_points
            ).outerjoin(
                PlayerStats,
                (Player.id == PlayerStats.player_id) & 
                (PlayerStats.season >= season - 1)  # Get current and last season
            ).filter(
                Player.id.in_(player_ids)
            ).all()
            
            # Organize data by player
            player_data = {}
            
            for row in query:
                player_id = row.id
                
                if player_id not in player_data:
                    player_data[player_id] = {
                        'id': row.id,
                        'name': row.name,
                        'team': row.team,
                        'position': row.position,
                        'age': row.age,
                        'experience_years': row.experience_years,
                        'stats': []
                    }
                
                # Add stats if available
                if row.season:
                    player_data[player_id]['stats'].append({
                        'season': row.season,
                        'week': row.week,
                        'passing_yards': row.passing_yards or 0,
                        'passing_tds': row.passing_tds or 0,
                        'interceptions': row.interceptions or 0,
                        'rushing_yards': row.rushing_yards or 0,
                        'rushing_tds': row.rushing_tds or 0,
                        'receiving_yards': row.receiving_yards or 0,
                        'receiving_tds': row.receiving_tds or 0,
                        'receptions': row.receptions or 0,
                        'fantasy_points': row.fantasy_points or 0
                    })
            
            return player_data
        
        return db_session.execute_readonly_query(query_func)
    
    def _prepare_batch_features(self, batch_data: Dict[int, Dict], season: int, week: int) -> pd.DataFrame:
        """
        Prepare features for all players in the batch
        """
        try:
            features_list = []
            
            for player_id, player_info in batch_data.items():
                # Calculate features for this player
                features = self._calculate_player_features(player_info, season, week)
                
                if features:
                    features['player_id'] = player_id
                    features_list.append(features)
            
            if not features_list:
                return pd.DataFrame()
            
            # Create DataFrame
            df = pd.DataFrame(features_list)
            
            # Ensure all expected feature columns are present
            for col in self.feature_columns:
                if col not in df.columns:
                    df[col] = 0
            
            # Select only the feature columns we trained on
            feature_cols = ['player_id'] + [col for col in self.feature_columns if col in df.columns]
            df = df[feature_cols]
            
            # Handle missing values
            numeric_columns = df.select_dtypes(include=[np.number]).columns
            df[numeric_columns] = df[numeric_columns].fillna(0)
            
            return df
            
        except Exception as e:
            self.logger.error(f"Error preparing batch features: {e}")
            return pd.DataFrame()
    
    def _calculate_player_features(self, player_info: Dict, season: int, week: int) -> Optional[Dict[str, float]]:
        """
        Calculate features for a single player
        Uses caching to improve performance
        """
        try:
            player_id = player_info['id']
            cache_key = f"{player_id}_{season}_{week}"
            
            # Check cache first
            if cache_key in self._feature_cache:
                return self._feature_cache[cache_key]
            
            features = {}
            
            # Basic player features
            features['age'] = player_info.get('age', 25)
            features['experience_years'] = player_info.get('experience_years', 1)
            
            # Encode team (simplified)
            team_mapping = {'BUF': 1, 'MIA': 2, 'NE': 3, 'NYJ': 4}  # Extend as needed
            features['team'] = team_mapping.get(player_info.get('team', ''), 0)
            
            # Calculate performance metrics from recent stats
            stats = player_info.get('stats', [])
            
            if stats:
                # Recent performance (last 4 games)
                recent_stats = sorted(stats, key=lambda x: (x['season'], x['week']), reverse=True)[:4]
                
                if recent_stats:
                    # Average recent performance
                    features['avg_fantasy_points'] = np.mean([s['fantasy_points'] for s in recent_stats])
                    features['avg_passing_yards'] = np.mean([s['passing_yards'] for s in recent_stats])
                    features['avg_passing_tds'] = np.mean([s['passing_tds'] for s in recent_stats])
                    features['avg_rushing_yards'] = np.mean([s['rushing_yards'] for s in recent_stats])
                    features['avg_rushing_tds'] = np.mean([s['rushing_tds'] for s in recent_stats])
                    features['avg_receiving_yards'] = np.mean([s['receiving_yards'] for s in recent_stats])
                    features['avg_receiving_tds'] = np.mean([s['receiving_tds'] for s in recent_stats])
                    features['avg_receptions'] = np.mean([s['receptions'] for s in recent_stats])
                    
                    # Performance consistency
                    fp_values = [s['fantasy_points'] for s in recent_stats]
                    features['fantasy_points_std'] = np.std(fp_values) if len(fp_values) > 1 else 0
                    
                    # Trending (last game vs average)
                    if len(recent_stats) >= 2:
                        last_game = recent_stats[0]['fantasy_points']
                        avg_previous = np.mean([s['fantasy_points'] for s in recent_stats[1:]])
                        features['trend_factor'] = (last_game - avg_previous) / max(avg_previous, 1)
                    else:
                        features['trend_factor'] = 0
            else:
                # Default values for players with no stats
                defaults = {
                    'avg_fantasy_points': 8.0,
                    'avg_passing_yards': 0,
                    'avg_passing_tds': 0,
                    'avg_rushing_yards': 0,
                    'avg_rushing_tds': 0,
                    'avg_receiving_yards': 0,
                    'avg_receiving_tds': 0,
                    'avg_receptions': 0,
                    'fantasy_points_std': 0,
                    'trend_factor': 0
                }
                features.update(defaults)
            
            # Position-specific adjustments
            if player_info.get('position') == 'QB':
                features['is_qb'] = 1
                features['is_rb'] = 0
                features['is_wr'] = 0
                features['is_te'] = 0
            elif player_info.get('position') == 'RB':
                features['is_qb'] = 0
                features['is_rb'] = 1
                features['is_wr'] = 0
                features['is_te'] = 0
            elif player_info.get('position') == 'WR':
                features['is_qb'] = 0
                features['is_rb'] = 0
                features['is_wr'] = 1
                features['is_te'] = 0
            elif player_info.get('position') == 'TE':
                features['is_qb'] = 0
                features['is_rb'] = 0
                features['is_wr'] = 0
                features['is_te'] = 1
            else:
                features['is_qb'] = 0
                features['is_rb'] = 0
                features['is_wr'] = 0
                features['is_te'] = 0
            
            # Cache the result
            self._feature_cache[cache_key] = features
            
            return features
            
        except Exception as e:
            self.logger.error(f"Error calculating features for player {player_info.get('id')}: {e}")
            return None
    
    def _make_batch_predictions(self, features_df: pd.DataFrame) -> Dict[str, np.ndarray]:
        """
        Make predictions for all players in the batch
        """
        try:
            if not self.models or not self.scalers:
                self.logger.error("No trained models available")
                return {}
            
            # Prepare features for prediction
            feature_columns = [col for col in self.feature_columns if col in features_df.columns]
            X = features_df[feature_columns].fillna(0)
            
            # Scale features
            if 'main' in self.scalers:
                X_scaled = self.scalers['main'].transform(X)
            else:
                X_scaled = X.values
            
            # Make predictions for each target
            predictions = {}
            
            for target in self.target_columns:
                if target in self.models:
                    try:
                        pred = self.models[target].predict(X_scaled)
                        # Ensure non-negative predictions for most stats
                        if target != 'interceptions':
                            pred = np.maximum(pred, 0)
                        predictions[target] = pred
                    except Exception as e:
                        self.logger.error(f"Error predicting {target}: {e}")
                        predictions[target] = np.zeros(len(X))
                else:
                    # Use default values if model not available
                    default_values = {
                        'target_fantasy_points': 10.0,
                        'target_passing_yards': 200.0,
                        'target_passing_tds': 1.5,
                        'target_rushing_yards': 20.0,
                        'target_rushing_tds': 0.3,
                        'target_receiving_yards': 40.0,
                        'target_receiving_tds': 0.4
                    }
                    predictions[target] = np.full(len(X), default_values.get(target, 0))
            
            return predictions
            
        except Exception as e:
            self.logger.error(f"Error making batch predictions: {e}")
            return {}
    
    def predict_top_performers_optimized(self, season: int, week: int, position: Optional[str] = None, top_n: int = 20) -> List[Dict[str, Any]]:
        """
        Optimized version of predict_top_performers using batch processing
        """
        try:
            # Get all relevant player IDs in a single query
            def get_player_ids(session):
                query = session.query(Player.id)
                
                if position:
                    query = query.filter(Player.position == position)
                elif self.position:
                    query = query.filter(Player.position == self.position)
                
                return [row.id for row in query.all()]
            
            player_ids = db_session.execute_readonly_query(get_player_ids)
            
            if not player_ids:
                self.logger.warning("No players found for prediction")
                return []
            
            # Make batch predictions
            predictions = self.predict_batch_players(player_ids, season, week)
            
            # Filter and sort by fantasy points
            valid_predictions = [
                pred for pred in predictions 
                if pred['predictions'].get('target_fantasy_points', 0) > 0
            ]
            
            # Sort by predicted fantasy points
            valid_predictions.sort(
                key=lambda x: x['predictions'].get('target_fantasy_points', 0), 
                reverse=True
            )
            
            return valid_predictions[:top_n]
            
        except Exception as e:
            self.logger.error(f"Error in optimized top performers prediction: {e}")
            return []
    
    def bulk_save_predictions(self, predictions_list: List[Dict[str, Any]]) -> bool:
        """
        Efficiently save multiple predictions using bulk operations
        """
        if not predictions_list:
            return True
        
        try:
            prediction_objects = []
            
            for pred_data in predictions_list:
                prediction = Prediction(
                    player_id=pred_data['player_id'],
                    season=pred_data.get('season', 2025),
                    week=pred_data.get('week', 1),
                    predicted_passing_yards=pred_data['predictions'].get('target_passing_yards', 0),
                    predicted_passing_tds=pred_data['predictions'].get('target_passing_tds', 0),
                    predicted_rushing_yards=pred_data['predictions'].get('target_rushing_yards', 0),
                    predicted_rushing_tds=pred_data['predictions'].get('target_rushing_tds', 0),
                    predicted_receiving_yards=pred_data['predictions'].get('target_receiving_yards', 0),
                    predicted_receiving_tds=pred_data['predictions'].get('target_receiving_tds', 0),
                    predicted_fantasy_points=pred_data['predictions'].get('target_fantasy_points', 0),
                    confidence_score=pred_data.get('confidence', 0.5),
                    model_version=f"{self.position}_v2.0_optimized"
                )
                prediction_objects.append(prediction)
            
            # Use bulk insert for better performance
            def bulk_insert(session):
                session.bulk_save_objects(prediction_objects)
                return len(prediction_objects)
            
            inserted_count = db_session.execute_query(bulk_insert)
            
            self.logger.info(f"Bulk saved {inserted_count} predictions to database")
            return True
            
        except Exception as e:
            self.logger.error(f"Error bulk saving predictions: {e}")
            return False
    
    def clear_cache(self):
        """Clear internal caches to free memory"""
        self._feature_cache.clear()
        self._player_cache.clear()
        self.logger.debug("Cleared prediction model caches")


# Backward compatibility wrapper
class NFLPredictionModel(OptimizedNFLPredictionModel):
    """
    Backward compatible version that maintains the same interface
    while using optimized implementations under the hood
    """
    
    def predict_player_performance(self, player_id: int, season: int, week: int) -> Optional[Dict[str, Any]]:
        """
        Single player prediction (maintains backward compatibility)
        """
        results = self.predict_batch_players([player_id], season, week)
        return results[0] if results else None
    
    def predict_top_performers(self, season: int, week: int, position: Optional[str] = None, top_n: int = 20) -> List[Dict[str, Any]]:
        """
        Top performers prediction (maintains backward compatibility)
        """
        return self.predict_top_performers_optimized(season, week, position, top_n)
    
    def save_predictions_to_db(self, predictions_list: List[Dict[str, Any]]):
        """
        Save predictions (maintains backward compatibility)
        """
        return self.bulk_save_predictions(predictions_list)


__all__ = ['NFLPredictionModel', 'OptimizedNFLPredictionModel']