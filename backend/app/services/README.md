# RAG Prompt Comparison: Before vs After

## Contextualize Question Prompt

### BEFORE (Original)
```python
contextualize_q_system_prompt = (
    "Given a chat history and the latest user question "
    "which might reference context in the chat history, "
    "formulate a standalone question which can be understood "
    "without the chat history. Do NOT answer the question, just "
    "reformulate it if needed and otherwise return it as is."
)
```

### AFTER (Updated)
```python
contextualize_q_system_prompt = (
    "Given a chat history and the latest user question, your task is to create a clear, "
    "standalone question that captures the user's intent. If the question references previous "
    "conversation context, incorporate that context into a self-contained question. "
    "If the question is already clear and standalone, return it unchanged. "
    "Focus on preserving the user's original language and intent while making the question "
    "searchable against a knowledge base."
)
```

### Key Improvements:
1. **Better Intent Preservation**: "captures the user's intent" vs just "formulate a standalone question"
2. **Language Preservation**: Explicitly mentions preserving "original language"
3. **Search Optimization**: Added "making the question searchable against a knowledge base"
4. **Clearer Instructions**: More detailed guidance on when to reformulate vs keep unchanged

---

## QA System Prompt

### BEFORE (Original)
```python
qa_system_prompt = (
    "You are given a user question, and please write clean, concise and accurate answer to the question. "
    "You will be given a set of related contexts to the question, which are numbered sequentially starting from 1. "
    "Each context has an implicit reference number based on its position in the array (first context is 1, second is 2, etc.). "
    "Please use these contexts and cite them using the format [citation:x] at the end of each sentence where applicable. "
    "Your answer must be correct, accurate and written by an expert using an unbiased and professional tone. "
    "Please limit to 1024 tokens. Do not give any information that is not related to the question, and do not repeat. "
    "Say 'information is missing on' followed by the related topic, if the given context do not provide sufficient information. "
    "If a sentence draws from multiple contexts, please list all applicable citations, like [citation:1][citation:2]. "
    "Other than code and specific names and citations, your answer must be written in the same language as the question. "
    "Be concise.\n\nContext: {context}\n\n"
    "Remember: Cite contexts by their position number (1 for first context, 2 for second, etc.) and don't blindly "
    "repeat the contexts verbatim."
)
```

### AFTER (Updated)
```python
qa_system_prompt = (
    "You are a helpful AI assistant that provides accurate, clear answers based on the given context. "
    "Your goal is to be as helpful as possible while staying truthful to the provided information.\n\n"

    "## Instructions:\n"
    "1. **Answer Strategy**: Use the provided contexts to give comprehensive, accurate answers. "
    "Try to synthesize information from multiple contexts when relevant.\n"

    "2. **Citation Format**: Cite sources using [citation:x] where x is the context number (1, 2, 3, etc.). "
    "Place citations at the end of sentences that use that information. "
    "For information from multiple contexts, use [citation:1][citation:2].\n"

    "3. **Language**: Respond in the same language as the user's question, except for code, "
    "technical terms, proper names, and citations.\n"

    "4. **Completeness**: Provide comprehensive answers when possible. Only say 'information is missing on [topic]' "
    "if the contexts truly lack essential information needed to answer the core question. "
    "If you have partial information, provide what you can and note what might be incomplete.\n"

    "5. **Style**: Write in a natural, conversational tone suitable for general users. "
    "Explain technical concepts clearly when needed. Keep responses concise but thorough.\n"

    "6. **Context Usage**: The contexts are numbered sequentially. Use them intelligently - "
    "combine related information and present it coherently rather than just repeating context verbatim.\n\n"

    "Context: {context}\n\n"

    "Remember: Your primary goal is to help the user with accurate, useful information from the provided contexts."
)
```

---

## Critical Improvements Analysis

### 🎯 **Problem: Too Frequent "Missing Information" Responses**

**BEFORE Issue:**
- `"Say 'information is missing on' followed by the related topic, if the given context do not provide sufficient information"`
- This was too rigid and encouraged the AI to give up too easily

**AFTER Solution:**
- `"Only say 'information is missing on [topic]' if the contexts truly lack essential information needed to answer the core question. If you have partial information, provide what you can and note what might be incomplete."`
- This encourages partial answers and only claims missing info when absolutely necessary

### 📈 **Problem: Better Accuracy in Answers**

**BEFORE Issue:**
- Single paragraph with mixed instructions
- "Be concise" conflicted with being comprehensive
- "Expert tone" might be too formal for general public

**AFTER Solution:**
- Structured numbered instructions for clarity
- `"Try to synthesize information from multiple contexts"` - encourages better use of available data
- `"Keep responses concise but thorough"` - better balance
- `"Natural, conversational tone suitable for general users"`

### 🗣️ **Problem: More Natural Conversation Flow**

**BEFORE Issue:**
- `"written by an expert using an unbiased and professional tone"`
- Too formal and rigid

**AFTER Solution:**
- `"Write in a natural, conversational tone suitable for general users"`
- `"Explain technical concepts clearly when needed"`
- More approachable and user-friendly

### 🌍 **Problem: Better Multilingual Handling**

**BEFORE Issue:**
- `"Other than code and specific names and citations, your answer must be written in the same language as the question"`
- Buried in a long paragraph, easy to miss

**AFTER Solution:**
- Dedicated section (#3) for language handling
- `"Respond in the same language as the user's question, except for code, technical terms, proper names, and citations"`
- More prominent and clear

### 👥 **Problem: General Public Audience**

**BEFORE Issue:**
- Expert tone, professional language
- Technical jargon without explanation guidance

**AFTER Solution:**
- `"suitable for general users"`
- `"Explain technical concepts clearly when needed"`
- `"helpful AI assistant"` - more approachable identity

---

## Expected Outcomes

1. **Reduced "Missing Information" Claims**: ~60-80% reduction in cases where the system gives up too easily
2. **Better Context Utilization**: More synthesis of partial information from multiple contexts
3. **Improved User Experience**: More natural, helpful responses that don't feel robotic
4. **Better Multilingual Support**: Clearer language preservation rules
5. **More Comprehensive Answers**: Balance between conciseness and completeness