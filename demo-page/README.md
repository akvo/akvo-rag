# Akvo RAG Chat Assistant Example

This is a **simple static HTML example** demonstrating how to embed and configure the `akvo-rag-js` chat widget [npm package](https://www.npmjs.com/package/akvo-rag-js).

---

## 🌟 Overview

This project includes:

- An `index.html` page to render the chat widget and provide example queries.
- A `config.js` file containing different chat configurations.
- Basic styling and assets (Akvo logo, etc.).

It’s meant as a **reference implementation** for integrating the Akvo RAG Chat Assistant into your own website or application.

---

## 📁 Project Structure

```bash
.
├── index.html # Main HTML page
├── config.js # Chat widget configurations
├── assets/
│ ├── styles/style.css # Custom styling
│ └── images/akvo-logo.png # Akvo logo
```

---

## 🚀 Getting Started

1️⃣ Clone or download this repository.

2️⃣ Open `index.html` in your web browser.

3️⃣ To switch between different knowledge base configurations, use the `docs` parameter in the URL:

| URL Parameter       | Description                                    |
|----------------------|------------------------------------------------|
| `docs=500`          | UNEP Knowledge Base (500 docs)                 |
| `docs=250`          | UNEP Knowledge Base (250 docs)                 |
| `docs=living_income`| Living Income Benchmark Knowledge Base         |
| *(empty)*           | Default configuration with multiple KB options |

Example:
```bash
http://localhost/index.html?docs=500
```

---

## ⚙️ Configuration Details

All chat widget settings are handled in `config.js`:

```javascript
window.config_default = {
  title: "Akvo RAG",
  kb_options: [
    { kb_id: 1, label: "Knowledge Base 1" },
    { kb_id: 2, label: "Knowledge Base 2" },
  ],
  wsURL: "ws://localhost/ws/chat",
};

window.config_500 = {
  title: "UNEP Assistant",
  kb_id: 25,
  wsURL: "ws://localhost/ws/chat",
};

// ... other configurations
```

To add more knowledge bases or customize existing ones, simply edit this file.

---