import os
import logging
from datetime import datetime
from .prediction_model import NFLPredictionModel
from config.config import Config

class ModelManager:
    def __init__(self):
        self.models = {}
        self.logger = logging.getLogger(__name__)
        self.model_dir = "models"
        
        # Create model directory if it doesn't exist
        os.makedirs(self.model_dir, exist_ok=True)
        
    def train_all_position_models(self, season=2024):
        """Train models for all offensive positions"""
        self.logger.info(f"Training models for season {season}")
        
        positions = Config.OFFENSIVE_POSITIONS
        
        for position in positions:
            try:
                self.logger.info(f"Training model for {position}")
                
                # Create and train model
                model = NFLPredictionModel(position=position)
                success = model.train_models(season)
                
                if success:
                    # Save model
                    model_path = os.path.join(self.model_dir, f"{position}_model_{season}.pkl")
                    model.save_model(model_path)
                    
                    # Store in memory
                    self.models[position] = model
                    
                    self.logger.info(f"Successfully trained and saved {position} model")
                else:
                    self.logger.error(f"Failed to train {position} model")
                    
            except Exception as e:
                self.logger.error(f"Error training {position} model: {e}")
                
    def load_all_models(self, season=2024):
        """Load all trained models"""
        positions = Config.OFFENSIVE_POSITIONS
        
        for position in positions:
            try:
                model_path = os.path.join(self.model_dir, f"{position}_model_{season}.pkl")
                
                if os.path.exists(model_path):
                    model = NFLPredictionModel(position=position)
                    if model.load_model(model_path):
                        self.models[position] = model
                        self.logger.info(f"Loaded {position} model")
                    else:
                        self.logger.error(f"Failed to load {position} model")
                else:
                    self.logger.warning(f"Model file not found for {position}: {model_path}")
                    
            except Exception as e:
                self.logger.error(f"Error loading {position} model: {e}")
                
    def get_model(self, position):
        """Get model for specific position"""
        return self.models.get(position)
        
    def predict_weekly_top_performers(self, season, week, top_n=50):
        """Predict top performers across all positions for a week"""
        all_predictions = []
        
        for position, model in self.models.items():
            try:
                predictions = model.predict_top_performers(season, week, position, top_n)
                all_predictions.extend(predictions)
                
            except Exception as e:
                self.logger.error(f"Error predicting for {position}: {e}")
                
        # Sort all predictions by fantasy points
        all_predictions.sort(key=lambda x: x['predicted_fantasy_points'], reverse=True)
        
        # Group by position for balanced results
        position_results = {}
        for pred in all_predictions:
            pos = pred['position']
            if pos not in position_results:
                position_results[pos] = []
            if len(position_results[pos]) < top_n // len(Config.OFFENSIVE_POSITIONS):
                position_results[pos].append(pred)
                
        # Flatten results
        balanced_results = []
        for pos_preds in position_results.values():
            balanced_results.extend(pos_preds)
            
        return balanced_results[:top_n]
        
    def update_models_with_new_data(self, season):
        """Retrain models with latest data"""
        self.logger.info("Updating models with new data")
        
        # Retrain all models
        self.train_all_position_models(season)
        
        self.logger.info("Model update completed")
        
    def get_model_performance_summary(self):
        """Get performance summary of all models"""
        summary = {}
        
        for position, model in self.models.items():
            summary[position] = {
                'trained': True,
                'feature_count': len(model.feature_columns) if model.feature_columns else 0,
                'target_metrics': len(model.models)
            }
            
        return summary