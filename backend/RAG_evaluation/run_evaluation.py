#!/usr/bin/env python3
"""
Akvo RAG Evaluation Runner

This script starts the Streamlit-based RAG evaluation dashboard.
"""

import os
import sys
import subprocess
import argparse
import json
from typing import Dict, List, Any
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("run_evaluation")

def check_dependencies() -> Dict[str, bool]:
    """Check if required dependencies are installed.
    
    Returns:
        Dictionary of dependencies and their status
    """
    dependencies = {
        "streamlit": False,
        "pandas": False,
        "plotly": False,
        "httpx": False,
        "ragas": False,
        "langchain": False
    }
    
    for dep in dependencies:
        try:
            __import__(dep)
            dependencies[dep] = True
            logger.info(f"✓ {dep} is installed")
        except ImportError:
            logger.warning(f"✗ {dep} is not installed")
    
    return dependencies

def check_services() -> bool:
    """Check if the required services are running.
    
    Returns:
        True if services are available, False otherwise
    """
    try:
        import httpx
        
        # Check if Akvo RAG API is available
        try:
            response = httpx.get("http://localhost:8000/api/health", timeout=5.0)
            if response.status_code == 200:
                logger.info("✅ Akvo RAG API is available")
                return True
            else:
                logger.error(f"❌ Akvo RAG API returned status code {response.status_code}")
        except Exception as e:
            logger.error(f"❌ Error connecting to Akvo RAG API: {e}")
            logger.info("Please make sure the Akvo RAG system is running with:")
            logger.info("docker compose up")
        
        return False
    except ImportError:
        logger.error("Cannot check services: httpx is not installed")
        return False

def install_dependencies() -> bool:
    """Install missing dependencies.
    
    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info("Installing dependencies...")
        script_dir = os.path.dirname(os.path.abspath(__file__))
        requirements_path = os.path.join(script_dir, "requirements.txt")
        
        if not os.path.exists(requirements_path):
            logger.error(f"Requirements file not found: {requirements_path}")
            return False
        
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", requirements_path],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            logger.info("✅ Dependencies installed successfully")
            return True
        else:
            logger.error(f"❌ Failed to install dependencies: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"❌ Error installing dependencies: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Run Akvo RAG Evaluation Dashboard")
    parser.add_argument(
        "--port", type=int, default=8501, help="Port for Streamlit dashboard (default: 8501)"
    )
    parser.add_argument(
        "--kb", default="Living Income Benchmark Knowledge Base", 
        help="Knowledge base to evaluate (default: Living Income Benchmark Knowledge Base)"
    )
    parser.add_argument(
        "--skip-checks", action="store_true", help="Skip dependency and service checks"
    )
    parser.add_argument(
        "--install-deps", action="store_true", help="Automatically install missing dependencies"
    )
    
    args = parser.parse_args()
    
    # Get the directory of this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Change to the script directory
    os.chdir(script_dir)
    
    if not args.skip_checks:
        # Check dependencies
        dependencies = check_dependencies()
        missing_deps = [dep for dep, installed in dependencies.items() if not installed]
        
        if missing_deps:
            logger.warning(f"Missing dependencies: {', '.join(missing_deps)}")
            if args.install_deps:
                if not install_dependencies():
                    logger.error("Failed to install dependencies. Please install them manually:")
                    logger.error(f"pip install -r {os.path.join(script_dir, 'requirements.txt')}")
                    sys.exit(1)
            else:
                logger.error("Please install required dependencies first:")
                logger.error(f"pip install -r {os.path.join(script_dir, 'requirements.txt')}")
                logger.error("Or run with --install-deps to install automatically")
                sys.exit(1)
        
        # Check services
        if not check_services():
            logger.error("Service checks failed. Use --skip-checks to bypass these checks.")
            sys.exit(1)
    
    # Set environment variables
    os.environ["STREAMLIT_SERVER_PORT"] = str(args.port)
    os.environ["INITIAL_KB_LABEL"] = args.kb
    
    # Start Streamlit - ensure it listens on all interfaces for Docker access
    cmd = [
        "streamlit", "run", "app.py",
        "--server.port", str(args.port),
        "--server.address", "0.0.0.0",
        "--server.enableCORS", "false",
        "--browser.gatherUsageStats", "false"
    ]
    
    logger.info(f"Starting Streamlit dashboard on port {args.port}...")
    logger.info(f"Evaluating knowledge base: {args.kb}")
    logger.info("Press Ctrl+C to stop")
    
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        logger.info("\nStopping dashboard...")

if __name__ == "__main__":
    main()