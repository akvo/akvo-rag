import json
import asyncio
import logging
import time
from typing import Dict, Any, Optional
from pathlib import Path

from mcp_clients.mcp_client_manager import MCPClientManager

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def to_serializable(obj: Any) -> Any:
    """
    Recursively convert objects to JSON-serializable formats.
    - Pydantic models -> dict
    - Lists/Tuples -> list
    - Dict -> dict with serialized values
    - AnyUrl/other -> str
    """
    if hasattr(obj, "dict"):  # Pydantic model
        return obj.dict()
    if isinstance(obj, (list, tuple)):
        return [to_serializable(o) for o in obj]
    if isinstance(obj, dict):
        return {k: to_serializable(v) for k, v in obj.items()}
    return str(obj)  # fallback


class MCPDiscoveryManager:
    """
    Handles discovery of MCP tools and resources with robust retry logic.
    Ensures discovery file is always created successfully before application starts.
    """

    def __init__(
        self,
        discovery_file: str = "mcp_discovery.json",
        lock_file: str = "mcp_discovery.lock",
    ):
        self.discovery_file = discovery_file
        self.lock_file = lock_file
        self.discovery_path = Path(discovery_file)
        self.lock_path = Path(lock_file)

    def _ensure_directory_exists(self) -> None:
        """Ensure the directory for discovery file exists."""
        try:
            self.discovery_path.parent.mkdir(parents=True, exist_ok=True)
            logger.info(
                f"[MCP] Ensured directory exists: {self.discovery_path.parent}"
            )
        except Exception as e:
            logger.error(f"[MCP] Failed to create directory: {e}")
            raise

    def _create_lock(self) -> bool:
        """
        Create a lock file to indicate discovery is in progress.
        Returns True if lock was created, False if lock already exists.
        """
        try:
            if self.lock_path.exists():
                # Check if lock is stale (older than 5 minutes)
                lock_age = time.time() - self.lock_path.stat().st_mtime
                if lock_age > 300:  # 5 minutes
                    logger.warning(
                        f"[MCP] Stale lock detected ({lock_age:.0f}s old), removing"
                    )
                    self.lock_path.unlink()
                else:
                    logger.info(
                        "[MCP] Discovery already in progress (lock exists)"
                    )
                    return False

            self.lock_path.touch()
            logger.info("[MCP] Created discovery lock file")
            return True
        except Exception as e:
            logger.error(f"[MCP] Failed to create lock: {e}")
            return False

    def _remove_lock(self) -> None:
        """Remove the lock file."""
        try:
            if self.lock_path.exists():
                self.lock_path.unlink()
                logger.info("[MCP] Removed discovery lock file")
        except Exception as e:
            logger.error(f"[MCP] Failed to remove lock: {e}")

    def _validate_discovery_data(
        self, data: Dict[str, Any]
    ) -> tuple[bool, str]:
        """
        Validate that discovery data has the expected structure.
        Returns (is_valid, error_message)
        """
        if not isinstance(data, dict):
            return False, "Discovery data is not a dict"

        if "tools" not in data or "resources" not in data:
            return False, "Discovery data missing 'tools' or 'resources' keys"

        if not isinstance(data["tools"], dict):
            return False, "'tools' is not a dict"

        if not isinstance(data["resources"], dict):
            return False, "'resources' is not a dict"

        # Check if data is completely empty
        if not data["tools"] and not data["resources"]:
            return False, "Both 'tools' and 'resources' are empty"

        # Validate structure of tools
        for server_name, tool_list in data["tools"].items():
            if not isinstance(tool_list, list):
                return False, f"Tools for '{server_name}' is not a list"

            for tool in tool_list:
                if not isinstance(tool, dict):
                    return False, f"Tool in '{server_name}' is not a dict"

                required_keys = ["name", "description", "inputSchema"]
                for key in required_keys:
                    if key not in tool:
                        return (
                            False,
                            f"Tool missing required key '{key}' in '{server_name}'",
                        )

        # Validate structure of resources
        for server_name, resource_list in data["resources"].items():
            if not isinstance(resource_list, list):
                return False, f"Resources for '{server_name}' is not a list"

            for resource in resource_list:
                if not isinstance(resource, dict):
                    return False, f"Resource in '{server_name}' is not a dict"

                required_keys = ["uri", "name", "description"]
                for key in required_keys:
                    if key not in resource:
                        return (
                            False,
                            f"Resource missing required key '{key}' in '{server_name}'",
                        )

        return True, "Valid"

    def _wait_for_discovery(
        self, timeout: int = 120, check_interval: int = 2
    ) -> bool:
        """
        Wait for another process to complete discovery.
        Returns True if discovery file becomes valid, False if timeout.
        """
        logger.info(
            f"[MCP] Waiting for discovery to complete (timeout: {timeout}s)"
        )
        start_time = time.time()

        while time.time() - start_time < timeout:
            # Check if lock is removed and file is valid
            if not self.lock_path.exists():
                is_valid, _ = self.verify_discovery_file()
                if is_valid:
                    logger.info("[MCP] Discovery completed by another process")
                    return True

            time.sleep(check_interval)

        logger.error(f"[MCP] Timeout waiting for discovery ({timeout}s)")
        return False

    async def _perform_discovery(self) -> Optional[Dict[str, Any]]:
        """
        Perform the actual MCP discovery.
        Returns discovery data if successful, None otherwise.
        """
        try:
            logger.info("[MCP] Starting MCP client manager...")
            manager = MCPClientManager()

            logger.info("[MCP] Fetching all tools...")
            all_tools_info = await manager.get_all_tools()

            logger.info("[MCP] Fetching all resources...")
            all_resources_info = await manager.get_all_resources()

            discovery_data: Dict[str, Any] = {"tools": {}, "resources": {}}

            # Format tools
            tools_count = 0
            for server_name, tool_list in all_tools_info.items():
                if isinstance(tool_list, list) and tool_list:
                    discovery_data["tools"][server_name] = [
                        {
                            "name": tool.name,
                            "description": tool.description or "",
                            "inputSchema": to_serializable(tool.inputSchema),
                        }
                        for tool in tool_list
                    ]
                    tools_count += len(tool_list)
                    logger.info(
                        f"[MCP] Discovered {len(tool_list)} tools for '{server_name}'"
                    )

            # Format resources
            resources_count = 0
            for server_name, resource_list in all_resources_info.items():
                if isinstance(resource_list, list) and resource_list:
                    discovery_data["resources"][server_name] = [
                        {
                            "uri": to_serializable(r.uri),
                            "name": r.name,
                            "description": r.description or "",
                        }
                        for r in resource_list
                    ]
                    resources_count += len(resource_list)
                    logger.info(
                        f"[MCP] Discovered {resources_count} resources for '{server_name}'"
                    )

            logger.info(
                f"[MCP] Total: {tools_count} tools, {resources_count} resources"
            )
            return discovery_data

        except Exception as e:
            logger.exception(f"[MCP] Discovery failed: {e}")
            return None

    async def discover_and_save(
        self,
        max_retries: int = 5,
        retry_delay: int = 10,
        exponential_backoff: bool = True,
    ) -> bool:
        """
        Discover all MCP tools and resources, then save to JSON file.
        Blocks until discovery is successful or all retries are exhausted.

        Args:
            max_retries: Maximum number of retry attempts
            retry_delay: Initial delay in seconds between retries
            exponential_backoff: Whether to use exponential backoff for retries

        Returns:
            bool: True if discovery succeeded, False otherwise
        """
        # Ensure directory exists
        self._ensure_directory_exists()

        # Try to create lock
        if not self._create_lock():
            # Another process is running discovery, wait for it
            success = self._wait_for_discovery()
            if success:
                return True

            logger.warning(
                "[MCP] Other discovery process failed or timed out, taking over"
            )
            # Force create lock
            self._remove_lock()
            if not self._create_lock():
                logger.error("[MCP] Cannot acquire discovery lock")
                return False

        try:
            current_delay = retry_delay

            for attempt in range(max_retries):
                logger.info(
                    f"[MCP] Discovery attempt {attempt + 1}/{max_retries}"
                )

                # Perform discovery
                discovery_data = await self._perform_discovery()

                if discovery_data is None:
                    logger.error(
                        f"[MCP] Discovery attempt {attempt + 1} returned no data"
                    )
                else:
                    # Validate discovered data
                    is_valid, error_msg = self._validate_discovery_data(
                        discovery_data
                    )

                    if not is_valid:
                        logger.error(
                            f"[MCP] Discovery data validation failed: {error_msg}"
                        )
                    else:
                        # Write to file
                        try:
                            with open(self.discovery_file, "w") as f:
                                json.dump(discovery_data, f, indent=2)

                            logger.info(
                                f"[MCP] ✅ Discovery data written to {self.discovery_file}"
                            )
                            logger.info(
                                f"[MCP] ✅ Discovered {len(discovery_data['tools'])} tool servers"
                            )
                            logger.info(
                                f"[MCP] ✅ Discovered {len(discovery_data['resources'])} resource servers"
                            )

                            # Verify written file
                            is_valid, _ = self.verify_discovery_file()
                            if is_valid:
                                return True
                            else:
                                logger.error(
                                    "[MCP] Written file validation failed"
                                )

                        except Exception as e:
                            logger.error(
                                f"[MCP] Failed to write discovery file: {e}"
                            )

                # Retry logic
                if attempt < max_retries - 1:
                    logger.warning(
                        f"[MCP] ⏳ Retrying in {current_delay} seconds..."
                    )
                    await asyncio.sleep(current_delay)

                    if exponential_backoff:
                        current_delay = min(
                            current_delay * 2, 60
                        )  # Max 60 seconds

            logger.error(
                f"[MCP] ❌ All {max_retries} discovery attempts failed"
            )
            return False

        finally:
            self._remove_lock()

    def verify_discovery_file(self) -> tuple[bool, Optional[str]]:
        """
        Verify that the discovery file exists and is valid.

        Returns:
            tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        try:
            if not self.discovery_path.exists():
                return (
                    False,
                    f"Discovery file {self.discovery_file} does not exist",
                )

            with open(self.discovery_file, "r") as f:
                data = json.load(f)

            is_valid, error_msg = self._validate_discovery_data(data)

            if not is_valid:
                return False, f"Invalid discovery data: {error_msg}"

            logger.info(
                f"[MCP] ✅ Discovery file {self.discovery_file} is valid"
            )
            return True, None

        except json.JSONDecodeError as e:
            return False, f"Discovery file is not valid JSON: {e}"
        except Exception as e:
            return False, f"Error verifying discovery file: {e}"

    async def ensure_discovery_ready(
        self, max_wait: int = 120, force_rediscovery: bool = False
    ) -> bool:
        """
        Ensure discovery file is ready and valid.
        If file doesn't exist or is invalid, run discovery.
        If another process is running discovery, wait for it.

        Args:
            max_wait: Maximum time to wait for discovery (seconds)
            force_rediscovery: Force rediscovery even if file exists

        Returns:
            bool: True if discovery file is ready, False otherwise
        """
        # Check if file already exists and is valid
        if not force_rediscovery:
            is_valid, error = self.verify_discovery_file()
            if is_valid:
                logger.info("[MCP] Discovery file already exists and is valid")
                return True
            else:
                logger.warning(
                    f"[MCP] Existing discovery file invalid: {error}"
                )

        # Check if discovery is in progress
        if self.lock_path.exists():
            logger.info("[MCP] Discovery in progress, waiting...")
            success = self._wait_for_discovery(timeout=max_wait)
            if success:
                return True
            logger.warning("[MCP] Wait timeout, will attempt discovery")

        # Run discovery
        logger.info("[MCP] Starting discovery process...")
        return await self.discover_and_save()


if __name__ == "__main__":

    async def main():
        manager = MCPDiscoveryManager()

        # Ensure discovery is ready (will wait or run as needed)
        success = await manager.ensure_discovery_ready()

        if success:
            logger.info("[MCP] ✅ Discovery completed successfully")

            # Verify one more time
            is_valid, error = manager.verify_discovery_file()
            if is_valid:
                logger.info("[MCP] ✅ Final verification passed")
            else:
                logger.error(f"[MCP] ❌ Final verification failed: {error}")
                exit(1)
        else:
            logger.error("[MCP] ❌ Discovery failed after all retries")
            exit(1)

    asyncio.run(main())
