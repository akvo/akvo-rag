#!/bin/sh
set -e

# Ensure upload directory exists and permissions are set
UPLOAD_DIR="/mnt/uploads"
mkdir -p $UPLOAD_DIR
chmod 777 $UPLOAD_DIR

# -------------------------------------------
# FOR DEV ONLY: Install dependencies once
# -------------------------------------------
PIP_CACHE_DIR="/app/.pip"
if [ "$ENVIRONMENT" = "development" ]; then
    echo "Installing system dependencies..."
    apt-get update -qq && apt-get install -y -qq \
    build-essential \
    default-libmysqlclient-dev \
    pkg-config \
    netcat-traditional
    
    echo "⏳ Installing Python dependencies..."
    mkdir -p "$PIP_CACHE_DIR"
    pip install -q --upgrade pip
    pip install -q --cache-dir="$PIP_CACHE_DIR" -r requirements.txt || \
    (echo "Retrying in 5s..." && sleep 5 && pip install -q --cache-dir="$PIP_CACHE_DIR" -r requirements.txt) || \
    (echo "Retrying in 10s..." && sleep 10 && pip install -q --cache-dir="$PIP_CACHE_DIR" -r requirements.txt)
    
    # Ensure uploads folder exists
    mkdir -p /app/uploads
fi

# -------------------------------------------
echo "Waiting for MySQL..."
DB_HOST=${MYSQL_SERVER:-db}
DB_PORT=${MYSQL_PORT:-3306}
while ! nc -z $DB_HOST $DB_PORT; do
    sleep 1
done
echo "✅ MySQL started"

echo "Running migrations..."
if alembic upgrade head; then
    echo "✅ Migrations completed successfully"
else
    echo "❌ Migration failed"
    exit 1
fi

# -------------------------------------------
# Function to run Initial Prompt Seeder
# -------------------------------------------
run_initial_prompt_seeder() {
    echo "🚀 Running initial prompt seeder..."
    if ! python -m app.seeder.seed_prompts; then
        echo "⚠️ Initial prompt seeder failed, continuing startup..."
        return 1
    else
        echo "✅ Initial prompt seeder finished successfully"
        return 0
    fi
}

# -------------------------------------------
# Function to run MCP discovery with retries
# CRITICAL: This MUST succeed before app starts
# -------------------------------------------
run_mcp_discovery_manager() {
    echo "🚀 Running MCP discovery manager..."
    echo "⏳ This may take a few moments..."
    
    # Run discovery with increased verbosity
    if python -m mcp_clients.mcp_discovery_manager; then
        echo "✅ MCP discovery manager completed successfully"
        
        # Verify the discovery file exists and is valid
        if [ -f "mcp_discovery.json" ]; then
            echo "✅ Discovery file created: mcp_discovery.json"
            
            # Check file size
            FILE_SIZE=$(stat -f%z "mcp_discovery.json" 2>/dev/null || stat -c%s "mcp_discovery.json" 2>/dev/null || echo "0")
            if [ "$FILE_SIZE" -gt 100 ]; then
                echo "✅ Discovery file size: ${FILE_SIZE} bytes"
                return 0
            else
                echo "⚠️ Discovery file is too small (${FILE_SIZE} bytes), may be invalid"
                return 1
            fi
        else
            echo "❌ Discovery file not found after successful run"
            return 1
        fi
    else
        echo "❌ MCP discovery manager failed"
        return 1
    fi
}

# -------------------------------------------
# Function to create minimal fallback discovery file
# -------------------------------------------
create_fallback_discovery() {
    echo "⚠️ Creating minimal fallback discovery file..."
    cat > mcp_discovery.json <<EOF
{
  "tools": {
    "knowledge_bases_mcp": [
      {
        "name": "query_knowledge_base",
        "description": "Query a specific knowledge base return answer with context. (FALLBACK MODE)",
        "inputSchema": {
          "properties": {
            "query": {
              "title": "Query",
              "type": "string"
            },
            "knowledge_base_ids": {
              "items": {
                "type": "integer"
              },
              "title": "Knowledge Base Ids",
              "type": "array"
            },
            "top_k": {
              "default": "10",
              "title": "Top K",
              "type": "integer"
            }
          },
          "required": ["query", "knowledge_base_ids"],
          "type": "object"
        }
      }
    ]
  },
  "resources": {
    "knowledge_bases_mcp": [
      {
        "uri": "resource://server_info",
        "name": "Vector Knowledge Base MCP Server",
        "description": "A secure MCP server that provides access to vector-based knowledge bases. It exposes tools and resources for querying, retrieving, and managing knowledge base documents using similarity search. This server allows LLM-powered agents to discover relevant context across multiple knowledge bases and return grounded responses with supporting evidence. (FALLBACK MODE)"
      }
    ]
  }
}
EOF
    echo "⚠️ Fallback discovery file created"
}

# -------------------------------------------
# Wait for MCP discovery with optional fallback
# -------------------------------------------
wait_for_mcp_discovery() {
    MAX_ATTEMPTS=3
    ATTEMPT=1
    ALLOW_FALLBACK=${MCP_DISCOVERY_ALLOW_FALLBACK:-true}
    
    while [ $ATTEMPT -le $MAX_ATTEMPTS ]; do
        echo "📋 MCP Discovery attempt $ATTEMPT of $MAX_ATTEMPTS"
        
        if run_mcp_discovery_manager; then
            echo "✅ MCP discovery ready"
            return 0
        fi
        
        if [ $ATTEMPT -lt $MAX_ATTEMPTS ]; then
            WAIT_TIME=$((ATTEMPT * 10))
            echo "⏳ Waiting ${WAIT_TIME} seconds before retry..."
            sleep $WAIT_TIME
        fi
        
        ATTEMPT=$((ATTEMPT + 1))
    done
    
    echo "❌ MCP discovery failed after $MAX_ATTEMPTS attempts"
    
    # Check if fallback is allowed
    if [ "$ALLOW_FALLBACK" = "true" ]; then
        echo "⚠️ MCP_DISCOVERY_ALLOW_FALLBACK=true, using fallback mode"
        create_fallback_discovery
        echo "⚠️ Application will start with LIMITED FUNCTIONALITY"
        return 0
    else
        echo "❌ Cannot start application without valid MCP discovery data"
        echo "💡 Set MCP_DISCOVERY_ALLOW_FALLBACK=true to allow degraded mode"
        exit 1
    fi
}

# -------------------------------------------
# Start FastAPI with proper dependency checks
# -------------------------------------------
start_application() {
    echo "🚀 Starting application..."
    
    if [ "$ENVIRONMENT" = "development" ]; then
        echo "🔧 Development mode"
        uvicorn app.main:app \
        --host 0.0.0.0 \
        --port 8000 \
        --proxy-headers \
        --forwarded-allow-ips="*" \
        --reload
    else
        echo "🚀 Production mode"
        uvicorn app.main:app \
        --host 0.0.0.0 \
        --port 8000 \
        --proxy-headers \
        --forwarded-allow-ips="*"
    fi
}

# -------------------------------------------
# Main execution flow
# -------------------------------------------
echo "=========================================="
echo "🚀 Application Startup Sequence"
echo "=========================================="

# Step 1: Run initial prompt seeder (non-blocking)
echo ""
echo "Step 1: Initial Prompt Seeder"
run_initial_prompt_seeder || echo "⚠️ Continuing without prompt seeder"

# Step 2: Wait for MCP discovery (BLOCKING - must succeed)
echo ""
echo "Step 2: MCP Discovery (REQUIRED)"
wait_for_mcp_discovery

# Step 3: Start the application
echo ""
echo "Step 3: Starting Application"
echo "=========================================="
start_application