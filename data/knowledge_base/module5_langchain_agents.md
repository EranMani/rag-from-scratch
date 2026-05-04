# Module 5: Building Autonomous Agents with LangChain

## LLM vs Agent
- **LLM**: Stateless function — input text → output text. No memory, no tools.
- **Agent**: Has autonomy, memory, and access to tools. Can decide what to do next based on context.

## Key LangChain Components

### Prompt Templates
Reusable prompt structures with variable slots:
```python
template = PromptTemplate(
    input_variables=["context", "question"],
    template="Use the context below to answer.\nContext: {context}\nQuestion: {question}"
)
```

### LCEL (LangChain Expression Language)
A pipe syntax for chaining components:
```python
chain = prompt | llm | StrOutputParser()
result = chain.invoke({"context": "...", "question": "..."})
```
Components: `RunnablePassthrough`, `RunnableParallel`, `RunnableLambda`

### Memory Modules
- **ConversationBufferMemory**: Stores all past messages in memory. Simple but grows unbounded.
- **ConversationSummaryMemory**: Summarizes old messages to save tokens.
- **Persistent Profiles**: Save conversation to JSON so users are recognized across sessions.

### Vendor Independence
Switch from OpenAI to Anthropic or Ollama with one line:
```python
# OpenAI
llm = ChatOpenAI(model="gpt-4o")
# Ollama (local)
llm = ChatOllama(model="gemma3:4b")
# Both implement the same BaseChatModel interface
```

## Tools in Agents
Agents can call tools — functions the LLM can choose to invoke:
- `similarity_search` — query the vector database
- `get_chat_history` — retrieve past conversation
- `get_user_profile` — load persistent user data
