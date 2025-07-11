# ✨ Prompt Service & Dynamic Prompt Support

We’ve introduced a **Prompt Service** that enables dynamic and centralized management of system prompts used in our AI-powered chat and RAG (Retrieval-Augmented Generation) features.


## ✅ Key Benefits

- **Flexible Prompt Updates**
  Prompts can now be updated without modifying application code or restarting services.

- **Centralized Management**
  All prompts are stored in the database, giving better control, visibility, and version tracking.

- **Support for Multiple Prompt Types**
  Prompts such as `contextualize_q_system_prompt`, `qa_flexible_prompt`, and `qa_strict_prompt` are modular and managed independently.

- **Fallback Defaults**
  If a specific prompt isn't found in the system, the application automatically uses a default version to ensure consistent behavior.


## 📚 Use Cases

- Fine-tune the **tone**, **style**, or **response behavior** of the assistant.
- Empower non-developers (via future admin panel or CMS) to modify assistant responses without backend changes.


## 🧩 Prompt Service Overview

The system includes a `PromptService` class responsible for:

- **Fetching active prompt content** by name (using enums for consistency).
- **Fallback handling**, ensuring the assistant functions even if prompts aren't present in the DB.
- **Encapsulation**, abstracting prompt logic away from business features and making it reusable across modules.

This service enables developers and non-developers alike to manage and iterate on prompts rapidly.


## 🗄️ Prompt Storage Model (Database Schema)

We use a versioned model for storing prompts, separating **prompt definition** from **prompt content** to allow flexibility and maintainability.

### `prompt_definitions` Table

Stores unique, logical identifiers for each type of prompt.

| Column     | Type    | Description                                      |
|------------|---------|--------------------------------------------------|
| `id`       | Integer | Primary key                                      |
| `name`     | String  | Unique prompt key from `PromptNameEnum` enum     |
| `created_at`, `updated_at` | Timestamp | Managed by `TimestampMixin`             |

Each definition maps to one or more prompt versions.


### `prompt_versions` Table

Stores the actual prompt text and versioning metadata.

| Column               | Type     | Description                                         |
|----------------------|----------|-----------------------------------------------------|
| `id`                 | Integer  | Primary key                                         |
| `prompt_definition_id` | FK (int) | Links to `prompt_definitions`                      |
| `content`            | Text     | The actual prompt used by the LLM                  |
| `version_number`     | Integer  | Indicates the version of the prompt                |
| `is_active`          | Boolean  | Marks if this version is currently in use          |
| `activated_by_user_id` | FK (int) | User ID who activated this version (nullable)      |
| `activation_reason`  | String   | Optional note on why this version was activated    |
| `created_at`, `updated_at` | Timestamp | Managed by `TimestampMixin`             |

This design supports future capabilities such as:
- Prompt version history and rollback
- Auditability of prompt changes


## 🧾 Prompt Enum Reference

The `PromptNameEnum` is the **single source of truth** for recognized prompt types in the application. Example values include:

```python
class PromptNameEnum(str, Enum):
    contextualize_q_system_prompt = "contextualize_q_system_prompt"
    qa_flexible_prompt = "qa_flexible_prompt"
    qa_strict_prompt = "qa_strict_prompt"
```

Using enums ensures type safety and consistency across code and database.

## ⚙️ Initial Setup

To initialize default prompt values into the database, run the following command inside the backend container:

```bash
# From your backend container
python -m app.seeder.seed_prompts
```

or from your terminal:

```bash
# From your terminal
docker compose exec backend python -m app.seeder.seed_prompts
```

This will insert default PromptDefinition and PromptVersion entries into your database.
