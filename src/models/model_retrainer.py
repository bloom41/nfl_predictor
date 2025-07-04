#!/usr/bin/env python3
"""
Model Retrainer
Retrains prediction models using real collected NFL data
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import pickle
from pathlib import Path

from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import lightgbm as lgb

from src.utils.unified_database_operations import DatabaseSessionManager
from src.database.models import Player, ActualResults, PlayerStats
from src.utils.type_hint_utility import Position, Season, Week

logger = logging.getLogger(__name__)

@dataclass
class ModelTrainingData:
    """Container for model training data"""
    features: pd.DataFrame
    targets: pd.DataFrame
    feature_names: List[str]
    player_ids: List[int]
    position: Position

@dataclass 
class ModelPerformance:
    """Model performance metrics"""
    mae: float
    rmse: float
    r2: float
    cross_val_score: float
    feature_importance: Dict[str, float]

class ModelRetrainer:
    """Retrain prediction models using real NFL data"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.db_manager = DatabaseSessionManager()
        self.models_dir = Path("models")
        self.models_dir.mkdir(exist_ok=True)
        
        # Model parameters
        self.lgb_params = {
            'objective': 'regression',
            'metric': 'mae',
            'boosting_type': 'gbdt',
            'num_leaves': 31,
            'learning_rate': 0.05,
            'feature_fraction': 0.9,
            'bagging_fraction': 0.8,
            'bagging_freq': 5,
            'verbose': 0
        }
    
    def retrain_all_models(self, season: Season = 2024, min_weeks: int = 3) -> Dict[Position, ModelPerformance]:
        """Retrain models for all positions using real data"""
        self.logger.info(f"Starting model retraining for {season} season")
        
        results = {}
        positions = ['QB', 'RB', 'WR', 'TE']
        
        for position in positions:
            self.logger.info(f"Retraining {position} model...")
            
            try:
                # Prepare training data
                training_data = self._prepare_training_data(position, season, min_weeks)
                
                if training_data.features.empty:
                    self.logger.warning(f"No training data available for {position}")
                    continue
                
                # Train model
                model, performance = self._train_position_model(training_data)
                
                # Save model
                self._save_model(model, position, season)
                
                results[position] = performance
                self.logger.info(f"{position} model trained: MAE={performance.mae:.2f}, R²={performance.r2:.3f}")
                
            except Exception as e:
                self.logger.error(f"Error training {position} model: {e}")
                continue
        
        self._save_training_summary(results, season)
        return results
    
    def _prepare_training_data(self, position: Position, season: Season, min_weeks: int) -> ModelTrainingData:
        """Prepare training data for a specific position"""
        self.logger.info(f"Preparing training data for {position}")
        
        try:
            def get_training_data(session):
                # Get actual results with player info
                query = session.query(ActualResults, Player).join(
                    Player, ActualResults.player_id == Player.id
                ).filter(
                    Player.position == position,
                    ActualResults.data_source == 'RealNFLData'
                ).all()
                
                data = []
                for result, player in query:
                    data.append({
                        'player_id': player.id,
                        'player_name': player.name,
                        'team': player.team,
                        'position': player.position,
                        'week': result.week,
                        'season': result.season,
                        'opponent': result.opponent_team,
                        'is_home': result.is_home_game,
                        
                        # Stats
                        'passing_attempts': result.actual_passing_attempts or 0,
                        'passing_completions': result.actual_passing_completions or 0,
                        'passing_yards': result.actual_passing_yards or 0,
                        'passing_tds': result.actual_passing_tds or 0,
                        'interceptions': result.actual_interceptions or 0,
                        'rushing_attempts': result.actual_rushing_attempts or 0,
                        'rushing_yards': result.actual_rushing_yards or 0,
                        'rushing_tds': result.actual_rushing_tds or 0,
                        'targets': result.actual_targets or 0,
                        'receptions': result.actual_receptions or 0,
                        'receiving_yards': result.actual_receiving_yards or 0,
                        'receiving_tds': result.actual_receiving_tds or 0,
                        
                        # Target
                        'fantasy_points': result.actual_fantasy_points or 0
                    })
                
                return data
            
            raw_data = self.db_manager.execute_readonly(get_training_data)
            
            if not raw_data:
                self.logger.warning(f"No raw data found for {position}")
                return ModelTrainingData(pd.DataFrame(), pd.DataFrame(), [], [], position)
            
            # Convert to DataFrame
            df = pd.DataFrame(raw_data)
            
            # Filter players with minimum appearances
            player_game_counts = df['player_id'].value_counts()
            valid_players = player_game_counts[player_game_counts >= min_weeks].index
            df = df[df['player_id'].isin(valid_players)]
            
            if df.empty:
                self.logger.warning(f"No players with minimum {min_weeks} games for {position}")
                return ModelTrainingData(pd.DataFrame(), pd.DataFrame(), [], [], position)
            
            # Create features
            features_df = self._create_features(df, position)
            
            # Target variable
            targets_df = df[['fantasy_points']].copy()
            
            self.logger.info(f"Created {len(features_df)} training samples for {position}")
            self.logger.info(f"Features: {list(features_df.columns)}")
            
            return ModelTrainingData(
                features=features_df,
                targets=targets_df,
                feature_names=list(features_df.columns),
                player_ids=df['player_id'].tolist(),
                position=position
            )
            
        except Exception as e:
            self.logger.error(f"Error preparing training data for {position}: {e}")
            return ModelTrainingData(pd.DataFrame(), pd.DataFrame(), [], [], position)
    
    def _create_features(self, df: pd.DataFrame, position: Position) -> pd.DataFrame:
        """Create features for model training"""
        features = pd.DataFrame()
        
        # Basic stats features
        if position == 'QB':
            features['passing_attempts'] = df['passing_attempts']
            features['passing_completions'] = df['passing_completions']
            features['passing_yards'] = df['passing_yards']
            features['passing_tds'] = df['passing_tds']
            features['interceptions'] = df['interceptions']
            features['rushing_attempts'] = df['rushing_attempts']
            features['rushing_yards'] = df['rushing_yards']
            features['rushing_tds'] = df['rushing_tds']
            
            # Derived features
            features['completion_pct'] = df['passing_completions'] / (df['passing_attempts'] + 1)
            features['yards_per_attempt'] = df['passing_yards'] / (df['passing_attempts'] + 1)
            features['td_rate'] = df['passing_tds'] / (df['passing_attempts'] + 1)
            features['int_rate'] = df['interceptions'] / (df['passing_attempts'] + 1)
            
        elif position == 'RB':
            features['rushing_attempts'] = df['rushing_attempts']
            features['rushing_yards'] = df['rushing_yards']
            features['rushing_tds'] = df['rushing_tds']
            features['targets'] = df['targets']
            features['receptions'] = df['receptions']
            features['receiving_yards'] = df['receiving_yards']
            features['receiving_tds'] = df['receiving_tds']
            
            # Derived features
            features['yards_per_carry'] = df['rushing_yards'] / (df['rushing_attempts'] + 1)
            features['catch_rate'] = df['receptions'] / (df['targets'] + 1)
            features['yards_per_target'] = df['receiving_yards'] / (df['targets'] + 1)
            features['total_touches'] = df['rushing_attempts'] + df['receptions']
            
        elif position in ['WR', 'TE']:
            features['targets'] = df['targets']
            features['receptions'] = df['receptions']
            features['receiving_yards'] = df['receiving_yards']
            features['receiving_tds'] = df['receiving_tds']
            features['rushing_attempts'] = df['rushing_attempts']
            features['rushing_yards'] = df['rushing_yards']
            features['rushing_tds'] = df['rushing_tds']
            
            # Derived features
            features['catch_rate'] = df['receptions'] / (df['targets'] + 1)
            features['yards_per_target'] = df['receiving_yards'] / (df['targets'] + 1)
            features['yards_per_reception'] = df['receiving_yards'] / (df['receptions'] + 1)
            features['td_rate'] = df['receiving_tds'] / (df['targets'] + 1)
        
        # Common features for all positions
        features['is_home'] = df['is_home'].astype(int)
        features['week'] = df['week']
        
        # Fill NaN values
        features = features.fillna(0)
        
        return features
    
    def _train_position_model(self, training_data: ModelTrainingData) -> Tuple[Any, ModelPerformance]:
        """Train model for a specific position"""
        X = training_data.features
        y = training_data.targets['fantasy_points']
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        # Scale features
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        # Train LightGBM model
        train_data = lgb.Dataset(X_train_scaled, label=y_train)
        model = lgb.train(
            self.lgb_params,
            train_data,
            num_boost_round=100,
            valid_sets=[train_data],
            callbacks=[lgb.early_stopping(10), lgb.log_evaluation(0)]
        )
        
        # Make predictions
        y_pred = model.predict(X_test_scaled, num_iteration=model.best_iteration)
        
        # Calculate performance metrics
        mae = mean_absolute_error(y_test, y_pred)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        r2 = r2_score(y_test, y_pred)
        
        # Cross-validation score
        cv_scores = cross_val_score(
            RandomForestRegressor(n_estimators=50, random_state=42),
            X_train_scaled, y_train, cv=3, scoring='neg_mean_absolute_error'
        )
        cv_score = -cv_scores.mean()
        
        # Feature importance
        feature_importance = dict(zip(
            training_data.feature_names,
            model.feature_importance(importance_type='gain')
        ))
        
        # Create model package with scaler
        model_package = {
            'model': model,
            'scaler': scaler,
            'feature_names': training_data.feature_names,
            'position': training_data.position,
            'training_date': datetime.now(),
            'training_samples': len(X_train)
        }
        
        performance = ModelPerformance(
            mae=mae,
            rmse=rmse,
            r2=r2,
            cross_val_score=cv_score,
            feature_importance=feature_importance
        )
        
        return model_package, performance
    
    def _save_model(self, model_package: Dict[str, Any], position: Position, season: Season) -> None:
        """Save trained model to disk"""
        try:
            model_path = self.models_dir / f"{position}_model_{season}_retrained.pkl"
            
            with open(model_path, 'wb') as f:
                pickle.dump(model_package, f)
            
            self.logger.info(f"Saved {position} model to {model_path}")
            
        except Exception as e:
            self.logger.error(f"Error saving {position} model: {e}")
    
    def _save_training_summary(self, results: Dict[Position, ModelPerformance], season: Season) -> None:
        """Save training summary"""
        try:
            summary_path = self.models_dir / f"retraining_summary_{season}.txt"
            
            with open(summary_path, 'w') as f:
                f.write(f"Model Retraining Summary - {season} Season\n")
                f.write("=" * 50 + "\n")
                f.write(f"Training Date: {datetime.now()}\n\n")
                
                for position, performance in results.items():
                    f.write(f"{position} Model Performance:\n")
                    f.write(f"  MAE: {performance.mae:.2f}\n")
                    f.write(f"  RMSE: {performance.rmse:.2f}\n")
                    f.write(f"  R²: {performance.r2:.3f}\n")
                    f.write(f"  CV Score: {performance.cross_val_score:.2f}\n")
                    f.write(f"  Top Features:\n")
                    
                    # Sort features by importance
                    sorted_features = sorted(
                        performance.feature_importance.items(),
                        key=lambda x: x[1], reverse=True
                    )
                    
                    for feature, importance in sorted_features[:5]:
                        f.write(f"    {feature}: {importance:.1f}\n")
                    f.write("\n")
            
            self.logger.info(f"Saved training summary to {summary_path}")
            
        except Exception as e:
            self.logger.error(f"Error saving training summary: {e}")

# Convenience functions
def retrain_models(season: Season = 2024, min_weeks: int = 3) -> Dict[Position, ModelPerformance]:
    """Retrain all models using real data"""
    retrainer = ModelRetrainer()
    return retrainer.retrain_all_models(season, min_weeks)

if __name__ == "__main__":
    print("🏈 NFL MODEL RETRAINING")
    print("=" * 40)
    
    # Retrain all models
    results = retrain_models(2024, 3)
    
    if results:
        print("\n✅ Model Retraining Complete!")
        print("\nPerformance Summary:")
        
        for position, performance in results.items():
            print(f"\n{position}:")
            print(f"  MAE: {performance.mae:.2f} fantasy points")
            print(f"  R²: {performance.r2:.3f}")
    else:
        print("\n❌ No models could be retrained")