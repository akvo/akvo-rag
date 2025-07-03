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
    import importlib.util
    
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
            # Use importlib.util.find_spec for more reliable detection
            spec = importlib.util.find_spec(dep)
            if spec is not None:
                dependencies[dep] = True
                logger.info(f"✓ {dep} is installed")
            else:
                logger.warning(f"✗ {dep} is not installed")
        except (ImportError, ModuleNotFoundError, ValueError):
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
        "--headless", action="store_true", help="Run evaluation in headless mode (without Streamlit)"
    )
    parser.add_argument(
        "--queries", type=str, help="Path to file containing queries for headless mode"
    )
    parser.add_argument(
        "--output", type=str, help="Path to output file for headless mode results"
    )
    parser.add_argument(
        "--openai-api-key", type=str, help="OpenAI API key for evaluation"
    )
    parser.add_argument(
        "--openai-model", type=str, default="gpt-4o", 
        help="OpenAI model to use for evaluation (default: gpt-4o)"
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
            logger.error("Some dependencies are missing. Make sure you're running in the virtual environment.")
            sys.exit(1)
        
        # Check services
        if not check_services():
            logger.error("Service checks failed. Use --skip-checks to bypass these checks.")
            sys.exit(1)
    
    # Set environment variables
    os.environ["STREAMLIT_SERVER_PORT"] = str(args.port)
    os.environ["INITIAL_KB_LABEL"] = args.kb
    
    if args.openai_api_key:
        os.environ["OPENAI_API_KEY"] = args.openai_api_key
    
    if args.headless:
        # Run in headless mode
        logger.info("Starting headless evaluation...")
        logger.info(f"Evaluating knowledge base: {args.kb}")
        
        from headless_evaluation import run_headless_evaluation
        
        # Load queries from file or use defaults
        queries = None
        if args.queries:
            try:
                with open(args.queries, 'r') as f:
                    queries = [line.strip() for line in f if line.strip()]
                logger.info(f"Loaded {len(queries)} queries from {args.queries}")
            except Exception as e:
                logger.error(f"Error loading queries from {args.queries}: {e}")
                sys.exit(1)
        
        # Run headless evaluation
        results = run_headless_evaluation(
            kb_name=args.kb,
            queries=queries,
            openai_model=args.openai_model
        )
        
        # Save results to file if specified
        if args.output:
            try:
                with open(args.output, 'w') as f:
                    json.dump(results, f, indent=2)
                logger.info(f"Results saved to {args.output}")
            except Exception as e:
                logger.error(f"Error saving results to {args.output}: {e}")
        else:
            # Print results to console
            print(json.dumps(results, indent=2))
    else:
        # Start Streamlit - ensure it listens on all interfaces for Docker access
        cmd = [
            "streamlit", "run", "streamlit_app/main.py",
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