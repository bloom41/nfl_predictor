"""
Improved roster change detector using the robust monitoring framework
"""
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from src.monitoring.robust_monitoring_framework import BaseMonitor
from src.monitoring.transaction_monitor import TransactionMonitor
from src.analysis.team_environment_analyzer import TeamEnvironmentAnalyzer
from src.database.database_v2 import db_session
from src.database.models import Player, TransactionLog, Prediction
from src.utils.error_handling import handle_errors, retry_on_error

logger = logging.getLogger(__name__)

class ImprovedRosterChangeDetector(BaseMonitor):
    """
    Roster change detector with robust error handling and recovery
    """
    
    def __init__(self, check_interval: float = 300.0):  # 5 minutes
        super().__init__("RosterChangeDetector", check_interval)
        
        # Initialize components with error handling
        try:
            self.transaction_monitor = TransactionMonitor()
            self.environment_analyzer = TeamEnvironmentAnalyzer()
        except Exception as e:
            logger.error(f"Failed to initialize roster change detector components: {e}")
            raise
        
        # Configuration
        self.significant_impact_threshold = 0.1  # 10% impact threshold
        self.prediction_update_threshold = 0.15  # 15% threshold for prediction updates
        self.max_transactions_per_check = 100   # Limit processing to prevent overload
        
        # State tracking
        self.last_transaction_check: Optional[datetime] = None
        self.processed_transaction_ids = set()
        
        # Performance metrics
        self.transactions_processed = 0
        self.significant_changes_found = 0
        self.prediction_updates_triggered = 0
        self.environment_impacts_calculated = 0
    
    def _monitor_iteration(self) -> bool:
        """
        Perform one iteration of roster change detection
        
        Returns:
            bool: True if successful, False if failed
        """
        try:
            logger.debug("Starting roster change detection iteration")
            
            # Monitor for new transactions
            new_transactions_count = self._monitor_transactions_safe()
            
            if new_transactions_count > 0:
                logger.info(f"Detected {new_transactions_count} new transactions")
                
                # Process significant roster changes
                significant_changes = self._process_significant_changes_safe()
                
                if significant_changes:
                    logger.info(f"Found {len(significant_changes)} significant roster changes")
                    
                    # Handle the significant changes
                    self._handle_significant_changes_batch(significant_changes)
                else:
                    logger.debug("No significant roster changes found")
            else:
                logger.debug("No new transactions detected")
            
            # Clean up old processed transaction IDs
            self._cleanup_processed_transactions()
            
            logger.debug("Roster change detection iteration completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error in roster change detection iteration: {e}")
            return False
    
    @retry_on_error(max_retries=2, retry_delay=1.0)
    def _monitor_transactions_safe(self) -> int:
        """
        Safely monitor for new transactions with retry logic
        """
        try:
            # Use the transaction monitor to check for new transactions
            new_transactions = self.transaction_monitor.monitor_all_transactions()
            
            if new_transactions > 0:
                self.transactions_processed += new_transactions
                logger.debug(f"Transaction monitor found {new_transactions} new transactions")
            
            return new_transactions
            
        except Exception as e:
            logger.warning(f"Error in transaction monitoring: {e}")
            # Return 0 to indicate no new transactions found due to error
            return 0
    
    def _process_significant_changes_safe(self) -> List[Dict[str, Any]]:
        """
        Safely process and identify significant roster changes
        """
        try:
            # Get recent unprocessed transactions
            def get_unprocessed_transactions(session):
                cutoff_time = datetime.utcnow() - timedelta(hours=24)
                
                query = session.query(TransactionLog).filter(
                    TransactionLog.processed == False,
                    TransactionLog.timestamp >= cutoff_time,
                    TransactionLog.transaction_type.in_(['trade', 'signing', 'release'])
                ).order_by(
                    TransactionLog.timestamp.desc()
                ).limit(self.max_transactions_per_check)
                
                return query.all()
            
            recent_transactions = db_session.execute_readonly_query(get_unprocessed_transactions)
            
            if not recent_transactions:
                return []
            
            significant_changes = []
            
            for transaction in recent_transactions:
                try:
                    # Skip if already processed by this detector
                    if transaction.id in self.processed_transaction_ids:
                        continue
                    
                    # Only process transactions with team changes
                    if not (transaction.player and transaction.old_team and transaction.new_team):
                        self.processed_transaction_ids.add(transaction.id)
                        continue
                    
                    # Analyze environment impact
                    impact_analysis = self._analyze_environment_impact_safe(transaction)
                    
                    if impact_analysis and abs(impact_analysis['overall_impact']) >= self.significant_impact_threshold:
                        significant_change = {
                            'transaction': transaction,
                            'impact_analysis': impact_analysis,
                            'requires_prediction_update': abs(impact_analysis['overall_impact']) >= self.prediction_update_threshold
                        }
                        significant_changes.append(significant_change)
                        self.significant_changes_found += 1
                    
                    # Mark as processed
                    self.processed_transaction_ids.add(transaction.id)
                    self.environment_impacts_calculated += 1
                    
                except Exception as e:
                    logger.warning(f"Error processing transaction {transaction.id}: {e}")
                    # Mark as processed to avoid reprocessing
                    self.processed_transaction_ids.add(transaction.id)
                    continue
            
            return significant_changes
            
        except Exception as e:
            logger.error(f"Error processing significant changes: {e}")
            return []
    
    @handle_errors(suppress=True)
    def _analyze_environment_impact_safe(self, transaction: TransactionLog) -> Optional[Dict[str, Any]]:
        """
        Safely analyze environment impact of a roster change
        """
        try:
            if not (transaction.player_id and transaction.old_team and transaction.new_team):
                return None
            
            # Use the environment analyzer
            impact_analysis = self.environment_analyzer.analyze_player_environment_change(
                transaction.player_id,
                transaction.old_team,
                transaction.new_team
            )
            
            if impact_analysis:
                # Add transaction context
                impact_analysis['transaction_id'] = transaction.id
                impact_analysis['transaction_type'] = transaction.transaction_type
                impact_analysis['timestamp'] = transaction.timestamp
                
                logger.debug(
                    f"Environment impact analysis for {impact_analysis.get('player_name', 'unknown')}: "
                    f"{impact_analysis.get('overall_impact', 0):.3f}"
                )
            
            return impact_analysis
            
        except Exception as e:
            logger.warning(f"Error analyzing environment impact for transaction {transaction.id}: {e}")
            return None
    
    def _handle_significant_changes_batch(self, significant_changes: List[Dict[str, Any]]):
        """
        Handle a batch of significant roster changes
        """
        try:
            prediction_updates_needed = []
            alerts_to_send = []
            
            for change in significant_changes:
                try:
                    transaction = change['transaction']
                    impact_analysis = change['impact_analysis']
                    
                    # Update transaction status in database
                    self._update_transaction_status(transaction, impact_analysis)
                    
                    # Collect prediction updates needed
                    if change.get('requires_prediction_update', False):
                        prediction_updates_needed.append(change)
                    
                    # Collect high-impact alerts
                    if abs(impact_analysis['overall_impact']) >= 0.2:  # 20% impact threshold for alerts
                        alerts_to_send.append(change)
                    
                except Exception as e:
                    logger.error(f"Error handling individual significant change: {e}")
                    continue
            
            # Trigger prediction updates if needed
            if prediction_updates_needed:
                self._trigger_prediction_updates_batch(prediction_updates_needed)
            
            # Send alerts for high-impact changes
            if alerts_to_send:
                self._send_impact_alerts_batch(alerts_to_send)
            
            logger.info(
                f"Processed {len(significant_changes)} significant changes, "
                f"{len(prediction_updates_needed)} prediction updates needed, "
                f"{len(alerts_to_send)} alerts sent"
            )
            
        except Exception as e:
            logger.error(f"Error handling significant changes batch: {e}")
    
    def _update_transaction_status(self, transaction: TransactionLog, impact_analysis: Dict[str, Any]):
        """Update transaction status in database"""
        try:
            def update_transaction(session):
                # Get the transaction from this session
                trans = session.query(TransactionLog).filter_by(id=transaction.id).first()
                if trans:
                    trans.processed = True
                    trans.impact_level = self._categorize_impact_level(impact_analysis['overall_impact'])
                    return True
                return False
            
            success = db_session.execute_query(update_transaction)
            
            if success:
                logger.debug(f"Updated transaction {transaction.id} status")
            else:
                logger.warning(f"Failed to update transaction {transaction.id} status")
                
        except Exception as e:
            logger.error(f"Error updating transaction status: {e}")
    
    def _categorize_impact_level(self, impact_score: float) -> str:
        """Categorize impact level based on score"""
        abs_impact = abs(impact_score)
        
        if abs_impact >= 0.2:
            return 'high'
        elif abs_impact >= 0.1:
            return 'medium'
        else:
            return 'low'
    
    def _trigger_prediction_updates_batch(self, prediction_updates: List[Dict[str, Any]]):
        """
        Trigger prediction updates for players affected by roster changes
        """
        try:
            players_to_update = []
            
            for update in prediction_updates:
                impact_analysis = update['impact_analysis']
                
                player_update = {
                    'player_id': impact_analysis.get('player_id'),
                    'player_name': impact_analysis.get('player_name'),
                    'impact_score': impact_analysis.get('overall_impact', 0),
                    'old_team': impact_analysis.get('old_team'),
                    'new_team': impact_analysis.get('new_team'),
                    'reason': f"Roster change impact: {impact_analysis.get('overall_impact', 0):+.2f}"
                }
                
                players_to_update.append(player_update)
            
            if players_to_update:
                # Log the prediction updates (actual implementation would trigger model updates)
                logger.info(f"Triggering prediction updates for {len(players_to_update)} players")
                
                for player_update in players_to_update:
                    logger.info(
                        f"Prediction update needed: {player_update['player_name']} "
                        f"({player_update['old_team']} → {player_update['new_team']}) "
                        f"Impact: {player_update['impact_score']:+.2f}"
                    )
                
                self.prediction_updates_triggered += len(players_to_update)
                
                # TODO: Integrate with actual prediction model updates
                # This would call the optimized prediction model to regenerate predictions
                
        except Exception as e:
            logger.error(f"Error triggering prediction updates: {e}")
    
    def _send_impact_alerts_batch(self, alerts: List[Dict[str, Any]]):
        """
        Send alerts for high-impact roster changes
        """
        try:
            alert_messages = []
            
            for alert in alerts:
                impact_analysis = alert['impact_analysis']
                
                message = (
                    f"🚨 HIGH IMPACT ROSTER CHANGE: "
                    f"{impact_analysis.get('player_name', 'Unknown')} "
                    f"({impact_analysis.get('old_team', '?')} → {impact_analysis.get('new_team', '?')}) "
                    f"Impact: {impact_analysis.get('overall_impact', 0):+.2f}"
                )
                
                alert_messages.append(message)
            
            if alert_messages:
                # Log alerts (actual implementation could send emails, Slack, etc.)
                logger.warning("HIGH IMPACT ROSTER CHANGES DETECTED:")
                for message in alert_messages:
                    logger.warning(message)
                
                # TODO: Integrate with notification system
                # - Email alerts
                # - Slack notifications
                # - Dashboard updates
                # - Mobile push notifications
                
        except Exception as e:
            logger.error(f"Error sending impact alerts: {e}")
    
    def _cleanup_processed_transactions(self):
        """Clean up old processed transaction IDs to prevent memory growth"""
        if len(self.processed_transaction_ids) > 1000:  # Keep last 1000 transaction IDs
            # Convert to list and keep most recent ones
            id_list = list(self.processed_transaction_ids)
            # Keep the most recent 500 IDs (simple cleanup)
            self.processed_transaction_ids = set(id_list[-500:])
            logger.debug("Cleaned up old processed transaction IDs")
    
    def check_immediate_impact(self) -> List[Dict[str, Any]]:
        """
        Check for immediate impact transactions (manual trigger)
        """
        try:
            logger.info("Running immediate impact check...")
            
            def get_recent_unprocessed_transactions(session):
                cutoff_time = datetime.utcnow() - timedelta(hours=1)
                
                return session.query(TransactionLog).filter(
                    TransactionLog.timestamp >= cutoff_time,
                    TransactionLog.processed == False,
                    TransactionLog.transaction_type.in_(['trade', 'signing'])
                ).all()
            
            recent_transactions = db_session.execute_readonly_query(get_recent_unprocessed_transactions)
            
            if not recent_transactions:
                logger.info("No recent unprocessed transactions found")
                return []
            
            immediate_impacts = []
            
            for transaction in recent_transactions:
                if transaction.player and transaction.old_team != transaction.new_team:
                    impact_analysis = self._analyze_environment_impact_safe(transaction)
                    
                    if impact_analysis:
                        immediate_impact = {
                            'player_name': impact_analysis['player_name'],
                            'old_team': impact_analysis['old_team'],
                            'new_team': impact_analysis['new_team'],
                            'impact_score': impact_analysis['overall_impact'],
                            'requires_update': abs(impact_analysis['overall_impact']) >= self.significant_impact_threshold,
                            'transaction_type': transaction.transaction_type,
                            'timestamp': transaction.timestamp
                        }
                        immediate_impacts.append(immediate_impact)
                        
                        # Mark as processed
                        self._update_transaction_status(transaction, impact_analysis)
            
            logger.info(f"Found {len(immediate_impacts)} immediate impacts")
            return immediate_impacts
            
        except Exception as e:
            logger.error(f"Error checking immediate impact: {e}")
            return []
    
    def get_monitor_metrics(self) -> Dict[str, Any]:
        """Get monitor-specific metrics"""
        base_metrics = self.get_metrics()
        
        base_metrics.update({
            'transactions_processed': self.transactions_processed,
            'significant_changes_found': self.significant_changes_found,
            'prediction_updates_triggered': self.prediction_updates_triggered,
            'environment_impacts_calculated': self.environment_impacts_calculated,
            'processed_transaction_ids_count': len(self.processed_transaction_ids),
            'significant_impact_threshold': self.significant_impact_threshold,
            'prediction_update_threshold': self.prediction_update_threshold
        })
        
        return base_metrics


__all__ = ['ImprovedRosterChangeDetector']