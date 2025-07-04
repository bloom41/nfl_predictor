#!/usr/bin/env python3
"""
NFL Assistant Flask Application Startup Script
Handles environment setup and graceful startup
"""
import os
import sys
import time
import subprocess
from pathlib import Path

def setup_environment():
    """Setup environment and check dependencies"""
    print("🏈 NFL Assistant Flask Setup")
    print("=" * 50)
    
    # Create necessary directories
    directories = ['logs', 'data_cache', 'templates']
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"✅ Directory created/verified: {directory}")
    
    # Check if .env file exists
    if not Path('.env').exists():
        if Path('.env.example').exists():
            print("⚠️  .env file not found, copying from .env.example")
            subprocess.run(['cp', '.env.example', '.env'])
        else:
            print("❌ No .env file found. Please create one with database configuration.")
            return False
    
    # Check Python dependencies with correct import names
    required_packages = {
        'flask': 'flask',
        'flask-cors': 'flask_cors', 
        'python-dotenv': 'dotenv',
        'sqlalchemy': 'sqlalchemy',
        'psycopg2-binary': 'psycopg2',
        'gunicorn': 'gunicorn',
        'numpy': 'numpy',
        'pandas': 'pandas',
        'scikit-learn': 'sklearn'
    }
    
    missing_packages = []
    for package_name, import_name in required_packages.items():
        try:
            __import__(import_name)
        except ImportError:
            missing_packages.append(package_name)
    
    if missing_packages:
        print(f"❌ Missing packages: {', '.join(missing_packages)}")
        print("💡 Install with: pip install -r requirements_flask.txt")
        return False
    
    print("✅ All dependencies satisfied")
    return True

def check_database():
    """Check database connectivity"""
    try:
        from database_config import db_manager
        if db_manager.test_connection():
            print("✅ Database connection successful")
            return True
        else:
            print("⚠️  Database connection failed, will use SQLite fallback")
            return True  # Still allow startup
    except Exception as e:
        print(f"⚠️  Database check failed: {e}")
        return True  # Still allow startup

def start_development_server():
    """Start Flask development server"""
    print("\n🚀 Starting Flask Development Server")
    print("-" * 40)
    
    # Set environment variables
    os.environ['FLASK_APP'] = 'app.py'
    os.environ['FLASK_ENV'] = 'development'
    os.environ['FLASK_DEBUG'] = 'True'
    
    from app import app
    
    port = int(os.getenv('PORT', 5000))
    host = os.getenv('HOST', '0.0.0.0')
    
    print(f"🌐 Server starting on http://{host}:{port}")
    print("📊 API Documentation: http://localhost:5000/api/status")
    print("🎮 Web Interface: http://localhost:5000")
    print("\n💡 Press Ctrl+C to stop the server")
    
    app.run(host=host, port=port, debug=True)

def start_production_server():
    """Start Gunicorn production server"""
    print("\n🚀 Starting Gunicorn Production Server")
    print("-" * 40)
    
    port = int(os.getenv('PORT', 5000))
    workers = int(os.getenv('WORKERS', 2))
    
    cmd = [
        'gunicorn',
        '--bind', f'0.0.0.0:{port}',
        '--workers', str(workers),
        '--threads', '4',
        '--timeout', '120',
        '--keep-alive', '2',
        '--max-requests', '1000',
        '--max-requests-jitter', '100',
        '--preload',
        '--access-logfile', 'logs/access.log',
        '--error-logfile', 'logs/error.log',
        'app:app'
    ]
    
    print(f"🌐 Starting production server on port {port} with {workers} workers")
    subprocess.run(cmd)

def main():
    """Main startup function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='NFL Assistant Flask Startup')
    parser.add_argument('--mode', choices=['dev', 'prod'], default='dev',
                       help='Startup mode (dev/prod)')
    parser.add_argument('--skip-checks', action='store_true',
                       help='Skip environment checks')
    
    args = parser.parse_args()
    
    if not args.skip_checks:
        if not setup_environment():
            sys.exit(1)
        
        if not check_database():
            print("⚠️  Database issues detected, but continuing...")
    
    try:
        if args.mode == 'dev':
            start_development_server()
        else:
            start_production_server()
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        print(f"❌ Server startup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()