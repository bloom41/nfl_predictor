import logging
import schedule
import time
from datetime import datetime, timedelta
from src.models.feedback_loop import ModelFeedbackLoop
from src.analysis.prediction_accuracy import PredictionAccuracyAnalyzer
from src.utils.logging_config import setup_logging

class AutomatedFeedbackScheduler:
    def __init__(self):
        setup_logging()
        self.logger = logging.getLogger(__name__)
        self.feedback_loop = ModelFeedbackLoop()
        self.accuracy_analyzer = PredictionAccuracyAnalyzer()
        
        # Scheduling configuration
        self.feedback_frequency = 'weekly'  # 'daily', 'weekly', 'after_games'
        self.min_new_results = 5  # Minimum new results to trigger feedback
        self.season = 2024
        
    def schedule_feedback_loops(self):
        """Schedule automated feedback loops"""
        try:
            # Schedule weekly comprehensive feedback
            schedule.every().monday.at("02:00").do(self.run_weekly_feedback)
            
            # Schedule daily light feedback during season
            schedule.every().day.at("06:00").do(self.run_daily_feedback_check)
            
            # Schedule post-game feedback (Tuesday after Monday Night Football)
            schedule.every().tuesday.at("08:00").do(self.run_post_games_feedback)
            
            self.logger.info("Feedback loops scheduled successfully")
            self.logger.info("- Weekly comprehensive feedback: Mondays at 2:00 AM")
            self.logger.info("- Daily feedback check: Every day at 6:00 AM")
            self.logger.info("- Post-games feedback: Tuesdays at 8:00 AM")
            
        except Exception as e:
            self.logger.error(f"Error scheduling feedback loops: {e}")
            
    def run_weekly_feedback(self):
        """Run comprehensive weekly feedback analysis"""
        try:
            self.logger.info("Starting weekly comprehensive feedback cycle...")
            
            # Run full feedback cycle for all positions
            improvements_made = self.feedback_loop.run_automated_feedback_cycle(self.season)
            
            if improvements_made:
                self.logger.info("Weekly feedback cycle completed with improvements")
                
                # Generate comprehensive accuracy report
                report = self.accuracy_analyzer.generate_accuracy_report(self.season)
                self.logger.info(f"Weekly accuracy report:\n{report}")
                
                # Send alert if accuracy is declining
                self._check_performance_alerts()
                
            else:
                self.logger.info("Weekly feedback cycle completed - no improvements needed")
                
        except Exception as e:
            self.logger.error(f"Error in weekly feedback cycle: {e}")
            
    def run_daily_feedback_check(self):
        """Run daily lightweight feedback check"""
        try:
            self.logger.info("Running daily feedback check...")
            
            # Check if there are enough new results for feedback
            new_results_count = self._count_recent_results(days=1)
            
            if new_results_count >= self.min_new_results:
                self.logger.info(f"Found {new_results_count} new results - running light feedback")
                
                # Run light feedback (confidence calibration only)
                self._run_light_feedback()
                
            else:
                self.logger.info(f"Only {new_results_count} new results - skipping daily feedback")
                
        except Exception as e:
            self.logger.error(f"Error in daily feedback check: {e}")
            
    def run_post_games_feedback(self):
        """Run feedback after weekend games are completed"""
        try:
            self.logger.info("Running post-games feedback...")
            
            # Check for new results from weekend games
            weekend_results = self._count_recent_results(days=3)  # Fri-Mon
            
            if weekend_results >= 10:  # Substantial number of games
                self.logger.info(f"Found {weekend_results} weekend results - running targeted feedback")
                
                # Run position-specific feedback for positions with poor performance
                self._run_targeted_position_feedback()
                
            else:
                self.logger.info(f"Only {weekend_results} weekend results - skipping post-games feedback")
                
        except Exception as e:
            self.logger.error(f"Error in post-games feedback: {e}")
            
    def _count_recent_results(self, days=1):
        """Count actual results from recent days"""
        try:
            from src.database.database import db
            from src.database.models import ActualResults
            from datetime import datetime, timedelta
            
            session = db.get_session()
            
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            count = session.query(ActualResults).filter(
                ActualResults.created_at >= cutoff_date
            ).count()
            
            db.close_session(session)
            return count
            
        except Exception as e:
            self.logger.error(f"Error counting recent results: {e}")
            return 0
            
    def _run_light_feedback(self):
        """Run lightweight feedback (confidence calibration only)"""
        try:
            positions = ['QB', 'RB', 'WR', 'TE']
            
            for position in positions:
                # Only recalibrate confidence scores
                success = self.feedback_loop._recalibrate_confidence_scores(self.season, position)
                if success:
                    self.logger.info(f"Recalibrated confidence for {position}")
                    
        except Exception as e:
            self.logger.error(f"Error in light feedback: {e}")
            
    def _run_targeted_position_feedback(self):
        """Run feedback targeting positions with poor recent performance"""
        try:
            # Analyze recent performance by position
            recent_analysis = self.accuracy_analyzer.analyze_prediction_accuracy(
                self.season, week=None  # All weeks
            )
            
            if not recent_analysis:
                return
                
            # Identify positions with high error rates
            position_errors = recent_analysis['aggregate_metrics']['position_breakdown']
            
            for position, metrics in position_errors.items():
                if metrics['mae_fantasy'] > 4.0:  # High error threshold
                    self.logger.info(f"Running targeted feedback for {position} (MAE: {metrics['mae_fantasy']:.1f})")
                    
                    success = self.feedback_loop.implement_feedback_improvements(
                        self.season, position
                    )
                    
                    if success:
                        self.logger.info(f"Completed targeted improvements for {position}")
                        
        except Exception as e:
            self.logger.error(f"Error in targeted position feedback: {e}")
            
    def _check_performance_alerts(self):
        """Check for performance issues and send alerts"""
        try:
            # Get recent performance trends
            trends = self.accuracy_analyzer.get_model_performance_trends(self.season)
            
            if not trends or len(trends) < 3:
                return
                
            # Check for declining accuracy
            recent_weeks = trends[-3:]
            early_weeks = trends[:3]
            
            recent_avg_error = sum(w['avg_error'] for w in recent_weeks) / len(recent_weeks)
            early_avg_error = sum(w['avg_error'] for w in early_weeks) / len(early_weeks)
            
            if recent_avg_error > early_avg_error * 1.3:  # 30% increase in error
                self.logger.warning(f"PERFORMANCE ALERT: Model accuracy declining!")
                self.logger.warning(f"Recent error: {recent_avg_error:.2f}, Early error: {early_avg_error:.2f}")
                
                # Trigger emergency full retrain
                self.logger.info("Triggering emergency model retrain...")
                self.feedback_loop._full_model_retrain(self.season)
                
        except Exception as e:
            self.logger.error(f"Error checking performance alerts: {e}")
            
    def start_automated_feedback_system(self):
        """Start the automated feedback system"""
        try:
            self.logger.info("Starting automated feedback system...")
            
            # Schedule all feedback loops
            self.schedule_feedback_loops()
            
            # Run initial feedback check
            self.logger.info("Running initial feedback analysis...")
            initial_success = self.feedback_loop.run_automated_feedback_cycle(self.season)
            
            if initial_success:
                self.logger.info("Initial feedback cycle completed successfully")
            else:
                self.logger.info("Initial feedback cycle - no improvements needed")
                
            # Start scheduler loop
            self.logger.info("Automated feedback system running. Press Ctrl+C to stop.")
            
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
                
        except KeyboardInterrupt:
            self.logger.info("Automated feedback system stopped by user")
        except Exception as e:
            self.logger.error(f"Error in automated feedback system: {e}")
            
    def run_manual_feedback(self, position=None, force_retrain=False):
        """Manually trigger feedback cycle"""
        try:
            self.logger.info(f"Running manual feedback cycle for {position or 'all positions'}...")
            
            if force_retrain:
                # Force full retrain
                success = self.feedback_loop._full_model_retrain(self.season, position)
                action = "Full retrain"
            else:
                # Standard feedback improvements
                success = self.feedback_loop.implement_feedback_improvements(self.season, position)
                action = "Standard feedback"
                
            if success:
                self.logger.info(f"{action} completed successfully")
                
                # Generate report
                report = self.accuracy_analyzer.generate_accuracy_report(self.season)
                print(f"\n{report}")
                
            else:
                self.logger.info(f"{action} completed - no improvements needed")
                
        except Exception as e:
            self.logger.error(f"Error in manual feedback: {e}")
            
    def get_feedback_status(self):
        """Get current status of feedback system"""
        try:
            # Get recent accuracy metrics
            analysis = self.accuracy_analyzer.analyze_prediction_accuracy(self.season)
            
            if not analysis:
                return "No accuracy data available"
                
            status = {
                'total_predictions': analysis['total_predictions'],
                'average_error': analysis['aggregate_metrics']['overall']['mae_fantasy_points'],
                'within_10_points': analysis['aggregate_metrics']['overall']['within_10_points_pct'],
                'last_feedback_run': 'Unknown',  # Would track in metadata
                'scheduled_runs': [
                    'Weekly: Mondays at 2:00 AM',
                    'Daily: Every day at 6:00 AM', 
                    'Post-games: Tuesdays at 8:00 AM'
                ]
            }
            
            return status
            
        except Exception as e:
            self.logger.error(f"Error getting feedback status: {e}")
            return "Error getting status"