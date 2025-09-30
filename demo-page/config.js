// TEST USING kb_options params
window.config_default = {
  title: "Akvo RAG",
  kb_options: [
    {
      kb_id: 34,
      label: "UNEP Knowledge Base",
    },
    {
      kb_id: 38,
      label: "Living Income Benchmark Knowledge Base",
    },
    {
      kb_id: 48,
      label: "Kefaas Knowledge Base",
    },
  ],
  wsURL: "wss://akvo-rag.akvotest.org/ws/chat",
};

// TEST USING ~ 500 docs
window.config_500 = {
  title: "UNEP Assistant",
  kb_id: 34,
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
  kb_id: 38,
  wsURL: "wss://akvo-rag.akvotest.org/ws/chat",
};

window.config_local = {
  title: "TDT #3",
  kb_id: 43,
  wsURL: "ws://localhost:81/ws/chat",
};

window.config_local_tdt4 = {
  title: "TDT #4",
  kb_id: 46,
  wsURL: "ws://localhost:81/ws/chat",
};

window.config_local_lib = {
  title: "LIB Assistant",
  kb_id: 44,
  wsURL: "ws://localhost:81/ws/chat",
};

window.config_living_income_1 = {
  title: "LIB #1",
  kb_id: 28,
  wsURL: "wss://akvo-rag.akvotest.org/ws/chat",
};

window.config_kefaas = {
  title: "Kefaas Knowledge Base",
  kb_id: 48,
  wsURL: "wss://akvo-rag.akvotest.org/ws/chat",
};
