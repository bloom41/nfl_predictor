import logging
import numpy as np
import pandas as pd
from datetime import datetime
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from src.database.database import db
from src.database.models import (
    Prediction, ActualResults, PredictionAccuracy, Player, ModelMetadata
)

class PredictionAccuracyAnalyzer:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def analyze_prediction_accuracy(self, season, week=None):
        """Analyze prediction accuracy for a specific season/week"""
        session = db.get_session()
        
        try:
            # Build query for predictions and actual results
            query = session.query(Prediction, ActualResults, Player).join(
                ActualResults, 
                (Prediction.player_id == ActualResults.player_id) &
                (Prediction.season == ActualResults.season) &
                (Prediction.week == ActualResults.week)
            ).join(
                Player, Prediction.player_id == Player.id
            ).filter(Prediction.season == season)
            
            if week:
                query = query.filter(Prediction.week == week)
                
            results = query.all()
            
            if not results:
                self.logger.warning(f"No matching predictions and actual results found for season {season}")
                return None
                
            # Process accuracy metrics
            accuracy_data = []
            for prediction, actual, player in results:
                accuracy_metrics = self._calculate_accuracy_metrics(prediction, actual, player)
                if accuracy_metrics:
                    accuracy_data.append(accuracy_metrics)
                    
            if not accuracy_data:
                return None
                
            # Store individual accuracy records
            self._store_accuracy_records(accuracy_data)
            
            # Calculate aggregate metrics
            aggregate_metrics = self._calculate_aggregate_metrics(accuracy_data)
            
            return {
                'season': season,
                'week': week,
                'total_predictions': len(accuracy_data),
                'individual_accuracy': accuracy_data,
                'aggregate_metrics': aggregate_metrics
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing prediction accuracy: {e}")
            return None
        finally:
            db.close_session(session)
            
    def _calculate_accuracy_metrics(self, prediction, actual, player):
        """Calculate accuracy metrics for a single prediction"""
        try:
            predicted_fp = prediction.predicted_fantasy_points or 0
            actual_fp = actual.actual_fantasy_points or 0
            
            # Skip if actual fantasy points is 0 (player didn't play)
            if actual_fp == 0:
                return None
                
            # Calculate errors
            fantasy_error = predicted_fp - actual_fp
            fantasy_abs_error = abs(fantasy_error)
            fantasy_percent_error = (fantasy_error / actual_fp * 100) if actual_fp != 0 else 0
            
            # Calculate other stat errors
            passing_error = (prediction.predicted_passing_yards or 0) - (actual.actual_passing_yards or 0)
            rushing_error = (prediction.predicted_rushing_yards or 0) - (actual.actual_rushing_yards or 0)
            receiving_error = (prediction.predicted_receiving_yards or 0) - (actual.actual_receiving_yards or 0)
            
            # Accuracy flags
            within_5_points = fantasy_abs_error <= 5
            within_10_points = fantasy_abs_error <= 10
            within_20_percent = abs(fantasy_percent_error) <= 20
            
            # Accuracy grade
            accuracy_grade = self._calculate_accuracy_grade(fantasy_abs_error, actual_fp)
            
            return {
                'prediction_id': prediction.id,
                'player_id': player.id,
                'player_name': player.name,
                'position': player.position,
                'team': player.team,
                'season': prediction.season,
                'week': prediction.week,
                'predicted_fantasy_points': predicted_fp,
                'actual_fantasy_points': actual_fp,
                'fantasy_points_error': fantasy_error,
                'fantasy_points_abs_error': fantasy_abs_error,
                'fantasy_points_percent_error': fantasy_percent_error,
                'passing_yards_error': passing_error,
                'rushing_yards_error': rushing_error,
                'receiving_yards_error': receiving_error,
                'was_within_5_points': within_5_points,
                'was_within_10_points': within_10_points,
                'was_within_20_percent': within_20_percent,
                'model_version': prediction.model_version or 'v1.0',
                'confidence_score': prediction.confidence_score or 0.5,
                'accuracy_grade': accuracy_grade
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating accuracy metrics: {e}")
            return None
            
    def _calculate_accuracy_grade(self, abs_error, actual_points):
        """Calculate letter grade for prediction accuracy"""
        if actual_points == 0:
            return 'F'
            
        percent_error = (abs_error / actual_points) * 100
        
        if percent_error <= 10:
            return 'A'
        elif percent_error <= 20:
            return 'B'
        elif percent_error <= 35:
            return 'C'
        elif percent_error <= 50:
            return 'D'
        else:
            return 'F'
            
    def _store_accuracy_records(self, accuracy_data):
        """Store individual accuracy records in database"""
        session = db.get_session()
        
        try:
            for data in accuracy_data:
                # Check if accuracy record already exists
                existing = session.query(PredictionAccuracy).filter_by(
                    prediction_id=data['prediction_id'],
                    player_id=data['player_id'],
                    season=data['season'],
                    week=data['week']
                ).first()
                
                if existing:
                    # Update existing record
                    for key, value in data.items():
                        if hasattr(existing, key) and key not in ['prediction_id', 'player_id', 'season', 'week']:
                            setattr(existing, key, value)
                else:
                    # Create new record (exclude non-database fields)
                    db_data = {k: v for k, v in data.items() 
                              if k not in ['player_name', 'position', 'team', 'predicted_fantasy_points', 'actual_fantasy_points']}
                    accuracy_record = PredictionAccuracy(**db_data)
                    session.add(accuracy_record)
                    
            session.commit()
            self.logger.info(f"Stored {len(accuracy_data)} accuracy records")
            
        except Exception as e:
            session.rollback()
            self.logger.error(f"Error storing accuracy records: {e}")
        finally:
            db.close_session(session)
            
    def _calculate_aggregate_metrics(self, accuracy_data):
        """Calculate aggregate accuracy metrics"""
        try:
            df = pd.DataFrame(accuracy_data)
            
            # Overall metrics
            mae_fantasy = df['fantasy_points_abs_error'].mean()
            rmse_fantasy = np.sqrt(df['fantasy_points_error'].pow(2).mean())
            mape_fantasy = df['fantasy_points_percent_error'].abs().mean()
            
            # Accuracy percentages
            within_5_pct = (df['was_within_5_points'].sum() / len(df)) * 100
            within_10_pct = (df['was_within_10_points'].sum() / len(df)) * 100
            within_20_percent_pct = (df['was_within_20_percent'].sum() / len(df)) * 100
            
            # Grade distribution
            grade_dist = df['accuracy_grade'].value_counts().to_dict()
            
            # Position-specific metrics
            position_metrics = {}
            for position in df['position'].unique():
                pos_df = df[df['position'] == position]
                position_metrics[position] = {
                    'count': len(pos_df),
                    'mae_fantasy': pos_df['fantasy_points_abs_error'].mean(),
                    'within_10_points_pct': (pos_df['was_within_10_points'].sum() / len(pos_df)) * 100,
                    'avg_confidence': pos_df['confidence_score'].mean()
                }
                
            # Confidence analysis
            high_conf = df[df['confidence_score'] >= 0.7]
            low_conf = df[df['confidence_score'] < 0.7]
            
            return {
                'overall': {
                    'mae_fantasy_points': round(mae_fantasy, 2),
                    'rmse_fantasy_points': round(rmse_fantasy, 2),
                    'mape_fantasy_points': round(mape_fantasy, 2),
                    'within_5_points_pct': round(within_5_pct, 1),
                    'within_10_points_pct': round(within_10_pct, 1),
                    'within_20_percent_pct': round(within_20_percent_pct, 1)
                },
                'grade_distribution': grade_dist,
                'position_breakdown': position_metrics,
                'confidence_analysis': {
                    'high_confidence_accuracy': round(high_conf['fantasy_points_abs_error'].mean(), 2) if len(high_conf) > 0 else 0,
                    'low_confidence_accuracy': round(low_conf['fantasy_points_abs_error'].mean(), 2) if len(low_conf) > 0 else 0,
                    'high_confidence_count': len(high_conf),
                    'low_confidence_count': len(low_conf)
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating aggregate metrics: {e}")
            return {}
            
    def get_model_performance_trends(self, season, position=None):
        """Analyze model performance trends over time"""
        session = db.get_session()
        
        try:
            query = session.query(PredictionAccuracy, Player).join(
                Player, PredictionAccuracy.player_id == Player.id
            ).filter(PredictionAccuracy.season == season)
            
            if position:
                query = query.filter(Player.position == position)
                
            results = query.order_by(PredictionAccuracy.week).all()
            
            if not results:
                return None
                
            # Group by week
            weekly_metrics = {}
            for accuracy, player in results:
                week = accuracy.week
                if week not in weekly_metrics:
                    weekly_metrics[week] = []
                    
                weekly_metrics[week].append({
                    'fantasy_abs_error': accuracy.fantasy_points_abs_error,
                    'within_10_points': accuracy.was_within_10_points,
                    'confidence': accuracy.confidence_score or 0.5,
                    'position': player.position
                })
                
            # Calculate weekly averages
            trends = []
            for week in sorted(weekly_metrics.keys()):
                week_data = weekly_metrics[week]
                
                avg_error = np.mean([d['fantasy_abs_error'] for d in week_data])
                accuracy_pct = (sum(d['within_10_points'] for d in week_data) / len(week_data)) * 100
                avg_confidence = np.mean([d['confidence'] for d in week_data])
                
                trends.append({
                    'week': week,
                    'avg_error': round(avg_error, 2),
                    'accuracy_pct': round(accuracy_pct, 1),
                    'avg_confidence': round(avg_confidence, 2),
                    'prediction_count': len(week_data)
                })
                
            return trends
            
        except Exception as e:
            self.logger.error(f"Error getting performance trends: {e}")
            return None
        finally:
            db.close_session(session)
            
    def identify_model_weaknesses(self, season):
        """Identify areas where the model performs poorly"""
        session = db.get_session()
        
        try:
            query = session.query(PredictionAccuracy, Player).join(
                Player, PredictionAccuracy.player_id == Player.id
            ).filter(
                PredictionAccuracy.season == season,
                PredictionAccuracy.fantasy_points_abs_error > 10  # Poor predictions
            )
            
            results = query.all()
            
            if not results:
                return None
                
            weaknesses = {
                'high_error_players': [],
                'position_analysis': {},
                'confidence_vs_accuracy': [],
                'common_patterns': []
            }
            
            # Analyze high error players
            player_errors = {}
            for accuracy, player in results:
                player_key = f"{player.name} ({player.position})"
                if player_key not in player_errors:
                    player_errors[player_key] = []
                player_errors[player_key].append(accuracy.fantasy_points_abs_error)
                
            # Get worst performers
            for player, errors in player_errors.items():
                avg_error = np.mean(errors)
                if avg_error > 15:  # Very high error
                    weaknesses['high_error_players'].append({
                        'player': player,
                        'avg_error': round(avg_error, 2),
                        'prediction_count': len(errors)
                    })
                    
            # Position analysis
            position_errors = {}
            for accuracy, player in results:
                pos = player.position
                if pos not in position_errors:
                    position_errors[pos] = []
                position_errors[pos].append(accuracy.fantasy_points_abs_error)
                
            for pos, errors in position_errors.items():
                weaknesses['position_analysis'][pos] = {
                    'avg_error': round(np.mean(errors), 2),
                    'error_count': len(errors),
                    'worst_error': round(max(errors), 2)
                }
                
            return weaknesses
            
        except Exception as e:
            self.logger.error(f"Error identifying weaknesses: {e}")
            return None
        finally:
            db.close_session(session)
            
    def generate_accuracy_report(self, season, week=None):
        """Generate comprehensive accuracy report"""
        try:
            # Get accuracy analysis
            accuracy_data = self.analyze_prediction_accuracy(season, week)
            if not accuracy_data:
                return "No prediction accuracy data available"
                
            report = []
            report.append(f"=== NFL PREDICTION ACCURACY REPORT ===")
            report.append(f"Season: {season}" + (f", Week: {week}" if week else " (Full Season)"))
            report.append(f"Total Predictions Analyzed: {accuracy_data['total_predictions']}")
            report.append("")
            
            # Overall metrics
            overall = accuracy_data['aggregate_metrics']['overall']
            report.append("OVERALL ACCURACY:")
            report.append(f"  Mean Absolute Error: {overall['mae_fantasy_points']} fantasy points")
            report.append(f"  Within 5 Points: {overall['within_5_points_pct']}%")
            report.append(f"  Within 10 Points: {overall['within_10_points_pct']}%")
            report.append(f"  Within 20%: {overall['within_20_percent_pct']}%")
            report.append("")
            
            # Position breakdown
            report.append("POSITION BREAKDOWN:")
            for pos, metrics in accuracy_data['aggregate_metrics']['position_breakdown'].items():
                report.append(f"  {pos}: {metrics['count']} predictions, "
                            f"MAE: {metrics['mae_fantasy']:.1f}, "
                            f"Accuracy: {metrics['within_10_points_pct']:.1f}%")
            report.append("")
            
            # Grade distribution
            report.append("GRADE DISTRIBUTION:")
            for grade, count in sorted(accuracy_data['aggregate_metrics']['grade_distribution'].items()):
                report.append(f"  {grade}: {count} predictions")
            report.append("")
            
            # Confidence analysis
            conf = accuracy_data['aggregate_metrics']['confidence_analysis']
            report.append("CONFIDENCE ANALYSIS:")
            report.append(f"  High Confidence (≥0.7): {conf['high_confidence_count']} predictions, "
                        f"MAE: {conf['high_confidence_accuracy']}")
            report.append(f"  Low Confidence (<0.7): {conf['low_confidence_count']} predictions, "
                        f"MAE: {conf['low_confidence_accuracy']}")
            
            return "\n".join(report)
            
        except Exception as e:
            self.logger.error(f"Error generating accuracy report: {e}")
            return "Error generating accuracy report"