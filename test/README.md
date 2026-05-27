# Orchestrator Agent - Project Structure

```
project/
├── main.py                 # Entry point - Orchestrator Agent
├── tools/                  # Tool functions
│   ├── __init__.py
│   ├── weather.py          # Weather API tool
│   └── rag.py              # RAG/Knowledge search tool
├── knowledge/              # Markdown documents (knowledge base)
│   ├── london.md
│   ├── weather.md
│   └── ai_agents.md
└── vector_db/              # Vector store for RAG
    └── chroma_store.py     # Simple vector database
```

---

## How It Works

### 1. **User Query → Orchestrator**
```
User: "What is the temperature in London?"
         ↓
   main.py → OrchestratorAgent.run()
```

### 2. **Orchestrator → LLM (with tools)**
The orchestrator sends the query + available tools to the LLM.

```python
# In main.py - OrchestratorAgent.run()
completion = client.chat.completions.create(
    model="Qwen/Qwen2.5-7B-Instruct",
    messages=messages,
    tools=[weather_tool_schema, rag_tool_schema],  # Tool schemas
)
```

### 3. **LLM Decides → Tool Call or Direct Answer**
The LLM analyzes the query:
- **If needs external data** → calls a tool (e.g., `get_temperature`)
- **If needs knowledge** → calls `search_knowledge_base`
- **If can answer directly** → returns the answer

### 4. **Tool Execution**
If a tool is called:
```
LLM decides: "I need to call get_temperature with city='London'"
         ↓
Orchestrator executes: get_temperature(city="London")
         ↓
Result: "22°C"
         ↓
Result sent back to LLM for final response
```

### 5. **Final Response**
The LLM combines the tool result with its own knowledge to answer.

---

## Component Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      USER QUERY                             │
│            "What's the weather in London?"                  │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ↓
┌──────────────────────────────────────────────────────────────┐
│                 ORCHESTRATOR AGENT (main.py)                 │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  1. Append user message to messages                     │ │
│  │  2. Call LLM with messages + tool schemas              │ │
│  │  3. Check if LLM requests tool call                     │ │
│  │  4. If yes → execute tool → append result → loop       │ │
│  │  5. If no → return final response                     │ │
│  └─────────────────────────────────────────────────────────┘ │
└──────────────────────────┬──────────────────────────────────┘
                           │
           ┌───────────────┴───────────────┐
           │                               │
           ↓                               ↓
┌─────────────────────┐        ┌─────────────────────────────┐
│   LLM DECISION     │        │       LLM DECISION         │
│                     │        │                             │
│  "I need weather"  │        │  "I need knowledge"         │
│         ↓          │        │         ↓                   │
│  Tool: get_temp   │        │  Tool: search_knowledge     │
└────────┬───────────┘        └──────────┬──────────────────┘
         │                               │
         ↓                               ↓
┌─────────────────────┐        ┌─────────────────────────────┐
│  TOOLS/weather.py   │        │  TOOLS/rag.py               │
│                     │        │                               │
│  - Calls Open-Meteo│        │  - Calls VectorStore          │
│  - Returns temp    │        │  - Searches knowledge/        │
└────────┬───────────┘        └──────────┬──────────────────┘
         │                               │
         └───────────────┬───────────────┘
                         │
                         ↓
              ┌─────────────────────────┐
              │    TOOL RESULT SENT     │
              │    BACK TO LLM          │
              └────────────┬────────────┘
                           │
                           ↓
              ┌─────────────────────────┐
              │    FINAL RESPONSE       │
              │    "The temperature    │
              │    in London is 22°C"   │
              └─────────────────────────┘
```

---

## File Details

### `main.py` - Orchestrator
- **OrchestratorAgent**: Main class that handles the loop
  - `run()`: Process user query through LLM + tools
  - `execute_tool()`: Run the actual tool function
  - `register_tool()`: Add tool schemas

- **Router**: (Optional) Decides which tool to use

### `tools/weather.py`
- `get_temperature(city)`: Calls Open-Meteo API
- Returns temperature in Celsius

### `tools/rag.py`
- `search_knowledge_base(query)`: Searches vector store
- Calls `vector_db/chroma_store.py` for similarity search

### `knowledge/*.md`
- Markdown files containing information
- Auto-loaded by VectorStore on startup
- Add more .md files here to expand knowledge
- Example: `knowledge/online_apparel_tv_cc_drop_playbook.md` for `online_apparel` tv/cc drop investigations
- Example: `knowledge/online_mobile_cc_users_playbook.md` for `online_mobile` cc_users drop investigations

### `vector_db/chroma_store.py`
- **VectorStore class**:
  - `_load_knowledge_base()`: Loads all .md files
  - `search(query)`: Returns top-k similar documents
  - Uses simple hash-based embeddings (replace with sentence-transformers for production)

---

## How to Add More Tools

1. Create a new file in `tools/`, e.g., `tools/calculator.py`
2. Define your function and tool schema:
```python
def add(a: int, b: int) -> int:
    return a + b

add_tool_schema = {
    "type": "function",
    "function": {
        "name": "add",
        "description": "Add two numbers",
        "parameters": {
            "type": "object",
            "properties": {
                "a": {"type": "number"},
                "b": {"type": "number"}
            },
            "required": ["a", "b"]
        }
    }
}
```
3. Import and register in `main.py`:
```python
from tools.calculator import add, add_tool_schema
agent.register_tool(add_tool_schema)
```

---

## How to Add More Knowledge

1. Create a new `.md` file in `knowledge/`, e.g., `knowledge/python.md`
2. Add content to the file
3. The VectorStore will automatically load it on next run

---

## Running the Project

```bash
python main.py
```

The agent will:
1. Load knowledge from `knowledge/` directory
2. Start the orchestrator
3. Process test queries using available tools