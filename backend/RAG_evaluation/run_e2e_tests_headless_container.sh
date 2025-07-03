#!/bin/bash

# RAG Evaluation E2E Test Runner - Headless Container Mode
# This script runs end-to-end tests inside the Docker container in headless mode.
# It automatically installs missing Playwright browsers and system dependencies 
# that are lost when containers restart due to volume mounting behavior.

set -e  # Exit on any error

# Configuration
CONTAINER_NAME="akvo-rag-backend-1"
TEST_TIMEOUT=${TEST_TIMEOUT:-600}  # 10 minutes default
VERBOSE=${VERBOSE:-true}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[E2E]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[E2E]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[E2E]${NC} $1"
}

print_error() {
    echo -e "${RED}[E2E]${NC} $1"
}

# Function to check if container is running
check_container() {
    print_status "Checking if container '$CONTAINER_NAME' is running..."
    if ! docker ps --format "table {{.Names}}" | grep -q "^$CONTAINER_NAME$"; then
        print_error "Container '$CONTAINER_NAME' is not running!"
        print_error "Please run './rag-evaluate' from the main directory first."
        exit 1
    fi
    print_success "Container is running"
}

# Function to check if virtual environment exists
check_venv() {
    print_status "Checking virtual environment..."
    if ! docker exec "$CONTAINER_NAME" bash -c "[ -d /app/RAG_evaluation/venv ]"; then
        print_error "Virtual environment not found in container!"
        print_error "Please ensure RAG evaluation system is properly set up."
        exit 1
    fi
    print_success "Virtual environment found"
}

# Function to check and install Python dependencies
check_python_deps() {
    print_status "Checking Python dependencies..."
    
    # Check if pytest and playwright are installed in venv
    if docker exec "$CONTAINER_NAME" bash -c "cd /app/RAG_evaluation && source venv/bin/activate && python -c 'import pytest, playwright' 2>/dev/null"; then
        print_success "Python dependencies are installed"
    else
        print_warning "Installing missing Python dependencies..."
        docker exec "$CONTAINER_NAME" bash -c "
            cd /app/RAG_evaluation && 
            source venv/bin/activate && 
            pip install pytest pytest-asyncio playwright
        "
        print_success "Python dependencies installed"
    fi
}

# Function to check and install Playwright browsers
check_playwright_browsers() {
    print_status "Checking Playwright browsers..."
    
    # Check if Chromium browser exists
    if docker exec "$CONTAINER_NAME" bash -c "[ -f /root/.cache/ms-playwright/chromium-*/chrome-linux/chrome ] 2>/dev/null"; then
        print_success "Playwright browsers are installed"
    else
        print_warning "Installing Playwright browsers..."
        docker exec "$CONTAINER_NAME" bash -c "
            cd /app/RAG_evaluation && 
            source venv/bin/activate && 
            playwright install
        "
        print_success "Playwright browsers installed"
    fi
}

# Function to check and install system dependencies
check_system_deps() {
    print_status "Checking system dependencies for Playwright..."
    
    # Check if essential system libraries exist
    if docker exec "$CONTAINER_NAME" bash -c "dpkg -l | grep -q libgtk-3-0 && dpkg -l | grep -q libasound2" 2>/dev/null; then
        print_success "System dependencies are installed"
    else
        print_warning "Installing system dependencies for Playwright..."
        docker exec "$CONTAINER_NAME" bash -c "
            cd /app/RAG_evaluation && 
            source venv/bin/activate && 
            playwright install-deps
        "
        print_success "System dependencies installed"
    fi
}

# Function to run the actual tests
run_tests() {
    print_status "Running E2E tests..."
    
    # Prepare pytest command
    local pytest_cmd="cd /app/RAG_evaluation && source venv/bin/activate && timeout ${TEST_TIMEOUT}s pytest tests/test_eight_metrics_e2e.py"
    
    if [ "$VERBOSE" = "true" ]; then
        pytest_cmd="$pytest_cmd -v -s --tb=long"
    else
        pytest_cmd="$pytest_cmd --tb=short"
    fi
    
    # Run the test with proper error handling
    if docker exec "$CONTAINER_NAME" bash -c "$pytest_cmd"; then
        print_success "🎉 E2E tests PASSED!"
        return 0
    else
        local exit_code=$?
        if [ $exit_code -eq 124 ]; then
            print_error "❌ Tests TIMED OUT after ${TEST_TIMEOUT} seconds"
        else
            print_error "❌ Tests FAILED with exit code $exit_code"
        fi
        return $exit_code
    fi
}

# Function to show usage
show_usage() {
    echo "RAG Evaluation E2E Test Runner - Headless Container Mode"
    echo "Runs end-to-end tests inside Docker container with automatic dependency management."
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -h, --help              Show this help message"
    echo "  -t, --timeout SECONDS   Set test timeout (default: 600)"
    echo "  -q, --quiet            Run in quiet mode (less verbose output)"
    echo "  -v, --verbose          Run in verbose mode (default)"
    echo ""
    echo "Environment Variables:"
    echo "  TEST_TIMEOUT           Test timeout in seconds (default: 600)"
    echo "  VERBOSE               Enable verbose output (true/false, default: true)"
    echo ""
    echo "Examples:"
    echo "  $0                     # Run with defaults"
    echo "  $0 -t 300             # Run with 5-minute timeout"
    echo "  $0 --quiet            # Run in quiet mode"
    echo "  TEST_TIMEOUT=900 $0   # Run with 15-minute timeout"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_usage
            exit 0
            ;;
        -t|--timeout)
            TEST_TIMEOUT="$2"
            shift 2
            ;;
        -q|--quiet)
            VERBOSE=false
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Main execution
main() {
    print_status "🚀 Starting RAG Evaluation E2E Test Runner (Headless Container Mode)"
    print_status "Container: $CONTAINER_NAME"
    print_status "Timeout: ${TEST_TIMEOUT}s"
    print_status "Verbose: $VERBOSE"
    echo ""
    
    # Run all checks and installations
    check_container
    check_venv
    check_python_deps
    check_playwright_browsers
    check_system_deps
    
    echo ""
    print_status "🧪 All dependencies verified, running tests..."
    echo ""
    
    # Run the tests
    run_tests
    local test_result=$?
    
    echo ""
    if [ $test_result -eq 0 ]; then
        print_success "✅ E2E test execution completed successfully!"
    else
        print_error "❌ E2E test execution failed!"
    fi
    
    exit $test_result
}

# Execute main function
main "$@"