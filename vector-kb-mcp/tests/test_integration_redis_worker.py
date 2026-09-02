import asyncio
import json
import time
import pytest
import redis.asyncio as redis

from core.config import settings
from main import VectorMCPWorker


@pytest.mark.asyncio
async def test_real_redis_rpc_roundtrip(mock_openai_client):
    """Test full RPC roundtrip against live Redis broker in Docker network."""
    # Test Redis connectivity
    try:
        r = redis.from_url(settings.REDIS_URL, decode_responses=True)
        await r.ping()
    except Exception as exc:
        pytest.skip(
            f"Live Redis not accessible ({exc}); skipping integration test."
        )

    worker = VectorMCPWorker()
    worker.redis_client = r
    worker.openai_client = mock_openai_client

    await worker.initialize(skip_connection_init=False)

    # Start worker event loop in background task
    worker_task = asyncio.create_task(worker.run())
    await asyncio.sleep(0.05)

    try:
        # Enqueue request
        correlation_id = f"test-real-rpc-{int(time.time() * 1000)}"
        req_payload = {
            "correlation_id": correlation_id,
            "tool_name": "list_knowledge_bases",
            "arguments": {},
        }

        start_time = time.perf_counter()
        await r.rpush(settings.REQUEST_QUEUE, json.dumps(req_payload))

        # Await response from correlation response queue
        resp_key = f"{settings.RESPONSE_PREFIX}:{correlation_id}"
        item = await r.blpop(resp_key, timeout=3)
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        assert (
            item is not None
        ), "Did not receive response on correlation queue"
        _, raw_resp = item
        resp = json.loads(raw_resp)
        assert resp["status"] == "ok"
        assert resp["data"] == {"knowledge_bases": []}
        assert elapsed_ms < 100.0  # RPC roundtrip well within sub-100ms budget

    finally:
        await worker.shutdown()
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass
        await r.aclose()
