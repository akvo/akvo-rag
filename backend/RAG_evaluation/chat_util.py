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
from typing import Dict, List, Any, Tuple, AsyncGenerator, Optional
from datetime import datetime, timezone

logger = logging.getLogger("rag_evaluation")

class RagChatUtil:
    """Utility for interacting with Akvo RAG API to generate responses for evaluation."""

    def __init__(self, base_url: str = "http://localhost:8000", username: str = None, password: str = None):
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
            self.logs.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "operation": operation,
                "inputs": inputs if not isinstance(inputs, dict) or len(str(inputs)) < 1000 else "...(truncated)",
                "outputs": outputs if not isinstance(outputs, dict) or len(str(outputs)) < 1000 else "...(truncated)"
            })
            logger.info(f"Operation: {operation}")

    async def login(self) -> bool:
        """Login to the Akvo RAG API.

        Returns:
            bool: True if login successful, False otherwise
        """
        if not self.username or not self.password:
            self._log("login", {}, {"status": "failed", "reason": "No credentials provided"})
            return False

        login_url = f"{self.base_url}/api/auth/token"
        payload = {
            "username": self.username,
            "password": self.password
        }

        self._log("login", {"username": self.username}, "Logging in")

        try:
            response = await self.client.post(login_url, data=payload)
            if response.status_code == 200:
                token_data = response.json()
                self.token = token_data.get("access_token")
                self._log("login", {}, {"status": "success"})
                return True
            else:
                self._log("login", {}, {"status": "failed", "status_code": response.status_code})
                return False
        except Exception as e:
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

        headers = {
            "Authorization": f"Bearer {self.token}"
        }

        kb_url = f"{self.base_url}/api/knowledge-base"

        self._log("get_knowledge_bases", {}, "Getting knowledge bases")

        try:
            response = await self.client.get(kb_url, headers=headers)
            if response.status_code == 200:
                kbs = response.json()
                self._log("get_knowledge_bases", {}, {"status": "success", "count": len(kbs)})
                return kbs
            else:
                self._log("get_knowledge_bases", {}, {"status": "failed", "status_code": response.status_code})
                return []
        except Exception as e:
            self._log("get_knowledge_bases", {}, {"status": "error", "error": str(e)})
            return []

    async def get_knowledge_base_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a knowledge base by its name.

        Args:
            name: Name of the knowledge base

        Returns:
            Knowledge base if found, None otherwise
        """
        kbs = await self.get_knowledge_bases()

        self._log("get_knowledge_base_by_name", {"name": name}, {"total_kbs": len(kbs)})
        # Log the returned kbs
        self._log("get_knowledge_base_by_name", {"name": name}, {"kbs": kbs if len(kbs) < 10 else "...(truncated)"})

        for kb in kbs:
            if kb.get("name") == name:
                self._log("get_knowledge_base_by_name", {"name": name}, {"status": "found", "kb_id": kb.get("id")})
                return kb

        self._log("get_knowledge_base_by_name", {"name": name}, {"status": "not_found"})
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
            "Content-Type": "application/json"
        }

        chat_url = f"{self.base_url}/api/chat"

        payload = {
            "title": f"RAG Evaluation Chat {kb_ids}",
            "knowledge_base_ids": kb_ids
        }

        self._log("create_chat", payload, "Creating chat")

        try:
            response = await self.client.post(chat_url, json=payload, headers=headers)
            if response.status_code == 200:
                chat_data = response.json()
                self._log("create_chat", payload, {"status": "success", "chat_id": chat_data.get("id")})
                return chat_data
            else:
                self._log("create_chat", payload, {"status": "failed", "status_code": response.status_code})
                return None
        except Exception as e:
            self._log("create_chat", payload, {"status": "error", "error": str(e)})
            return None

    async def send_message(self, chat_id: int, message: str) -> AsyncGenerator[Tuple[str, Dict[str, Any]], None]:
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
            "Accept": "text/event-stream"
        }

        message_url = f"{self.base_url}/api/chat/{chat_id}/messages"

        payload = {
            "messages": [
                {"role": "user", "content": message}
            ]
        }

        self._log("send_message", {"chat_id": chat_id, "message": message}, "Sending message")

        try:
            async with self.client.stream("POST", message_url, json=payload, headers=headers) as response:
                if response.status_code != 200:
                    error = f"Error: {response.status_code}"
                    self._log("send_message", payload, {"status": "failed", "status_code": response.status_code})
                    yield error, {}
                    return

                full_response = ""
                context_data = {}

                async for chunk in response.aiter_text():
                    if chunk.strip():
                        # Parse SSE format
                        for line in chunk.split('\n'):
                            if line.startswith('0:'):
                                # Extract content
                                json_part = line[2:]
                                if not json_part.strip():
                                    continue  # Skip empty content
                                try:
                                    content = json.loads(json_part)
                                except json.JSONDecodeError as e:
                                    self._log("json_parse_error", {"line": line, "json_part": json_part}, {"error": str(e)})
                                    continue

                                # Check if it contains context
                                if "__LLM_RESPONSE__" in content:
                                    parts = content.split("__LLM_RESPONSE__")
                                    if len(parts) > 1:
                                        try:
                                            context_b64 = parts[0]
                                            context_json = base64.b64decode(context_b64).decode()
                                            context_data = json.loads(context_json)

                                            self._log("received_context", {"chat_id": chat_id},
                                                    {"num_chunks": len(context_data.get("context", []))})
                                        except Exception as e:
                                            self._log("parse_context", {"data": parts[0]}, {"error": str(e)})

                                    # Add actual response text
                                    if len(parts) > 1:
                                        response_text = parts[1]
                                        full_response += response_text
                                        yield response_text, context_data
                                else:
                                    # Regular response chunk
                                    full_response += content
                                    yield content, context_data

                self._log("send_message_complete", {"chat_id": chat_id},
                        {"status": "success", "response_length": len(full_response)})
        except Exception as e:
            error = f"Error: {str(e)}"
            self._log("send_message", payload, {"status": "error", "error": str(e)})
            yield error, {}

    async def generate_rag_response(self, query: str, kb_name: str) -> Dict[str, Any]:
        """Generate a RAG response for evaluation

        Args:
            query: The query to send
            kb_name: The name of the knowledge base to use

        Returns:
            Dictionary with query, response, and retrieval context
        """
        # Get KB by name
        kb = await self.get_knowledge_base_by_name(kb_name)
        if not kb:
            return {
                "query": query,
                "response": f"Error: Knowledge base '{kb_name}' not found",
                "contexts": [],
                "error": f"Knowledge base '{kb_name}' not found"
            }

        # Create chat
        chat = await self.create_chat([kb["id"]])
        if not chat:
            return {
                "query": query,
                "response": "Error: Failed to create chat",
                "contexts": [],
                "error": "Failed to create chat"
            }

        # Send message and collect response
        full_response = ""
        contexts = []

        async for text_chunk, context_data in self.send_message(chat["id"], query):
            full_response += text_chunk
            if context_data and "context" in context_data and context_data["context"]:
                contexts = context_data["context"]

        return {
            "query": query,
            "response": full_response,
            "contexts": contexts,
            "kb_id": kb["id"],
            "chat_id": chat["id"]
        }
