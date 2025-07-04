#!/usr/bin/env python3
"""
NFL Prediction System - Production Startup Script
Starts all system components for real-world operation
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import logging
import time
from datetime import datetime
from typing import Dict, Any

# Core system imports
from src.data_collection.automated_data_collector import start_automated_collection, get_collection_status
from src.models.comprehensive_prediction_system import ComprehensivePredictionSystem
from src.validation.model_validator import validate_current_season
from src.utils.logging_config import setup_logging
from src.utils.unified_database_operations import DatabaseSessionManager
from src.utils.typed_nfl_assistant import TypedNFLAssistant

def setup_system_logging():
    """Setup comprehensive logging for production"""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("🚀 Starting NFL Prediction System")
    logger.info(f"System startup time: {datetime.now()}")
    return logger

def start_data_collection(logger):
    """Start automated data collection system"""
    logger.info("📊 Starting automated data collection...")
    
    try:
        start_automated_collection()
        
        # Wait a moment for initialization
        time.sleep(2)
        
        status = get_collection_status()
        logger.info(f"Data collection status: {status['collection_status']}")
        logger.info(f"Current season: {status['current_season']}")
        logger.info(f"Current week: {status['current_week']}")
        
        return True
    except Exception as e:
        logger.error(f"Failed to start data collection: {e}")
        return False

def initialize_prediction_models(logger):
    """Initialize all prediction model components"""
    logger.info("🧠 Initializing prediction models...")
    
    try:
        # Initialize comprehensive prediction system for each position
        models = {}
        for position in ['QB', 'RB', 'WR', 'TE']:
            models[position] = ComprehensivePredictionSystem(position)
            logger.info(f"✅ {position} prediction model ready")
        
        return models
    except Exception as e:
        logger.error(f"Failed to initialize prediction models: {e}")
        return None

def verify_system_health(logger):
    """Verify all system components are healthy"""
    logger.info("🔍 Verifying system health...")
    
    try:
        # Test database connectivity
        db_manager = DatabaseSessionManager()
        def test_db(session):
            from sqlalchemy import text
            return session.execute(text("SELECT 1")).scalar()
        
        result = db_manager.execute_readonly(test_db)
        if result == 1:
            logger.info("✅ Database connectivity verified")
        
        # Test data collection status
        status = get_collection_status()
        logger.info(f"✅ Data collection system: {status['collection_status']}")
        
        # Test model validation
        try:
            summary = validate_current_season()
            logger.info(f"✅ Model validation system: {summary.total_predictions} predictions available")
        except Exception as e:
            logger.warning(f"Model validation: {e} (expected if no data yet)")
        
        return True
    except Exception as e:
        logger.error(f"System health check failed: {e}")
        return False

def start_user_interface(logger):
    """Start the user interface assistant"""
    logger.info("👤 Starting user interface...")
    
    try:
        assistant = TypedNFLAssistant(current_season=2024)
        logger.info("✅ NFL Assistant ready for queries")
        return assistant
    except Exception as e:
        logger.error(f"Failed to start user interface: {e}")
        return None

def main():
    """Main system startup"""
    print("🏈 NFL PREDICTION SYSTEM - PRODUCTION STARTUP")
    print("=" * 60)
    
    # Setup logging
    logger = setup_system_logging()
    
    # Start components
    startup_results = {}
    
    # 1. Start data collection
    print("📊 Starting automated data collection...")
    startup_results['data_collection'] = start_data_collection(logger)
    
    # 2. Initialize prediction models
    print("🧠 Initializing prediction models...")
    models = initialize_prediction_models(logger)
    startup_results['prediction_models'] = models is not None
    
    # 3. Verify system health
    print("🔍 Verifying system health...")
    startup_results['system_health'] = verify_system_health(logger)
    
    # 4. Start user interface
    print("👤 Starting user interface...")
    assistant = start_user_interface(logger)
    startup_results['user_interface'] = assistant is not None
    
    # Print startup summary
    print("\n" + "=" * 60)
    print("🎯 SYSTEM STARTUP SUMMARY")
    print("=" * 60)
    
    for component, status in startup_results.items():
        status_icon = "✅" if status else "❌"
        print(f"{component.replace('_', ' ').title()}: {status_icon}")
    
    all_good = all(startup_results.values())
    
    if all_good:
        print("\n🎉 ALL SYSTEMS OPERATIONAL!")
        print("The NFL Prediction System is ready for production use.")
        print("\nNext steps:")
        print("• Data collection will run automatically")
        print("• Use the assistant for predictions: assistant.ask('your question')")
        print("• Monitor logs in logs/ directory")
        print("• Access database at nfl_predictor.db")
        
        # Interactive mode option
        if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
            print("\n🤖 Starting interactive mode...")
            interactive_mode(assistant, logger)
        
    else:
        print("\n⚠️  Some components failed to start.")
        print("Check logs for details and fix issues before proceeding.")
        return 1
    
    return 0

def interactive_mode(assistant, logger):
    """Interactive mode for testing the system"""
    print("\n" + "=" * 60)
    print("🤖 NFL PREDICTION ASSISTANT - INTERACTIVE MODE")
    print("=" * 60)
    print("Type 'quit' to exit, 'help' for commands")
    print()
    
    while True:
        try:
            question = input("🏈 Ask me anything: ").strip()
            
            if question.lower() in ['quit', 'exit', 'bye']:
                print("👋 Goodbye!")
                break
            
            if not question:
                continue
            
            response = assistant.ask(question)
            print(f"\n{response}\n")
            
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            logger.error(f"Error in interactive mode: {e}")
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)