// TEST USING kb_options params
window.config_default = {
  title: "Akvo RAG",
  kb_options: [
    {
      kb_id: 6,
      label: "UNEP Knowledge Base",
    },
    {
      kb_id: 5,
      label: "Kenya Drylands Knowledge Base",
    },
    {
      kb_id: 7,
      label: "Kefaas Knowledge Base",
    },
  ],
  wsURL: "wss://akvo-rag.akvotest.org/ws/chat",
};

// TEST USING ~ 500 docs
window.config_unep = {
  title: "UNEP Knowledge Base",
  kb_id: 6,
  wsURL: "wss://akvo-rag.akvotest.org/ws/chat",
};

// TEST USING ~ Living Income Bechmark docs
// window.config_living_income = {
//   title: "Living Income Assistant",
//   kb_id: 38,
//   wsURL: "wss://akvo-rag.akvotest.org/ws/chat",
// };

// TEST USING Kefaas docs
window.config_kefaas = {
  title: "Kefaas Knowledge Base",
  kb_id: 7,
  wsURL: "wss://akvo-rag.akvotest.org/ws/chat",
};

// LOCAL
window.config_local = {
  title: "Test Integration with MCP server",
  kb_id: 8,
  wsURL: "ws://localhost:81/ws/chat",
};
