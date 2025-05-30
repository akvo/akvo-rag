# 📚 Table of Contents

- [📚 Table of Contents](#-table-of-contents)
- [WebSocket API: `/ws/chat`](#websocket-api-wschat)
  - [📡 Endpoint](#-endpoint)
  - [🔐 Authentication Flow](#-authentication-flow)
    - [🔑 Auth Message Format](#-auth-message-format)
    - [✅ On Success](#-on-success)
    - [❌ On Failure](#-on-failure)
  - [💬 Chat Interaction](#-chat-interaction)
    - [💬 Chat Message Format](#-chat-message-format)
    - [🔁 Message Roles](#-message-roles)
  - [🧠 Knowledge Base Linking](#-knowledge-base-linking)
  - [🔄 Streaming Responses](#-streaming-responses)
    - [▶️ Start of Response](#️-start-of-response)
    - [📦 Streamed Chunks](#-streamed-chunks)
    - [⏹️ End of Response](#️-end-of-response)
  - [❗ Error Handling](#-error-handling)
  - [🔌 Disconnection](#-disconnection)
  - [📝 Summary](#-summary)

---

# WebSocket API: `/ws/chat`

This WebSocket endpoint allows authenticated users to interact with a chatbot that uses knowledge bases specific to each user or shared by superusers.

## 📡 Endpoint

```
ws://<your-backend-domain>/ws/chat
```

## 🔐 Authentication Flow

Upon initial connection, the client **must send an authentication message** as the first WebSocket message:

### 🔑 Auth Message Format

```json
{
  "type": "auth",
  "visitor_id": <Visitor ID>,
  "kb_id": <KnowledgeBase ID>
}
```

### ✅ On Success

```json
{
  "type": "info",
  "message": "Authentication successful"
}
```

### ❌ On Failure

The server will send an error message and close the connection:

```json
{
  "type": "error",
  "message": "Knowledge base not found or unauthorized"
}
```

---

## 💬 Chat Interaction

After authentication, clients can send chat messages by providing a list of previous message history.

### 💬 Chat Message Format

```json
{
  "type": "chat",
  "messages": [
    { "role": "system", "content": "You are a helpful assistant." },
    { "role": "user", "content": "Hello, who are you?" }
  ]
}
```

### 🔁 Message Roles

- `system`: (Optional) Instruction or context for the assistant
- `user`: Input from the user
- `assistant`: (Optional) Previous responses from the assistant

> **Note:** The last message in the array **must** be from the `user`.

---

## 🧠 Knowledge Base Linking

The system uses the `kb_id` from the auth payload to:

- Validate user access (owner or superuser-shared)
- Link the user’s session to a `Chat` entity
- Create a new `Chat` if one does not already exist for this user and knowledge base

---

## 🔄 Streaming Responses

Once a valid chat request is received, the server responds in **streamed chunks**:

### ▶️ Start of Response

```json
{
  "type": "start",
  "message": "Generating response..."
}
```

### 📦 Streamed Chunks

```json
{
  "type": "response_chunk",
  "content": "partial text"
}
```

These messages will continue until the full response is sent.

### ⏹️ End of Response

```json
{
  "type": "end",
  "message": "Response generation completed"
}
```

---

## ❗ Error Handling

In case of validation or runtime errors, the following message is sent:

```json
{
  "type": "error",
  "message": "Detailed error message"
}
```

---

## 🔌 Disconnection

If the WebSocket is closed during message generation, the server logs a warning and stops the response stream.

---

## 📝 Summary

| Feature               | Description |
|-----------------------|-------------|
| Auth Required         | ✅ Yes (JWT Token + KnowledgeBase ID) |
| Message Format        | JSON |
| Response Type         | Streamed JSON |
| Chat Creation         | Auto-create if not exists for user & KB |
| Error Handling        | Structured error messages |

