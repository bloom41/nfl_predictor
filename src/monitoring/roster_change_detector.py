import logging
import time
import threading
from datetime import datetime, timedelta
from src.monitoring.transaction_monitor import TransactionMonitor
from src.analysis.team_environment_analyzer import TeamEnvironmentAnalyzer
from src.database.database import db
from src.database.models import Player, TransactionLog

class RosterChangeDetector:
    """
    Real-time detection and processing of NFL roster changes
    Automatically triggers prediction updates when significant changes occur
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.transaction_monitor = TransactionMonitor()
        self.environment_analyzer = TeamEnvironmentAnalyzer()
        self.is_monitoring = False
        self.monitoring_thread = None
        
        # Monitoring configuration
        self.check_interval = 300  # Check every 5 minutes
        self.significant_impact_threshold = 0.1  # 10% impact threshold
        
    def start_monitoring(self):
        """Start real-time monitoring in background thread"""
        try:
            if self.is_monitoring:
                self.logger.warning("Monitoring already running")
                return
                
            self.is_monitoring = True
            self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
            self.monitoring_thread.start()
            
            self.logger.info("Started real-time roster change monitoring")
            
        except Exception as e:
            self.logger.error(f"Error starting monitoring: {e}")
            self.is_monitoring = False
            
    def stop_monitoring(self):
        """Stop real-time monitoring"""
        try:
            self.is_monitoring = False
            
            if self.monitoring_thread and self.monitoring_thread.is_alive():
                self.monitoring_thread.join(timeout=5)
                
            self.logger.info("Stopped real-time roster change monitoring")
            
        except Exception as e:
            self.logger.error(f"Error stopping monitoring: {e}")
            
    def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.is_monitoring:
            try:
                self.logger.debug("Checking for roster changes...")
                
                # Check for new transactions
                new_transactions = self.transaction_monitor.monitor_all_transactions()
                
                if new_transactions > 0:
                    self.logger.info(f"Detected {new_transactions} new transactions")
                    
                    # Process significant changes
                    self._process_significant_changes()
                    
                # Wait before next check
                time.sleep(self.check_interval)
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                time.sleep(60)  # Wait a minute before retrying
                
    def _process_significant_changes(self):
        """Process and respond to significant roster changes"""
        try:
            # Get recent unprocessed transactions
            session = db.get_session()
            
            recent_transactions = session.query(TransactionLog).filter(
                TransactionLog.processed == False,
                TransactionLog.timestamp >= datetime.now() - timedelta(hours=24)
            ).all()
            
            significant_changes = []
            
            for transaction in recent_transactions:
                if transaction.player and transaction.transaction_type in ['trade', 'signing']:
                    # Analyze environment impact
                    impact = self.environment_analyzer.analyze_player_environment_change(
                        transaction.player_id,
                        transaction.old_team,
                        transaction.new_team
                    )
                    
                    if impact and abs(impact['overall_impact']) >= self.significant_impact_threshold:
                        significant_changes.append({
                            'transaction': transaction,
                            'impact': impact
                        })
                        
                        # Mark as processed
                        transaction.processed = True
                        transaction.impact_level = self._categorize_impact_level(impact['overall_impact'])
                        
            session.commit()
            
            if significant_changes:
                self._trigger_prediction_updates(significant_changes)
                self._send_alerts(significant_changes)
                
        except Exception as e:
            self.logger.error(f"Error processing significant changes: {e}")
            if session:
                session.rollback()
        finally:
            db.close_session(session)
            
    def _categorize_impact_level(self, impact_score):
        """Categorize impact level based on score"""
        abs_impact = abs(impact_score)
        
        if abs_impact >= 0.2:
            return 'high'
        elif abs_impact >= 0.1:
            return 'medium'
        else:
            return 'low'
            
    def _trigger_prediction_updates(self, significant_changes):
        """Trigger prediction model updates for affected players"""
        try:
            from src.models.prediction_model import NFLPredictionModel
            
            players_to_update = []
            
            for change in significant_changes:
                player_id = change['transaction'].player_id
                position = change['transaction'].player.position
                impact_score = change['impact']['overall_impact']
                
                players_to_update.append({
                    'player_id': player_id,
                    'position': position,
                    'impact_score': impact_score,
                    'reason': f"Team change impact: {impact_score:+.2f}"
                })
                
            if players_to_update:
                self.logger.info(f"Triggering prediction updates for {len(players_to_update)} players")
                
                # Update predictions for current season
                current_season = 2025
                current_week = self._get_current_nfl_week()
                
                for player_update in players_to_update:
                    try:
                        model = NFLPredictionModel(player_update['position'])
                        
                        # Generate updated prediction
                        prediction = model.predict_with_feedback_enhancements(
                            player_update['player_id'],
                            current_season,
                            current_week
                        )
                        
                        if prediction:
                            # Apply environment impact adjustment
                            self._apply_environment_adjustment(prediction, player_update['impact_score'])
                            
                            self.logger.info(f"Updated prediction for player {player_update['player_id']}")
                            
                    except Exception as e:
                        self.logger.error(f"Error updating prediction for player {player_update['player_id']}: {e}")
                        
        except Exception as e:
            self.logger.error(f"Error triggering prediction updates: {e}")
            
    def _apply_environment_adjustment(self, prediction, impact_score):
        """Apply environment impact adjustment to prediction"""
        try:
            # Adjust fantasy points prediction based on environment impact
            current_fp = prediction['predictions'].get('target_fantasy_points', 0)
            adjustment = current_fp * impact_score
            
            prediction['predictions']['target_fantasy_points'] = max(0, current_fp + adjustment)
            
            # Adjust confidence based on magnitude of change
            confidence_adjustment = -abs(impact_score) * 0.5  # Reduce confidence for big changes
            prediction['confidence'] = max(0.1, prediction['confidence'] + confidence_adjustment)
            
            # Add adjustment note
            prediction['adjustment_notes'] = f"Environment impact: {impact_score:+.2f}"
            
        except Exception as e:
            self.logger.error(f"Error applying environment adjustment: {e}")
            
    def _send_alerts(self, significant_changes):
        """Send alerts for significant roster changes"""
        try:
            high_impact_changes = [
                change for change in significant_changes
                if abs(change['impact']['overall_impact']) >= 0.15
            ]
            
            if high_impact_changes:
                alert_message = self._format_alert_message(high_impact_changes)
                self.logger.warning(f"HIGH IMPACT ROSTER CHANGES DETECTED:\n{alert_message}")
                
                # Here you could integrate with notification systems:
                # - Email alerts
                # - Slack notifications
                # - Push notifications
                # - Dashboard updates
                
        except Exception as e:
            self.logger.error(f"Error sending alerts: {e}")
            
    def _format_alert_message(self, changes):
        """Format alert message for significant changes"""
        try:
            message_lines = []
            
            for change in changes:
                impact = change['impact']
                transaction = change['transaction']
                
                message_lines.append(
                    f"🚨 {impact['player_name']} ({impact['position']}) "
                    f"{impact['old_team']} → {impact['new_team']}: "
                    f"{impact['overall_impact']:+.2f} impact"
                )
                
            return "\n".join(message_lines)
            
        except Exception as e:
            self.logger.error(f"Error formatting alert message: {e}")
            return "Error formatting alert"
            
    def _get_current_nfl_week(self):
        """Get current NFL week (simplified)"""
        # In a real implementation, this would calculate based on NFL season dates
        # For now, return a default week
        return 1
        
    def get_monitoring_status(self):
        """Get current monitoring status"""
        return {
            'is_monitoring': self.is_monitoring,
            'check_interval': self.check_interval,
            'threshold': self.significant_impact_threshold,
            'thread_alive': self.monitoring_thread.is_alive() if self.monitoring_thread else False
        }
        
    def check_immediate_impact(self):
        """Check for immediate impact transactions (manual trigger)"""
        try:
            self.logger.info("Running immediate impact check...")
            
            # Get very recent transactions (last hour)
            session = db.get_session()
            
            recent_transactions = session.query(TransactionLog).filter(
                TransactionLog.timestamp >= datetime.now() - timedelta(hours=1),
                TransactionLog.processed == False
            ).all()
            
            if not recent_transactions:
                self.logger.info("No recent unprocessed transactions found")
                return []
                
            immediate_impacts = []
            
            for transaction in recent_transactions:
                if transaction.player and transaction.transaction_type in ['trade', 'signing']:
                    impact = self.environment_analyzer.analyze_player_environment_change(
                        transaction.player_id,
                        transaction.old_team,
                        transaction.new_team
                    )
                    
                    if impact:
                        immediate_impacts.append({
                            'player_name': impact['player_name'],
                            'old_team': impact['old_team'],
                            'new_team': impact['new_team'],
                            'impact_score': impact['overall_impact'],
                            'requires_update': abs(impact['overall_impact']) >= self.significant_impact_threshold
                        })
                        
                        # Mark as processed
                        transaction.processed = True
                        
            session.commit()
            
            self.logger.info(f"Found {len(immediate_impacts)} immediate impacts")
            return immediate_impacts
            
        except Exception as e:
            self.logger.error(f"Error checking immediate impact: {e}")
            return []
        finally:
            db.close_session(session)
            
    def force_update_player_predictions(self, player_names):
        """Force update predictions for specific players"""
        try:
            session = db.get_session()
            
            updated_players = []
            
            for player_name in player_names:
                player = session.query(Player).filter(
                    Player.name.ilike(f"%{player_name}%")
                ).first()
                
                if player:
                    # Check if player had recent team change
                    recent_transaction = session.query(TransactionLog).filter(
                        TransactionLog.player_id == player.id,
                        TransactionLog.timestamp >= datetime.now() - timedelta(days=7)
                    ).first()
                    
                    if recent_transaction:
                        # Analyze and update
                        impact = self.environment_analyzer.analyze_player_environment_change(
                            player.id,
                            recent_transaction.old_team,
                            recent_transaction.new_team
                        )
                        
                        if impact:
                            updated_players.append({
                                'name': player.name,
                                'impact': impact['overall_impact'],
                                'updated': True
                            })
                        else:
                            updated_players.append({
                                'name': player.name,
                                'impact': 0.0,
                                'updated': False,
                                'reason': 'No environment impact calculated'
                            })
                    else:
                        updated_players.append({
                            'name': player.name,
                            'impact': 0.0,
                            'updated': False,
                            'reason': 'No recent team change found'
                        })
                else:
                    updated_players.append({
                        'name': player_name,
                        'impact': 0.0,
                        'updated': False,
                        'reason': 'Player not found'
                    })
                    
            return updated_players
            
        except Exception as e:
            self.logger.error(f"Error force updating predictions: {e}")
            return []
        finally:
            db.close_session(session)