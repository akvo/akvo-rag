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
        
        # Log initialization details
        logger.info(f"=== RAG CHAT UTIL INITIALIZED ===")
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

        logger.info(f"Attempting login to: {login_url}")
        logger.info(f"Login payload: username='{self.username}', password={'***' if self.password else 'None'}")
        self._log("login", {"username": self.username}, "Logging in")

        try:
            response = await self.client.post(login_url, data=payload)
            logger.info(f"Login response: status={response.status_code}")
            
            if response.status_code == 200:
                token_data = response.json()
                self.token = token_data.get("access_token")
                logger.info(f"✅ Login successful - token received: {'***' if self.token else 'None'}")
                self._log("login", {}, {"status": "success"})
                return True
            else:
                logger.error(f"❌ Login failed: HTTP {response.status_code}")
                try:
                    error_text = response.text
                    logger.error(f"Login error response: {error_text}")
                except:
                    pass
                self._log("login", {}, {"status": "failed", "status_code": response.status_code})
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
                
                # Log all available knowledge base names for debugging
                kb_names = [kb.get("name", "NO_NAME") for kb in kbs]
                logger.info(f"Available knowledge bases ({len(kbs)} total):")
                for i, name in enumerate(kb_names):
                    logger.info(f"  {i+1}. '{name}'")
                
                return kbs
            else:
                self._log("get_knowledge_bases", {}, {"status": "failed", "status_code": response.status_code})
                logger.error(f"Failed to get knowledge bases: HTTP {response.status_code}")
                return []
        except Exception as e:
            self._log("get_knowledge_bases", {}, {"status": "error", "error": str(e)})
            logger.error(f"Exception getting knowledge bases: {str(e)}")
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
        
        # Enhanced logging for knowledge base search
        logger.info(f"Searching for knowledge base: '{name}'")
        logger.info(f"Comparing against {len(kbs)} available knowledge bases...")
        
        for i, kb in enumerate(kbs):
            kb_name = kb.get("name", "NO_NAME")
            is_match = kb_name == name
            logger.info(f"  KB {i+1}: '{kb_name}' -> Match: {is_match}")
            
            if is_match:
                kb_id = kb.get("id")
                logger.info(f"✅ FOUND: Knowledge base '{name}' with ID: {kb_id}")
                self._log("get_knowledge_base_by_name", {"name": name}, {"status": "found", "kb_id": kb_id})
                return kb

        logger.error(f"❌ NOT FOUND: Knowledge base '{name}' not found in {len(kbs)} available knowledge bases")
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
                sse_buffer = ""  # Buffer to accumulate SSE data across chunks
                context_processed = False  # Track if we've processed the context chunk

                async for chunk in response.aiter_text():
                    if chunk.strip():
                        # Add to buffer for complete SSE message reconstruction
                        sse_buffer += chunk
                        
                        # Process complete SSE lines
                        lines = sse_buffer.split('\n')
                        # Keep last incomplete line in buffer for next chunk
                        sse_buffer = lines[-1] if not sse_buffer.endswith('\n') else ""
                        
                        for line in lines[:-1] if not sse_buffer.endswith('\n') else lines:
                            if line.startswith('0:'):
                                # Extract raw JSON content from SSE format
                                raw_content = line[2:].strip()
                                if not raw_content:
                                    continue
                                
                                logger.info(f"RAW SSE LINE: '{raw_content[:100]}...'")
                                
                                # Check if this might be base64 context data first
                                if not context_processed and raw_content.startswith('"') and len(raw_content) > 100:
                                    # This looks like a long quoted string - likely base64 context
                                    try:
                                        parsed_content = json.loads(raw_content)
                                        # This is a valid JSON string, check if it contains base64 + separator
                                        if "__LLM_RESPONSE__" in parsed_content:
                                            logger.info(f"PROCESSING BASE64 CONTEXT WITH SEPARATOR: '{parsed_content[:50]}...'")
                                            parts = parsed_content.split("__LLM_RESPONSE__", 1)
                                            base64_part = parts[0]
                                            response_part = parts[1] if len(parts) > 1 else ""
                                            
                                            try:
                                                # Add base64 padding if needed
                                                padding_needed = 4 - len(base64_part) % 4
                                                if padding_needed != 4:
                                                    base64_part += '=' * padding_needed
                                                
                                                # Decode base64 context
                                                context_json = base64.b64decode(base64_part).decode()
                                                context_data = json.loads(context_json)
                                                
                                                logger.info(f"SUCCESSFULLY PARSED CONTEXT: {len(context_data.get('context', []))} chunks")
                                                self._log("received_context", {"chat_id": chat_id},
                                                        {"num_chunks": len(context_data.get("context", []))})
                                                
                                                context_processed = True
                                                
                                                # If there's response text after separator, yield it
                                                if response_part:
                                                    full_response += response_part
                                                    yield response_part, context_data
                                                    
                                            except Exception as e:
                                                logger.error(f"ERROR PARSING CONTEXT: {e}")
                                                self._log("parse_context_error", {"data": base64_part[:100]}, {"error": str(e)})
                                                # Treat as regular content if parsing fails
                                                full_response += parsed_content
                                                yield parsed_content, context_data
                                                context_processed = True
                                        else:
                                            # This might be base64 context without separator yet - check if it looks like base64
                                            if len(parsed_content) > 50 and all(c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=' for c in parsed_content[:50]):
                                                logger.info("BASE64 CONTENT WITHOUT SEPARATOR - might be truncated, treating as response")
                                                full_response += parsed_content
                                                yield parsed_content, context_data
                                            else:
                                                # Regular response text
                                                full_response += parsed_content
                                                yield parsed_content, context_data
                                    except json.JSONDecodeError:
                                        # Not valid JSON, skip
                                        logger.info(f"UNPARSEABLE QUOTED STRING: '{raw_content[:50]}...'")
                                        continue
                                else:
                                    # Try to parse as complete JSON (normal response text)
                                    try:
                                        parsed_content = json.loads(raw_content)
                                        # Regular response text
                                        full_response += parsed_content
                                        yield parsed_content, context_data
                                        continue
                                        
                                    except json.JSONDecodeError:
                                        # Not valid JSON, skip
                                        logger.info(f"UNPARSEABLE CONTENT: '{raw_content[:50]}...'")
                                        continue

                # Log completion
                logger.info(f"SSE STREAM COMPLETE: response_length={len(full_response)}, context_processed={context_processed}")

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
            Dictionary with query, response, retrieval context, and response time
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
                "response_time": response_time
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
                "response_time": response_time
            }

        # Send message and collect response
        full_response = ""
        contexts = []

        async for text_chunk, context_data in self.send_message(chat["id"], query):
            full_response += text_chunk
            if context_data and "context" in context_data and context_data["context"]:
                contexts = context_data["context"]

        response_time = time.time() - start_time
        
        return {
            "query": query,
            "response": full_response,
            "contexts": contexts,
            "kb_id": kb["id"],
            "chat_id": chat["id"],
            "response_time": response_time
        }

    async def generate_rag_responses_batch(self, queries: List[str], kb_name: str, 
                                         batch_size: int = 5, 
                                         max_concurrent: int = 3) -> List[Dict[str, Any]]:
        """Generate RAG responses for multiple queries with batching and concurrency control.
        
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
                "response_time": 0
            }
            return [{**error_result, "query": query} for query in queries]

        # Process queries in batches
        all_results = []
        for i in range(0, len(queries), batch_size):
            batch = queries[i:i + batch_size]
            logger.info(f"Processing batch {i//batch_size + 1}/{(len(queries) + batch_size - 1)//batch_size}: {len(batch)} queries")
            
            # Limit concurrency within batch
            semaphore = asyncio.Semaphore(max_concurrent)
            
            async def process_single_query(query: str) -> Dict[str, Any]:
                async with semaphore:
                    return await self._generate_single_rag_response_cached_kb(query, kb)
            
            # Process batch concurrently
            batch_tasks = [process_single_query(query) for query in batch]
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Handle exceptions
            for j, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    logger.error(f"Error processing query '{batch[j]}': {str(result)}")
                    batch_results[j] = {
                        "query": batch[j],
                        "response": f"Error: {str(result)}",
                        "contexts": [],
                        "error": str(result),
                        "response_time": 0  # Unknown time for exceptions
                    }
            
            all_results.extend(batch_results)
            
            # Small delay between batches to be nice to the API
            if i + batch_size < len(queries):
                await asyncio.sleep(0.5)
        
        return all_results

    async def _generate_single_rag_response_cached_kb(self, query: str, kb: Dict[str, Any]) -> Dict[str, Any]:
        """Generate RAG response for a single query with cached knowledge base info.
        
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
                    "response_time": response_time
                }

            # Send message and collect response
            full_response = ""
            contexts = []

            async for text_chunk, context_data in self.send_message(chat["id"], query):
                full_response += text_chunk
                if context_data and "context" in context_data and context_data["context"]:
                    contexts = context_data["context"]

            response_time = time.time() - start_time
            
            return {
                "query": query,
                "response": full_response,
                "contexts": contexts,
                "kb_id": kb["id"],
                "chat_id": chat["id"],
                "response_time": response_time
            }
            
        except Exception as e:
            response_time = time.time() - start_time
            logger.error(f"Error processing query '{query}': {str(e)}")
            return {
                "query": query,
                "response": f"Error: {str(e)}",
                "contexts": [],
                "error": str(e),
                "response_time": response_time
            }
