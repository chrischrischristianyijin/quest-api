#!/usr/bin/env python3
"""
Script to run local server with enhanced error logging for debugging
"""
import os
import sys
import subprocess
import logging
from datetime import datetime

def setup_debug_logging():
    """Setup enhanced logging for debugging"""
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    
    # Setup logging configuration
    log_filename = f"logs/debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    print(f"📝 Debug logging enabled - logs will be saved to: {log_filename}")
    return log_filename

def check_environment():
    """Check if environment is properly set up"""
    print("🔍 Checking environment setup...")
    
    # Check if .env file exists
    if not os.path.exists(".env"):
        print("⚠️ WARNING: .env file not found")
        print("💡 Create .env file with your Supabase credentials:")
        print("""
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
""")
        return False
    
    # Check if main app file exists
    if not os.path.exists("app/main.py"):
        print("❌ ERROR: app/main.py not found")
        print("💡 Make sure you're running this from the quest-api root directory")
        return False
    
    print("✅ Environment looks good")
    return True

def install_dependencies():
    """Install required dependencies"""
    print("📦 Installing dependencies...")
    
    try:
        # Check if requirements.txt exists
        if os.path.exists("requirements.txt"):
            subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
            print("✅ Dependencies installed successfully")
        else:
            print("⚠️ requirements.txt not found, installing common dependencies...")
            deps = [
                "fastapi", "uvicorn", "supabase", "python-dotenv", 
                "python-multipart", "python-jose", "passlib", "bcrypt"
            ]
            subprocess.run([sys.executable, "-m", "pip", "install"] + deps, check=True)
            print("✅ Common dependencies installed")
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False
    
    return True

def run_server():
    """Run the local server with debug settings"""
    print("🚀 Starting local server with debug logging...")
    print("👀 WATCH THE CONSOLE OUTPUT FOR ERROR MESSAGES!")
    print("🔍 Error details will be printed here when digest preview fails")
    print("=" * 70)
    
    try:
        # Set environment variables for debug mode
        env = os.environ.copy()
        env["PYTHONPATH"] = "."
        env["LOG_LEVEL"] = "DEBUG"
        
        # Run uvicorn with debug settings
        cmd = [
            sys.executable, "-m", "uvicorn", 
            "app.main:app",
            "--reload",
            "--host", "0.0.0.0", 
            "--port", "8000",
            "--log-level", "debug"
        ]
        
        print(f"🔧 Running command: {' '.join(cmd)}")
        print("📡 Server will be available at: http://localhost:8000")
        print("🏥 Health check: http://localhost:8000/health")
        print("📚 API docs: http://localhost:8000/docs")
        print("=" * 70)
        
        # Run the server
        subprocess.run(cmd, env=env)
        
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Failed to start server: {e}")

def main():
    print("🏠 LOCAL DEBUG SERVER SETUP")
    print(f"🕐 Started at: {datetime.now()}")
    print("=" * 70)
    
    # Setup debug logging
    log_file = setup_debug_logging()
    
    # Check environment
    if not check_environment():
        print("❌ Environment check failed")
        return
    
    # Install dependencies
    if not install_dependencies():
        print("❌ Dependency installation failed")
        return
    
    print("\n🎯 DEBUG SERVER INSTRUCTIONS:")
    print("1. This server will run with enhanced error logging")
    print("2. When digest preview fails, you'll see detailed error messages")
    print("3. Run test_local_server_debug.py in another terminal to trigger errors")
    print("4. Press Ctrl+C to stop the server")
    print(f"5. Logs are also saved to: {log_file}")
    
    input("\n🔄 Press ENTER to start the debug server...")
    
    # Run the server
    run_server()

if __name__ == "__main__":
    main()
