// TEST USING kb_options params
window.config_default = {
  title: "Akvo RAG",
  kb_options: [
    {
      kb_id: 25,
      label: "UNEP Knowledge Base with 500 docs",
    },
    {
      kb_id: 26,
      label: "UNEP Knowledge Base with 250 docs",
    },
    {
      kb_id: 28,
      label: "Living Income Benchmark Knowledge Base",
    },
  ],
  wsURL: "wss://akvo-rag.akvotest.org/ws/chat",
};

// TEST USING ~ 500 docs
window.config_500 = {
  title: "UNEP Assistant",
  kb_id: 25,
  wsURL: "wss://akvo-rag.akvotest.org/ws/chat",
};

// TEST USING ~ 250 docs
window.config_250 = {
  title: "UNEP Assistant",
  kb_id: 26,
  wsURL: "wss://akvo-rag.akvotest.org/ws/chat",
};

// TEST USING ~ Living Income Bechmark docs
window.config_living_income = {
  title: "Living Income Assistant",
  kb_id: 28,
  wsURL: "wss://akvo-rag.akvotest.org/ws/chat",
};

window.config_local = {
  title: "UNEP Min",
  kb_id: 40,
  wsURL: "ws://localhost:81/ws/chat",
};
