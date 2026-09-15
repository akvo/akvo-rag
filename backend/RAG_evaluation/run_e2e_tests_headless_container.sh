#!/bin/bash
# ==============================================================================
# Akvo RAG E2E Test Runner & Headless Quality Gate Orchestrator (TASK-OPS-501)
# ==============================================================================
# This script orchestrates the end-to-end quality assurance gates:
#   Stage 1: Backend Unit & Integration Tests (100% pass)
#   Stage 2: Vector KB Microservice Tests (100% pass)
#   Stage 3: Headless RAGAS Golden Set Evaluation (Faithfulness >= 0.85, etc.)
# ==============================================================================

set -e  # Exit immediately on unhandled error

# Container names
CONTAINER_BACKEND="akvo-rag-backend-1"
CONTAINER_VECTOR="akvo-rag-vector-kb-mcp-1"
CONTAINER_CHROMA="akvo-rag-chromadb-1"
CONTAINER_POSTGRES="akvo-rag-postgres-1"
CONTAINER_REDIS="akvo-rag-redis-1"

# Evaluation defaults
CSV_FILENAME=${CSV_FILENAME:-"kenya_drylands_short_evaluation.csv"}
KB_NAME=${KB_NAME:-"Kenya Drylands"}
MIN_FAITHFULNESS=${MIN_FAITHFULNESS:-0.85}
MIN_RELEVANCY=${MIN_RELEVANCY:-0.85}
MIN_GROUNDEDNESS=${MIN_GROUNDEDNESS:-0.90}
OUTPUT_DIR=${OUTPUT_DIR:-"/app/RAG_evaluation/performance_reports"}
SKIP_UNIT_TESTS=${SKIP_UNIT_TESTS:-false}
VERBOSE=${VERBOSE:-true}

# Colors for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

print_banner() {
    echo -e "\n${CYAN}${BOLD}================================================================================"
    echo -e " $1"
    echo -e "================================================================================${NC}\n"
}

print_status() {
    echo -e "${BLUE}[E2E GATE]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[E2E GATE] ✅${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[E2E GATE] ⚠️${NC} $1"
}

print_error() {
    echo -e "${RED}[E2E GATE] ❌${NC} $1"
}

# Parse command line options
while [[ $# -gt 0 ]]; do
    case $1 in
        --csv|--input-csv)
            CSV_FILENAME="$2"
            shift 2
            ;;
        --kb|--knowledge-base)
            KB_NAME="$2"
            shift 2
            ;;
        --min-faithfulness)
            MIN_FAITHFULNESS="$2"
            shift 2
            ;;
        --min-relevancy)
            MIN_RELEVANCY="$2"
            shift 2
            ;;
        --min-groundedness)
            MIN_GROUNDEDNESS="$2"
            shift 2
            ;;
        --output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --skip-unit-tests)
            SKIP_UNIT_TESTS=true
            shift
            ;;
        -h|--help)
            echo "Akvo RAG E2E Test & Headless Evaluation Quality Gate Runner"
            echo ""
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --csv FILENAME          Evaluation dataset CSV (default: kenya_drylands_short_evaluation.csv)"
            echo "  --kb NAME               Knowledge Base name or alias (default: Kenya Drylands)"
            echo "  --min-faithfulness VAL  Minimum faithfulness threshold (default: 0.85)"
            echo "  --min-relevancy VAL     Minimum answer relevancy threshold (default: 0.85)"
            echo "  --min-groundedness VAL  Minimum groundedness / context precision threshold (default: 0.90)"
            echo "  --output-dir PATH       Directory for reports (default: /app/RAG_evaluation/performance_reports)"
            echo "  --skip-unit-tests       Skip pytest unit/integration test stages"
            echo "  -h, --help              Show this help message"
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Function to check container health
check_containers() {
    print_status "Verifying active runtime containers..."
    local required_containers=("$CONTAINER_BACKEND" "$CONTAINER_VECTOR" "$CONTAINER_POSTGRES" "$CONTAINER_REDIS" "$CONTAINER_CHROMA")

    for container in "${required_containers[@]}"; do
        if ! docker ps --format "{{.Names}}" | grep -q "^${container}$"; then
            print_error "Container '${container}' is not running!"
            print_error "Please start the local stack: docker compose -f docker-compose.dev.yml up -d"
            exit 1
        fi
    done
    print_success "All required containers are active and healthy"
}

# Stage 1: Backend Unit & Integration Tests
run_backend_tests() {
    if [ "$SKIP_UNIT_TESTS" = "true" ]; then
        print_warning "Skipping Backend Unit Tests (--skip-unit-tests specified)"
        return 0
    fi

    print_banner "STAGE 1: Executing Backend Unit & Integration Tests"
    print_status "Running: docker exec $CONTAINER_BACKEND python -m pytest tests/ -v --tb=short"

    if docker exec "$CONTAINER_BACKEND" python -m pytest tests/ -v --tb=short; then
        print_success "Backend test suite PASSED with 100% success rate"
    else
        print_error "Backend test suite FAILED"
        exit 1
    fi
}

# Stage 2: Vector KB Microservice Tests
run_vector_kb_tests() {
    if [ "$SKIP_UNIT_TESTS" = "true" ]; then
        print_warning "Skipping Vector KB Microservice Tests (--skip-unit-tests specified)"
        return 0
    fi

    print_banner "STAGE 2: Executing Vector KB Microservice Test Suite"
    print_status "Running: docker exec $CONTAINER_VECTOR pytest tests/ -v --tb=short"

    if docker exec "$CONTAINER_VECTOR" pytest tests/ -v --tb=short; then
        print_success "Vector KB microservice test suite PASSED with 100% success rate"
    else
        print_error "Vector KB microservice test suite FAILED"
        exit 1
    fi
}

# Stage 3: Virtual Environment & ChromaDB Seeding Verification
verify_eval_environment() {
    print_banner "STAGE 3A: Verifying Evaluation Environment & Golden KB Seeding"
    print_status "Checking RAG evaluation virtualenv in $CONTAINER_BACKEND..."

    # Ensure venv exists or set up
    docker exec "$CONTAINER_BACKEND" bash -c "
        if [ ! -d /app/RAG_evaluation/venv ]; then
            echo 'Setting up RAG evaluation virtualenv...'
            bash /app/RAG_evaluation/setup_venv.sh
        fi
    "

    print_status "Verifying ChromaDB collection seeding for evaluation..."
    # Verify/seed KB 115 (Kenya Drylands) if collection is empty
    docker exec "$CONTAINER_VECTOR" python -m cli.seed_chroma_kbs --kb-id 115 --limit 500 || true

    print_success "Evaluation environment and knowledge base verified"
}

# Stage 3B: Headless RAGAS Golden Evaluation
run_headless_evaluation() {
    print_banner "STAGE 3B: Executing Headless RAGAS Golden Set Accuracy Evaluation"

    local csv_path="/app/RAG_evaluation/example_csv_inputs/${CSV_FILENAME}"
    if [[ "$CSV_FILENAME" == /* ]]; then
        csv_path="$CSV_FILENAME"
    fi

    print_status "Target Dataset:        $csv_path"
    print_status "Target Knowledge Base: $KB_NAME"
    print_status "Thresholds:            Faithfulness >= $MIN_FAITHFULNESS | Relevancy >= $MIN_RELEVANCY | Groundedness >= $MIN_GROUNDEDNESS"

    local eval_cmd="cd /app/RAG_evaluation && source venv/bin/activate && python headless_evaluation.py \
        --input-csv '$csv_path' \
        --kb '$KB_NAME' \
        --min-faithfulness $MIN_FAITHFULNESS \
        --min-relevancy $MIN_RELEVANCY \
        --min-groundedness $MIN_GROUNDEDNESS \
        --output-dir '$OUTPUT_DIR'"

    if docker exec "$CONTAINER_BACKEND" bash -c "$eval_cmd"; then
        print_success "Headless Golden Set Evaluation PASSED all quality gate thresholds!"
    else
        local exit_code=$?
        print_error "Headless Golden Set Evaluation FAILED with exit code $exit_code"
        exit $exit_code
    fi
}

# Main Execution Flow
main() {
    local start_time
    start_time=$(date +%s)

    print_banner "Akvo RAG End-to-End Quality Gate & Golden Set Accuracy Runner"
    check_containers

    run_backend_tests
    run_vector_kb_tests
    verify_eval_environment
    run_headless_evaluation

    local end_time
    end_time=$(date +%s)
    local duration=$((end_time - start_time))

    print_banner "🎉 ALL QUALITY GATES & ACCURACY BENCHMARKS PASSED SUCCESSFULLY (${duration}s)"
}

main "$@"