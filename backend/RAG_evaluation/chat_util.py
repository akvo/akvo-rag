"""
Chat utility for RAG evaluation.

This module provides a utility class for interacting with the Akvo RAG API
to generate RAG responses for evaluation.
"""

import json
import base64
import logging
import httpx
import asyncio
import time
from typing import Dict, List, Any, Tuple, AsyncGenerator, Optional
from datetime import datetime, timezone

logger = logging.getLogger("rag_evaluation")


class RagChatUtil:
    """
    Utility for interacting with Akvo RAG API to
    generate responses for evaluation.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        username: str = None,
        password: str = None,
    ):
        """Initialize the RAG chat utility.

        Args:
            base_url: Base URL of the Akvo RAG API
            username: Username for authentication
            password: Password for authentication
        """
        self.base_url = base_url
        self.username = username
        self.password = password
        self.token = None
        self.client = httpx.AsyncClient(timeout=60.0)
        self.instrumentation_enabled = False
        self.logs = []

        # Log initialization details
        logger.info("=== RAG CHAT UTIL INITIALIZED ===")
        logger.info(f"Base URL: '{base_url}'")
        logger.info(f"Username: '{username}'")
        logger.info(f"Password: {'***' if password else 'None'}")

    def enable_instrumentation(self):
        """Enable instrumentation for logging API interactions."""
        self.instrumentation_enabled = True
        self.logs = []

    def get_logs(self) -> List[Dict[str, Any]]:
        """Get the logs collected during API interactions."""
        return self.logs

    def _log(self, operation: str, inputs: Any, outputs: Any):
        """Log an operation with inputs and outputs.

        Args:
            operation: Name of the operation
            inputs: Input data
            outputs: Output data
        """
        if self.instrumentation_enabled:
            self.logs.append(
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "operation": operation,
                    "inputs": (
                        inputs
                        if not isinstance(inputs, dict)
                        or len(str(inputs)) < 1000
                        else "...(truncated)"
                    ),
                    "outputs": (
                        outputs
                        if not isinstance(outputs, dict)
                        or len(str(outputs)) < 1000
                        else "...(truncated)"
                    ),
                }
            )
            logger.info(f"Operation: {operation}")

    async def login(self) -> bool:
        """Login to the Akvo RAG API.

        Returns:
            bool: True if login successful, False otherwise
        """
        if not self.username or not self.password:
            self._log(
                "login",
                {},
                {"status": "failed", "reason": "No credentials provided"},
            )
            return False

        login_url = f"{self.base_url}/api/auth/token"
        payload = {"username": self.username, "password": self.password}

        logger.info(f"Attempting login to: {login_url}")
        logger.info(
            f"Login payload: username='{self.username}', password={'***' if self.password else 'None'}"  # noqa
        )
        self._log("login", {"username": self.username}, "Logging in")

        try:
            response = await self.client.post(login_url, data=payload)
            logger.info(f"Login response: status={response.status_code}")

            if response.status_code == 200:
                token_data = response.json()
                self.token = token_data.get("access_token")
                logger.info(
                    f"✅ Login successful - token received: {'***' if self.token_data else 'None'}"  # noqa
                )
                self._log("login", {}, {"status": "success"})
                return True
            else:
                logger.error(f"❌ Login failed: HTTP {response.status_code}")
                try:
                    error_text = response.text
                    logger.error(f"Login error response: {error_text}")
                except BaseException:
                    pass
                self._log(
                    "login",
                    {},
                    {"status": "failed", "status_code": response.status_code},
                )
                return False
        except Exception as e:
            logger.error(f"❌ Login exception: {str(e)}")
            self._log("login", {}, {"status": "error", "error": str(e)})
            return False

    async def get_knowledge_bases(self) -> List[Dict[str, Any]]:
        """Get all knowledge bases for the authenticated user.

        Returns:
            List of knowledge bases
        """
        if not self.token:
            await self.login()
            if not self.token:
                return []

        headers = {"Authorization": f"Bearer {self.token}"}

        kb_url = f"{self.base_url}/api/knowledge-base"

        self._log("get_knowledge_bases", {}, "Getting knowledge bases")

        try:
            response = await self.client.get(kb_url, headers=headers)
            if response.status_code == 200:
                kbs = response.json()
                self._log(
                    "get_knowledge_bases",
                    {},
                    {"status": "success", "count": len(kbs)},
                )

                # Log all available knowledge base names for debugging
                kb_names = [kb.get("name", "NO_NAME") for kb in kbs]
                logger.info(f"Available knowledge bases ({len(kbs)} total):")
                for i, name in enumerate(kb_names):
                    logger.info(f"  {i+1}. '{name}'")

                return kbs
            else:
                self._log(
                    "get_knowledge_bases",
                    {},
                    {"status": "failed", "status_code": response.status_code},
                )
                logger.error(
                    f"Failed to get knowledge bases: HTTP {response.status_code}"  # noqa
                )
                return []
        except Exception as e:
            self._log(
                "get_knowledge_bases", {}, {"status": "error", "error": str(e)}
            )
            logger.error(f"Exception getting knowledge bases: {str(e)}")
            return []

    async def get_knowledge_base_by_name(
        self, name: str
    ) -> Optional[Dict[str, Any]]:
        """Get a knowledge base by its name, alias, or ID.

        Args:
            name: Name or alias of the knowledge base

        Returns:
            Knowledge base if found, None otherwise
        """
        kbs = await self.get_knowledge_bases()

        self._log(
            "get_knowledge_base_by_name",
            {"name": name},
            {"total_kbs": len(kbs)},
        )

        logger.info(
            f"Searching for knowledge base: '{name}' among {len(kbs)} available KBs"  # noqa
        )

        # 1. Check direct ID match if name is numeric
        if isinstance(name, int) or (isinstance(name, str) and name.isdigit()):
            target_id = int(name)
            for kb in kbs:
                if kb.get("id") == target_id:
                    logger.info(
                        f"✅ FOUND KB by ID {target_id}: '{kb.get('name')}'"
                    )
                    return kb

        # 2. Check exact match (case-insensitive)
        clean_name = str(name).strip().lower()
        for kb in kbs:
            kb_name = kb.get("name", "").strip().lower()
            if kb_name == clean_name:
                logger.info(
                    f"✅ FOUND KB by exact name: '{kb.get('name')}' (ID: {kb.get('id')})"  # noqa
                )
                return kb

        # 3. Check well-known aliases in strict priority order
        alias_map = {
            "kenya drylands": [
                "tdt library #2",
                115,
                "tdt library",
                "kenya drylands",
                "kenya",
            ],
            "kenya_drylands": [
                "tdt library #2",
                115,
                "tdt library",
                "kenya drylands",
                "kenya",
            ],
            "kenya": [
                "tdt library #2",
                115,
                "tdt library",
                "kenya drylands",
            ],
            "living income": [
                "living income",
                116,
                "living income benchmark knowledge base",
                "rag li",
            ],
            "living income benchmark": [
                "living income",
                116,
                "living income benchmark knowledge base",
            ],
            "living income benchmark knowledge base": [
                "living income",
                116,
            ],
            "rag li": [
                "living income",
                116,
            ],
        }

        target_aliases = []
        for alias_key, alias_targets in alias_map.items():
            if (
                alias_key == clean_name
                or alias_key in clean_name
                or clean_name in alias_key
            ):
                for target in alias_targets:
                    if target not in target_aliases:
                        target_aliases.append(target)

        for target in target_aliases:
            if isinstance(target, int):
                for kb in kbs:
                    if kb.get("id") == target:
                        logger.info(
                            f"✅ FOUND KB by alias target ID {target}: '{kb.get('name')}'"  # noqa
                        )
                        return kb
            else:
                target_clean = str(target).strip().lower()
                for kb in kbs:
                    kb_name = kb.get("name", "").strip().lower()
                    if kb_name == target_clean:
                        logger.info(
                            f"✅ FOUND KB by exact alias '{target}': '{kb.get('name')}' (ID: {kb.get('id')})"  # noqa
                        )
                        return kb

        # 4. Check partial substring match (fallback)
        for kb in kbs:
            kb_name = kb.get("name", "").strip().lower()
            if clean_name in kb_name or kb_name in clean_name:
                logger.info(
                    f"✅ FOUND KB by substring: '{kb.get('name')}' (ID: {kb.get('id')})"  # noqa
                )
                return kb

        logger.error(
            f"❌ NOT FOUND: Knowledge base '{name}' not found in {len(kbs)} available knowledge bases"  # noqa
        )
        self._log(
            "get_knowledge_base_by_name",
            {"name": name},
            {"status": "not_found"},
        )
        return None

    async def create_chat(self, kb_ids: List[int]) -> Optional[Dict[str, Any]]:
        """Create a new chat with specified knowledge bases.

        Args:
            kb_ids: List of knowledge base IDs

        Returns:
            Chat data if created successfully, None otherwise
        """
        if not self.token:
            await self.login()
            if not self.token:
                return None

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

        chat_url = f"{self.base_url}/api/chat"

        # TODO:: Fix knowledge base IDs payload, sent as list
        payload = {
            "title": f"RAG Evaluation Chat {kb_ids}",
            "knowledge_base_ids": kb_ids,
        }

        self._log("create_chat", payload, "Creating chat")

        try:
            response = await self.client.post(
                chat_url, json=payload, headers=headers
            )
            if response.status_code == 200:
                chat_data = response.json()
                self._log(
                    "create_chat",
                    payload,
                    {"status": "success", "chat_id": chat_data.get("id")},
                )
                return chat_data
            else:
                self._log(
                    "create_chat",
                    payload,
                    {"status": "failed", "status_code": response.status_code},
                )
                return None
        except Exception as e:
            self._log(
                "create_chat", payload, {"status": "error", "error": str(e)}
            )
            return None

    async def send_message(
        self, chat_id: int, message: str
    ) -> AsyncGenerator[Tuple[str, Dict[str, Any]], None]:
        """Send a message to a chat and stream the response

        Args:
            chat_id: ID of the chat
            message: Message to send

        Yields:
            Tuples of (text_chunk, context_data)
        """
        if not self.token:
            await self.login()
            if not self.token:
                yield "Error: Not authenticated", {}
                return

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        }

        message_url = f"{self.base_url}/api/chat/{chat_id}/messages"

        payload = {"messages": [{"role": "user", "content": message}]}

        self._log(
            "send_message",
            {"chat_id": chat_id, "message": message},
            "Sending message",
        )

        try:
            async with self.client.stream(
                "POST", message_url, json=payload, headers=headers
            ) as response:
                if response.status_code != 200:
                    error = f"Error: {response.status_code}"
                    self._log(
                        "send_message",
                        payload,
                        {
                            "status": "failed",
                            "status_code": response.status_code,
                        },
                    )
                    yield error, {}
                    return

                full_response = ""
                context_data = {}
                sse_buffer = ""  # Buffer to accumulate SSE data across chunks
                context_processed = (
                    False  # Track if we've processed the context chunk
                )

                async for chunk in response.aiter_text():
                    if not chunk:
                        continue
                    sse_buffer += chunk

                    while "\n" in sse_buffer:
                        line, sse_buffer = sse_buffer.split("\n", 1)
                        line = line.strip()
                        if not line or not line.startswith("0:"):
                            continue

                        raw_content = line[2:].strip()
                        if not raw_content:
                            continue

                        # Check for base64 context prefix
                        if (
                            not context_processed
                            and "__LLM_RESPONSE__" in raw_content
                        ):
                            try:
                                # Strip outer JSON quotes if present
                                clean_content = raw_content
                                if clean_content.startswith(
                                    '"'
                                ) and clean_content.endswith('"'):
                                    try:
                                        clean_content = json.loads(
                                            clean_content
                                        )
                                    except Exception:
                                        clean_content = clean_content[1:-1]

                                parts = clean_content.split(
                                    "__LLM_RESPONSE__", 1
                                )
                                base64_part = parts[0]
                                response_part = (
                                    parts[1] if len(parts) > 1 else ""
                                )

                                # Base64 padding
                                pad = len(base64_part) % 4
                                if pad > 0:
                                    base64_part += "=" * (4 - pad)

                                decoded_bytes = base64.b64decode(base64_part)
                                context_data = json.loads(
                                    decoded_bytes.decode("utf-8")
                                )
                                num_chunks = len(
                                    context_data.get("context", [])
                                )
                                logger.info(
                                    f"✅ Successfully decoded retrieval context: {num_chunks} chunks"  # noqa
                                )
                                context_processed = True

                                if response_part:
                                    full_response += response_part
                                    yield response_part, context_data
                                else:
                                    # Yield context with empty text so receiver
                                    # stores it
                                    yield "", context_data
                                continue
                            except Exception as e:
                                logger.error(
                                    f"Error decoding base64 context: {e}"
                                )
                                context_processed = True

                        # Regular text chunk token
                        try:
                            if raw_content.startswith(
                                '"'
                            ) and raw_content.endswith('"'):
                                parsed_token = json.loads(raw_content)
                            else:
                                parsed_token = raw_content
                            full_response += parsed_token
                            yield parsed_token, context_data
                        except Exception:
                            full_response += raw_content
                            yield raw_content, context_data

                # Log completion
                logger.info(
                    f"SSE STREAM COMPLETE: response_length={len(full_response)}, context_processed={context_processed}"  # noqa
                )

                self._log(
                    "send_message_complete",
                    {"chat_id": chat_id},
                    {
                        "status": "success",
                        "response_length": len(full_response),
                    },
                )
        except Exception as e:
            error = f"Error: {str(e)}"
            self._log(
                "send_message", payload, {"status": "error", "error": str(e)}
            )
            yield error, {}

    async def generate_rag_response(
        self, query: str, kb_name: str
    ) -> Dict[str, Any]:
        """Generate a RAG response for evaluation

        Args:
            query: The query to send
            kb_name: The name of the knowledge base to use

        Returns:
            Dictionary with query, response, retrieval context,
            and response time
        """
        start_time = time.time()

        # Get KB by name
        kb = await self.get_knowledge_base_by_name(kb_name)
        if not kb:
            response_time = time.time() - start_time
            return {
                "query": query,
                "response": f"Error: Knowledge base '{kb_name}' not found",
                "contexts": [],
                "error": f"Knowledge base '{kb_name}' not found",
                "response_time": response_time,
            }

        # Create chat
        chat = await self.create_chat([kb["id"]])
        if not chat:
            response_time = time.time() - start_time
            return {
                "query": query,
                "response": "Error: Failed to create chat",
                "contexts": [],
                "error": "Failed to create chat",
                "response_time": response_time,
            }

        # Send message and collect response
        full_response = ""
        contexts = []

        async for text_chunk, context_data in self.send_message(
            chat["id"], query
        ):
            full_response += text_chunk
            if (
                context_data
                and "context" in context_data
                and context_data["context"]
            ):
                contexts = context_data["context"]

        response_time = time.time() - start_time

        return {
            "query": query,
            "response": full_response,
            "contexts": contexts,
            "kb_id": kb["id"],
            "chat_id": chat["id"],
            "response_time": response_time,
        }

    async def generate_rag_responses_batch(
        self,
        queries: List[str],
        kb_name: str,
        batch_size: int = 5,
        max_concurrent: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Generate RAG responses for multiple queries with
        batching and concurrency control.

        Args:
            queries: List of query strings
            kb_name: Name of the knowledge base
            batch_size: Number of queries to process in each batch
            max_concurrent: Maximum number of concurrent requests per batch

        Returns:
            List of response dictionaries
        """
        # Cache knowledge base lookup
        kb = await self.get_knowledge_base_by_name(kb_name)
        if not kb:
            # Return error for all queries
            error_result = {
                "response": f"Error: Knowledge base '{kb_name}' not found",
                "contexts": [],
                "error": f"Knowledge base '{kb_name}' not found",
                "response_time": 0,
            }
            return [{**error_result, "query": query} for query in queries]

        # Process queries in batches
        all_results = []
        for i in range(0, len(queries), batch_size):
            batch = queries[i : i + batch_size]  # noqa
            total_b = (len(queries) + batch_size - 1) // batch_size
            logger.info(
                f"Processing batch {i//batch_size + 1}/{total_b}: "
                f"{len(batch)} queries"
            )

            # Limit concurrency within batch
            semaphore = asyncio.Semaphore(max_concurrent)

            async def process_single_query(query: str) -> Dict[str, Any]:
                async with semaphore:
                    return await self._generate_single_rag_response_cached_kb(
                        query, kb
                    )

            # Process batch concurrently
            batch_tasks = [process_single_query(query) for query in batch]
            batch_results = await asyncio.gather(
                *batch_tasks, return_exceptions=True
            )

            # Handle exceptions
            for j, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    logger.error(
                        f"Error processing query '{batch[j]}': {str(result)}"
                    )
                    batch_results[j] = {
                        "query": batch[j],
                        "response": f"Error: {str(result)}",
                        "contexts": [],
                        "error": str(result),
                        "response_time": 0,  # Unknown time for exceptions
                    }

            all_results.extend(batch_results)

            # Small delay between batches to be nice to the API
            if i + batch_size < len(queries):
                await asyncio.sleep(0.5)

        return all_results

    async def _generate_single_rag_response_cached_kb(
        self, query: str, kb: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate RAG response for a single query with
        cached knowledge base info.

        Args:
            query: Query string
            kb: Knowledge base dictionary (pre-fetched)

        Returns:
            Response dictionary with timing information
        """
        start_time = time.time()

        try:
            # Create chat for this query
            chat = await self.create_chat([kb["id"]])
            if not chat:
                response_time = time.time() - start_time
                return {
                    "query": query,
                    "response": "Error: Failed to create chat",
                    "contexts": [],
                    "error": "Failed to create chat",
                    "response_time": response_time,
                }

            # Send message and collect response
            full_response = ""
            contexts = []

            async for text_chunk, context_data in self.send_message(
                chat["id"], query
            ):
                full_response += text_chunk
                if (
                    context_data
                    and "context" in context_data
                    and context_data["context"]
                ):
                    contexts = context_data["context"]

            response_time = time.time() - start_time

            return {
                "query": query,
                "response": full_response,
                "contexts": contexts,
                "kb_id": kb["id"],
                "chat_id": chat["id"],
                "response_time": response_time,
            }

        except Exception as e:
            response_time = time.time() - start_time
            logger.error(f"Error processing query '{query}': {str(e)}")
            return {
                "query": query,
                "response": f"Error: {str(e)}",
                "contexts": [],
                "error": str(e),
                "response_time": response_time,
            }
