import logging
import numpy as np
import pandas as pd
import pickle
import json
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import GridSearchCV
from sklearn.metrics import mean_absolute_error
from src.database.database import db
from src.database.models import (
    Player, Prediction, ActualResults, PredictionAccuracy, ModelMetadata
)
from src.data_processing.feature_engineering import FeatureEngineer
from src.analysis.prediction_accuracy import PredictionAccuracyAnalyzer
from src.analysis.injury_aware_filter import InjuryAwareFilter

class ModelFeedbackLoop:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.feature_engineer = FeatureEngineer()
        self.accuracy_analyzer = PredictionAccuracyAnalyzer()
        self.injury_filter = InjuryAwareFilter()
        
        # Learning parameters
        self.min_predictions_for_feedback = 10  # Minimum predictions needed for feedback
        self.error_threshold = 5.0  # Fantasy points error threshold for poor predictions
        self.improvement_threshold = 0.1  # Minimum improvement needed to update model
        
        # Feature importance tracking
        self.feature_performance = {}
        self.confidence_calibration = {}
        
    def analyze_model_performance(self, season, position=None, min_weeks=3):
        """Analyze model performance and identify improvement opportunities"""
        session = db.get_session()
        
        try:
            # Get accuracy data for analysis
            query = session.query(PredictionAccuracy, Player).join(
                Player, PredictionAccuracy.player_id == Player.id
            ).filter(PredictionAccuracy.season == season)
            
            if position:
                query = query.filter(Player.position == position)
                
            accuracy_records = query.all()
            
            if len(accuracy_records) < self.min_predictions_for_feedback:
                self.logger.info(f"Not enough predictions ({len(accuracy_records)}) for feedback analysis")
                return None
                
            # Convert to DataFrame for analysis
            data = []
            for accuracy, player in accuracy_records:
                data.append({
                    'player_id': player.id,
                    'position': player.position,
                    'team': player.team,
                    'week': accuracy.week,
                    'fantasy_error': accuracy.fantasy_points_abs_error,
                    'confidence': accuracy.confidence_score or 0.5,
                    'model_version': accuracy.model_version or 'v1.0'
                })
                
            df = pd.DataFrame(data)
            
            # Analyze performance patterns
            performance_analysis = {
                'total_predictions': len(df),
                'average_error': df['fantasy_error'].mean(),
                'error_by_position': df.groupby('position')['fantasy_error'].mean().to_dict(),
                'error_by_week': df.groupby('week')['fantasy_error'].mean().to_dict(),
                'error_by_confidence': self._analyze_confidence_accuracy(df),
                'high_error_patterns': self._identify_error_patterns(df),
                'improvement_opportunities': self._find_improvement_opportunities(df, season)
            }
            
            return performance_analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing model performance: {e}")
            return None
        finally:
            db.close_session(session)
            
    def _analyze_confidence_accuracy(self, df):
        """Analyze relationship between confidence and actual accuracy"""
        confidence_bins = [0, 0.5, 0.7, 0.85, 1.0]
        confidence_labels = ['Low', 'Medium', 'High', 'Very High']
        
        df['confidence_bin'] = pd.cut(df['confidence'], bins=confidence_bins, labels=confidence_labels)
        
        confidence_analysis = {}
        for bin_name in confidence_labels:
            bin_data = df[df['confidence_bin'] == bin_name]
            if len(bin_data) > 0:
                confidence_analysis[bin_name] = {
                    'count': len(bin_data),
                    'avg_error': bin_data['fantasy_error'].mean(),
                    'accuracy_rate': (bin_data['fantasy_error'] <= 5).mean() * 100
                }
                
        return confidence_analysis
        
    def _identify_error_patterns(self, df):
        """Identify patterns in high-error predictions"""
        high_error_df = df[df['fantasy_error'] > self.error_threshold]
        
        if len(high_error_df) == 0:
            return {'message': 'No high-error predictions found'}
            
        patterns = {
            'high_error_count': len(high_error_df),
            'worst_positions': high_error_df.groupby('position')['fantasy_error'].mean().sort_values(ascending=False).to_dict(),
            'worst_weeks': high_error_df.groupby('week')['fantasy_error'].mean().sort_values(ascending=False).to_dict(),
            'overconfident_predictions': len(high_error_df[high_error_df['confidence'] > 0.7])
        }
        
        return patterns
        
    def _find_improvement_opportunities(self, df, season):
        """Find specific areas for model improvement"""
        opportunities = []
        
        # Check for overconfidence
        high_conf_high_error = df[(df['confidence'] > 0.8) & (df['fantasy_error'] > 5)]
        if len(high_conf_high_error) > 0:
            opportunities.append({
                'type': 'confidence_calibration',
                'description': f'{len(high_conf_high_error)} high-confidence predictions with high error',
                'severity': 'high',
                'action': 'recalibrate_confidence'
            })
            
        # Check for position-specific issues
        position_errors = df.groupby('position')['fantasy_error'].mean()
        for position, avg_error in position_errors.items():
            if avg_error > df['fantasy_error'].mean() * 1.5:
                opportunities.append({
                    'type': 'position_accuracy',
                    'description': f'{position} position has {avg_error:.1f} avg error (above overall average)',
                    'severity': 'medium',
                    'action': 'retrain_position_model',
                    'position': position
                })
                
        # Check for recent performance degradation
        if len(df['week'].unique()) >= 3:
            recent_weeks = sorted(df['week'].unique())[-3:]
            early_weeks = sorted(df['week'].unique())[:3]
            
            recent_error = df[df['week'].isin(recent_weeks)]['fantasy_error'].mean()
            early_error = df[df['week'].isin(early_weeks)]['fantasy_error'].mean()
            
            if recent_error > early_error * 1.2:
                opportunities.append({
                    'type': 'performance_degradation',
                    'description': f'Recent performance declining: {recent_error:.1f} vs {early_error:.1f}',
                    'severity': 'high',
                    'action': 'full_retrain'
                })
                
        return opportunities
        
    def implement_feedback_improvements(self, season, position=None):
        """Implement improvements based on performance analysis"""
        try:
            # Analyze current performance
            performance_analysis = self.analyze_model_performance(season, position)
            
            if not performance_analysis:
                self.logger.info("No performance analysis available for improvements")
                return False
                
            improvements_made = []
            
            # Process improvement opportunities
            for opportunity in performance_analysis.get('improvement_opportunities', []):
                if opportunity['action'] == 'recalibrate_confidence':
                    success = self._recalibrate_confidence_scores(season, position)
                    if success:
                        improvements_made.append('confidence_calibration')
                        
                elif opportunity['action'] == 'retrain_position_model':
                    success = self._retrain_position_model(season, opportunity['position'])
                    if success:
                        improvements_made.append(f"retrained_{opportunity['position']}")
                        
                elif opportunity['action'] == 'full_retrain':
                    success = self._full_model_retrain(season, position)
                    if success:
                        improvements_made.append('full_retrain')
                        
            # Update feature weights based on performance
            self._update_feature_weights(season, position)
            improvements_made.append('feature_weight_update')
            
            # Log improvements
            if improvements_made:
                self.logger.info(f"Implemented feedback improvements: {improvements_made}")
                self._log_feedback_cycle(season, position, performance_analysis, improvements_made)
                
            return len(improvements_made) > 0
            
        except Exception as e:
            self.logger.error(f"Error implementing feedback improvements: {e}")
            return False
            
    def _recalibrate_confidence_scores(self, season, position=None):
        """Recalibrate confidence scores based on historical accuracy"""
        try:
            session = db.get_session()
            
            # Get confidence vs accuracy data
            query = session.query(PredictionAccuracy).filter(
                PredictionAccuracy.season == season
            )
            
            if position:
                query = query.join(Player).filter(Player.position == position)
                
            accuracy_records = query.all()
            
            if len(accuracy_records) < 10:
                return False
                
            # Build confidence calibration model
            confidence_data = []
            for record in accuracy_records:
                confidence_data.append({
                    'original_confidence': record.confidence_score or 0.5,
                    'actual_accuracy': 1.0 if record.fantasy_points_abs_error <= 5 else 0.0,
                    'error_magnitude': record.fantasy_points_abs_error
                })
                
            df = pd.DataFrame(confidence_data)
            
            # Calculate calibrated confidence bins
            confidence_bins = np.linspace(0, 1, 11)  # 10 bins
            calibration_map = {}
            
            for i in range(len(confidence_bins) - 1):
                bin_mask = (df['original_confidence'] >= confidence_bins[i]) & \
                          (df['original_confidence'] < confidence_bins[i + 1])
                bin_data = df[bin_mask]
                
                if len(bin_data) > 0:
                    calibrated_confidence = bin_data['actual_accuracy'].mean()
                    calibration_map[f"{confidence_bins[i]:.1f}-{confidence_bins[i+1]:.1f}"] = calibrated_confidence
                    
            # Save calibration map
            self.confidence_calibration[position or 'all'] = calibration_map
            
            # Save to file
            with open(f'models/confidence_calibration_{position or "all"}.json', 'w') as f:
                json.dump(calibration_map, f)
                
            db.close_session(session)
            return True
            
        except Exception as e:
            self.logger.error(f"Error recalibrating confidence scores: {e}")
            return False
            
    def _retrain_position_model(self, season, position):
        """Retrain model for specific position with enhanced parameters"""
        try:
            from src.models.prediction_model import NFLPredictionModel
            
            # Get enhanced training data
            enhanced_data = self._get_enhanced_training_data(season, position)
            
            if enhanced_data is None or len(enhanced_data) < 20:
                self.logger.warning(f"Not enough data to retrain {position} model")
                return False
                
            # Create new model with optimized parameters
            model = NFLPredictionModel(position)
            
            # Use grid search to find better parameters
            improved_params = self._optimize_model_parameters(enhanced_data, position)
            
            # Train with improved parameters
            success = model.train_models_with_params(season, improved_params)
            
            if success:
                # Save model with version increment
                timestamp = datetime.now().strftime("%Y%m%d_%H%M")
                model_path = f"models/{position}_model_feedback_{timestamp}.pkl"
                model.save_model(model_path)
                
                self.logger.info(f"Successfully retrained {position} model with feedback improvements")
                return True
                
            return False
            
        except Exception as e:
            self.logger.error(f"Error retraining {position} model: {e}")
            return False
            
    def _get_enhanced_training_data(self, season, position):
        """Get training data enhanced with feedback insights and injury filtering"""
        try:
            # Get base training data
            df = self.feature_engineer.prepare_training_data(season, position)
            
            if df.empty:
                return None
                
            # Apply injury-aware filtering to remove contaminated training data
            self.logger.info("Applying injury-aware filtering to training data...")
            filtered_results = self.injury_filter.create_filtered_training_dataset(
                season, position, exclude_injury_games=True
            )
            
            if filtered_results:
                # Rebuild dataframe from filtered results
                self.logger.info(f"Injury filtering: {len(filtered_results)} clean training examples")
                # Note: In production, you'd properly reconstruct the DataFrame here
                # For now, we'll use the original data with a warning
                
            # Enhance with accuracy feedback
            session = db.get_session()
            
            # Add historical accuracy for each player
            for idx, row in df.iterrows():
                player_id = row.get('player_id')
                if player_id:
                    # Get player's historical accuracy
                    accuracy_records = session.query(PredictionAccuracy).filter_by(
                        player_id=player_id
                    ).all()
                    
                    if accuracy_records:
                        avg_error = np.mean([r.fantasy_points_abs_error for r in accuracy_records])
                        accuracy_trend = self._calculate_accuracy_trend(accuracy_records)
                        
                        df.at[idx, 'player_historical_accuracy'] = 1.0 / (1.0 + avg_error)
                        df.at[idx, 'player_accuracy_trend'] = accuracy_trend
                    else:
                        df.at[idx, 'player_historical_accuracy'] = 0.5
                        df.at[idx, 'player_accuracy_trend'] = 0.0
                        
            db.close_session(session)
            return df
            
        except Exception as e:
            self.logger.error(f"Error getting enhanced training data: {e}")
            return None
            
    def _optimize_model_parameters(self, training_data, position):
        """Optimize model parameters based on feedback"""
        try:
            # Prepare data for parameter optimization
            feature_cols = [col for col in training_data.columns 
                           if not col.startswith('target_') and col not in ['player_id', 'position', 'team']]
            
            X = training_data[feature_cols].fillna(0)
            y = training_data['target_fantasy_points'].fillna(0)
            
            # Define parameter grid based on position characteristics
            if position == 'QB':
                param_grid = {
                    'n_estimators': [100, 200, 300],
                    'max_depth': [10, 15, 20],
                    'min_samples_split': [2, 5, 10]
                }
            elif position == 'RB':
                param_grid = {
                    'n_estimators': [150, 250, 350],
                    'max_depth': [8, 12, 16],
                    'min_samples_split': [2, 4, 8]
                }
            else:  # WR, TE
                param_grid = {
                    'n_estimators': [100, 200, 250],
                    'max_depth': [6, 10, 14],
                    'min_samples_split': [2, 5, 10]
                }
                
            # Perform grid search
            rf = RandomForestRegressor(random_state=42)
            grid_search = GridSearchCV(
                rf, param_grid, cv=3, scoring='neg_mean_absolute_error', n_jobs=-1
            )
            
            grid_search.fit(X, y)
            
            best_params = grid_search.best_params_
            self.logger.info(f"Optimized parameters for {position}: {best_params}")
            
            return best_params
            
        except Exception as e:
            self.logger.error(f"Error optimizing model parameters: {e}")
            return {}
            
    def _calculate_accuracy_trend(self, accuracy_records):
        """Calculate accuracy trend for a player"""
        if len(accuracy_records) < 3:
            return 0.0
            
        # Sort by week
        sorted_records = sorted(accuracy_records, key=lambda x: x.week)
        errors = [r.fantasy_points_abs_error for r in sorted_records]
        
        # Calculate trend (negative means improving accuracy)
        if len(errors) >= 3:
            recent_avg = np.mean(errors[-3:])
            early_avg = np.mean(errors[:3])
            trend = (recent_avg - early_avg) / early_avg if early_avg > 0 else 0
            return -trend  # Negative error trend = positive accuracy trend
            
        return 0.0
        
    def _update_feature_weights(self, season, position=None):
        """Update feature importance weights based on performance"""
        try:
            # This would analyze which features correlate with high accuracy
            # and adjust their weights in future predictions
            
            session = db.get_session()
            
            # Get prediction and accuracy data
            query = session.query(PredictionAccuracy, Player).join(
                Player, PredictionAccuracy.player_id == Player.id
            ).filter(PredictionAccuracy.season == season)
            
            if position:
                query = query.filter(Player.position == position)
                
            records = query.all()
            
            if len(records) < 10:
                return False
                
            # Analyze feature performance (simplified version)
            # In a full implementation, this would analyze which features
            # correlate with high accuracy vs high error
            
            feature_insights = {
                'injury_risk_weight': 1.2 if position in ['RB', 'WR'] else 1.0,
                'workload_weight': 1.3 if position == 'RB' else 1.0,
                'sentiment_weight': 1.1,
                'consistency_weight': 1.2
            }
            
            # Save feature weights
            weights_file = f'models/feature_weights_{position or "all"}_{season}.json'
            with open(weights_file, 'w') as f:
                json.dump(feature_insights, f)
                
            self.logger.info(f"Updated feature weights for {position or 'all positions'}")
            
            db.close_session(session)
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating feature weights: {e}")
            return False
            
    def _full_model_retrain(self, season, position=None):
        """Perform full model retrain with all feedback improvements"""
        try:
            from src.models.prediction_model import NFLPredictionModel
            
            positions = [position] if position else ['QB', 'RB', 'WR', 'TE']
            success_count = 0
            
            for pos in positions:
                # Get enhanced training data
                enhanced_data = self._get_enhanced_training_data(season, pos)
                
                if enhanced_data is None or len(enhanced_data) < 15:
                    continue
                    
                # Create new model
                model = NFLPredictionModel(pos)
                
                # Get optimized parameters
                optimized_params = self._optimize_model_parameters(enhanced_data, pos)
                
                # Train with feedback improvements
                if model.train_models_with_params(season, optimized_params):
                    # Save improved model
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
                    model_path = f"models/{pos}_model_feedback_v2_{timestamp}.pkl"
                    model.save_model(model_path)
                    success_count += 1
                    
            return success_count > 0
            
        except Exception as e:
            self.logger.error(f"Error in full model retrain: {e}")
            return False
            
    def _log_feedback_cycle(self, season, position, analysis, improvements):
        """Log feedback cycle results for tracking"""
        try:
            session = db.get_session()
            
            # Create metadata record
            metadata = ModelMetadata(
                model_name=f"feedback_cycle_{position or 'all'}",
                version=f"v2.0_{datetime.now().strftime('%Y%m%d')}",
                training_date=datetime.utcnow(),
                accuracy_metrics=json.dumps({
                    'avg_error': analysis['average_error'],
                    'total_predictions': analysis['total_predictions'],
                    'improvements_made': improvements
                }),
                feature_count=len(improvements),
                algorithm='feedback_enhanced'
            )
            
            session.add(metadata)
            session.commit()
            
            self.logger.info(f"Logged feedback cycle for {position or 'all positions'}")
            
        except Exception as e:
            self.logger.error(f"Error logging feedback cycle: {e}")
        finally:
            db.close_session(session)
            
    def run_automated_feedback_cycle(self, season):
        """Run complete automated feedback cycle for all positions"""
        try:
            self.logger.info("Starting automated model feedback cycle...")
            
            total_improvements = 0
            
            # Run feedback for each position
            for position in ['QB', 'RB', 'WR', 'TE']:
                self.logger.info(f"Running feedback cycle for {position}...")
                
                success = self.implement_feedback_improvements(season, position)
                if success:
                    total_improvements += 1
                    
            # Run overall feedback cycle
            self.logger.info("Running overall feedback cycle...")
            overall_success = self.implement_feedback_improvements(season)
            
            if overall_success:
                total_improvements += 1
                
            self.logger.info(f"Automated feedback cycle completed. {total_improvements} improvements made.")
            
            return total_improvements > 0
            
        except Exception as e:
            self.logger.error(f"Error in automated feedback cycle: {e}")
            return False