from fastapi import FastAPI

app = FastAPI(title="Image RAG MCP Server")


@app.get("/health")
def health_check():
    return {"status": "ok"}
