import json
import asyncio
import logging
import time
import argparse
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

from mcp_clients.mcp_client_manager import MCPClientManager

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# =====================================================================
# Serialization
# =====================================================================


def to_serializable(obj: Any) -> Any:
    """
    Recursively convert objects into JSON-serializable structures.

    Contract (per tests):
    - Scalars -> string
    - list/tuple -> list of serialized values
    - dict -> recursive
    - objects with .dict() -> use it
    """
    if hasattr(obj, "dict") and callable(obj.dict):
        return to_serializable(obj.dict())

    if isinstance(obj, (list, tuple)):
        return [to_serializable(v) for v in obj]

    if isinstance(obj, dict):
        return {k: to_serializable(v) for k, v in obj.items()}

    return str(obj)


# =====================================================================
# MCP Discovery Manager
# =====================================================================


class MCPDiscoveryManager:
    """
    Discovers MCP tools and resources with:
    - filesystem locking
    - retries (linear or exponential)
    - validation
    - fallback support
    """

    LOCK_STALE_SECONDS = 300

    def __init__(
        self,
        discovery_file: str = "mcp_discovery.json",
        lock_file: str = "mcp_discovery.lock",
    ):
        self.discovery_file = discovery_file
        self.lock_file = lock_file
        self.discovery_path = Path(discovery_file)
        self.lock_path = Path(lock_file)

    # ------------------------------------------------------------------
    # Filesystem + locking
    # ------------------------------------------------------------------

    def _ensure_directory_exists(self) -> None:
        self.discovery_path.parent.mkdir(parents=True, exist_ok=True)

    def _lock_is_stale(self) -> bool:
        try:
            age = time.time() - self.lock_path.stat().st_mtime
            return age > self.LOCK_STALE_SECONDS
        except Exception:
            return True

    def _create_lock(self) -> bool:
        """
        Attempt to create a lock.
        Returns True if lock acquired.
        """
        if self.lock_path.exists():
            if self._lock_is_stale():
                logger.warning("[MCP] Removing stale lock")
                self._remove_lock()
            else:
                return False

        try:
            self.lock_path.touch()
            return True
        except Exception as e:
            logger.error(f"[MCP] Failed to create lock: {e}")
            return False

    def _remove_lock(self) -> None:
        try:
            if self.lock_path.exists():
                self.lock_path.unlink()
        except Exception as e:
            logger.error(f"[MCP] Failed to remove lock: {e}")

    def _wait_for_discovery(
        self, timeout: int = 120, interval: int = 2
    ) -> bool:
        """
        Wait for another process to finish discovery.
        """
        start = time.time()
        while time.time() - start < timeout:
            if not self.lock_path.exists():
                valid, _ = self.verify_discovery_file()
                if valid:
                    return True
            time.sleep(interval)
        return False

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate_discovery_data(self, data: Any) -> Tuple[bool, str]:
        if not isinstance(data, dict):
            return False, "Root is not a dict"

        for key in ("tools", "resources"):
            if key not in data:
                return False, f"Missing '{key}'"
            if not isinstance(data[key], dict):
                return False, f"'{key}' is not a dict"

        if not data["tools"] and not data["resources"]:
            return False, "Discovery data is empty"

        # Validate tools
        for server, tools in data["tools"].items():
            if not isinstance(tools, list):
                return False, f"tools for '{server}' not a list"
            for tool in tools:
                if not isinstance(tool, dict):
                    return False, f"Invalid tool entry for '{server}'"
                for field in ("name", "description", "inputSchema"):
                    if field not in tool:
                        return False, "missing required key"

        # Validate resources
        for server, resources in data["resources"].items():
            if not isinstance(resources, list):
                return False, f"resources for '{server}' not a list"
            for res in resources:
                if not isinstance(res, dict):
                    return False, f"Invalid resource entry for '{server}'"
                for field in ("uri", "name", "description"):
                    if field not in res:
                        return False, "missing required key"

        return True, "Valid"

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    async def _perform_discovery(self) -> Optional[Dict[str, Any]]:
        try:
            manager = MCPClientManager()
            all_tools = await manager.get_all_tools()
            all_resources = await manager.get_all_resources()

            discovery: Dict[str, Any] = {"tools": {}, "resources": {}}

            for server, tools in (all_tools or {}).items():
                if not isinstance(tools, list):
                    continue
                formatted = []
                for tool in tools:
                    if isinstance(tool, dict):
                        formatted.append(
                            {
                                "name": tool.get("name"),
                                "description": tool.get("description"),
                                "inputSchema": to_serializable(
                                    tool.get("inputSchema")
                                ),
                            }
                        )
                    else:
                        formatted.append(
                            {
                                "name": getattr(tool, "name", None),
                                "description": getattr(
                                    tool, "description", None
                                ),
                                "inputSchema": to_serializable(
                                    getattr(tool, "inputSchema", None)
                                ),
                            }
                        )
                if formatted:
                    discovery["tools"][server] = formatted

            for server, resources in (all_resources or {}).items():
                if not isinstance(resources, list):
                    continue
                formatted = []
                for res in resources:
                    if isinstance(res, dict):
                        formatted.append(
                            {
                                "uri": to_serializable(res.get("uri")),
                                "name": res.get("name"),
                                "description": res.get("description"),
                            }
                        )
                    else:
                        formatted.append(
                            {
                                "uri": to_serializable(
                                    getattr(res, "uri", None)
                                ),
                                "name": getattr(res, "name", None),
                                "description": getattr(
                                    res, "description", None
                                ),
                            }
                        )
                if formatted:
                    discovery["resources"][server] = formatted

            return discovery

        except Exception:
            logger.exception("[MCP] Discovery failed")
            return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def discover_and_save(
        self,
        max_retries: int = 3,
        retry_delay: float = 10.0,
        exponential_backoff: bool = True,
    ) -> bool:
        self._ensure_directory_exists()

        if not self._create_lock():
            waited = self._wait_for_discovery()
            if waited:
                return True
            # takeover
            self._remove_lock()
            if not self._create_lock():
                return False

        try:
            for attempt in range(max_retries):
                data = await self._perform_discovery()

                if data:
                    valid, _ = self._validate_discovery_data(data)
                    if valid:
                        with open(self.discovery_file, "w") as f:
                            json.dump(data, f, indent=2)
                        return True

                if attempt < max_retries - 1:
                    delay = (
                        retry_delay * (2**attempt)
                        if exponential_backoff
                        else retry_delay
                    )
                    await asyncio.sleep(delay)

            return False
        finally:
            self._remove_lock()

    def verify_discovery_file(self) -> Tuple[bool, Optional[str]]:
        if not self.discovery_path.exists():
            return False, "Discovery file does not exist"

        try:
            with open(self.discovery_file) as f:
                data = json.load(f)
        except json.JSONDecodeError:
            return False, "Discovery file is not valid JSON"
        except Exception as e:
            return False, str(e)

        valid, error = self._validate_discovery_data(data)
        if valid:
            return True, None
        return False, error

    async def ensure_discovery_ready(
        self,
        force_rediscovery: bool = False,
        allow_fallback: bool = False,
    ) -> bool:
        if not force_rediscovery:
            valid, _ = self.verify_discovery_file()
            if valid:
                return True

        success = await self.discover_and_save()
        if success:
            return True

        if allow_fallback:
            fallback = self._create_fallback_discovery()
            with open(self.discovery_file, "w") as f:
                json.dump(fallback, f, indent=2)
            return self.verify_discovery_file()[0]

        return False

    # ------------------------------------------------------------------
    # Fallback
    # ------------------------------------------------------------------

    def _create_fallback_discovery(self) -> Dict[str, Any]:
        return {
            "tools": {
                "knowledge_bases_mcp": [
                    {
                        "name": "query_knowledge_base",
                        "description": "Query knowledge base (FALLBACK)",
                        "inputSchema": {
                            "properties": {
                                "query": {"title": "Query", "type": "string"},
                                "knowledge_base_ids": {
                                    "items": {"type": "integer"},
                                    "title": "Knowledge Base Ids",
                                    "type": "array",
                                },
                                "top_k": {
                                    "default": "10",
                                    "title": "Top K",
                                    "type": "integer",
                                },
                            },
                            "required": ["query", "knowledge_base_ids"],
                            "type": "object",
                        },
                    }
                ]
            },
            "resources": {
                "knowledge_bases_mcp": [
                    {
                        "uri": "resource://server_info",
                        "name": "Vector Knowledge Base MCP Server",
                        "description": "Fallback MCP server",
                    }
                ]
            },
        }


# =====================================================================
# CLI Entrypoint
# =====================================================================


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-fallback", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    async def run() -> None:
        mgr = MCPDiscoveryManager()
        ok = await mgr.ensure_discovery_ready(
            allow_fallback=args.allow_fallback,
            force_rediscovery=args.force,
        )
        if not ok:
            raise SystemExit(1)

    asyncio.run(run())


if __name__ == "__main__":
    main()
