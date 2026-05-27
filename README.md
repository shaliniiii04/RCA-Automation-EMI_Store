# Orchestrator Agent - Multi-Tool System with RAG

A production-grade orchestrator agent that coordinates between user queries, multiple specialized tools, a knowledge base (RAG), and a language model. Intelligent routing ensures the right tool is selected for each query type.

```
project/
├── main.py                           # Entry point - Orchestrator Agent
├── tools/                            # Specialized tool implementations
│   ├── __init__.py
│   ├── weather.py                    # Weather API integration
│   ├── rag.py                        # Knowledge base retrieval (RAG)
│   ├── sql_generator.py              # ClickHouse query execution & analysis
│   └── clickhouse_examples.py
├── knowledge/                        # Markdown knowledge base
│   ├── ai_agents.md
│   ├── data_fetching_guide.md
│   ├── weather.md
│   ├── online_mobile_cc_users_playbook.md
│   └── (more playbooks...)
├── vector_db/                        # Vector store for RAG
│   ├── __init__.py
│   └── chroma_store.py               # Chroma vector store wrapper
├── scripts/                          # Utility scripts
└── README.md
```

---

## System Overview

### Available Tools

1. **get_temperature** - Real-time weather data from Open-Meteo API
2. **search_knowledge_base** - RAG search across markdown knowledge base
3. **fetch_data_from_clickhouse** - Execute SQL queries against ClickHouse
4. **analyze_cc_users_drop** - Playbook-driven analysis for cc_users drop investigations

### Execution Flow

```
┌─────────────────┐
│   User Query    │
└────────┬────────┘
         │
         ↓
┌─────────────────────────────────────┐
│   ROUTER (Intelligent Selection)    │
│ • Weather keywords → get_temperature│
│ • Analysis keywords → search_knowledge_base (RAG)
│ • SQL/fetch keywords → fetch_data_from_clickhouse
│ • cc_users keywords → analyze_cc_users_drop
└────────┬────────────────────────────┘
         │
         ↓
┌─────────────────────────────────────────────────┐
│ ORCHESTRATOR AGENT (OrchestratorAgent.run())   │
│ • Append user message                           │
│ • Pass selected tool to LLM with tool_choice   │
│ • Handle tool calls in loop                     │
│ • Collect results and compose final response    │
└────────┬────────────────────────────────────────┘
         │
         ↓
┌─────────────────────────────────────────────────┐
│    TOOL EXECUTION LAYER                         │
│  ┌────────────────────────────────────────────┐ │
│  │ Tool Execution: weather, RAG, SQL, etc.   │ │
│  │ Returns: structured JSON or text result   │ │
│  └────────────────────────────────────────────┘ │
└────────┬────────────────────────────────────────┘
         │
         ↓
┌──────────────────────────┐
│   FINAL RESPONSE         │
│ (LLM + tool results)     │
└──────────────────────────┘
```

---

## Key Components

### main.py - OrchestratorAgent
- **OrchestratorAgent** class:
  - `run(user_query)`: Main entry point for processing queries
  - `register_tool(tool_schema)`: Register tool schemas
  - `get_tool_name(tool_schema)`: Extract tool name (handles both root and function-wrapped schemas)
  - `get_tool_schema_by_name(tool_name)`: Look up tool schema by name
  - `execute_tool(function_name, args)`: Execute registered tool function

- **Router** class:
  - `should_use_tool(query, available_tools)`: Intelligent tool selection
  - Routes based on keyword matching:
    - **temperature/weather** → `get_temperature`
    - **cc_users** (non-SQL) → `analyze_cc_users_drop`
    - **analyze/investigate/drop/trend/summary** → `search_knowledge_base` (RAG)
    - **select/query/fetch/sql** → `fetch_data_from_clickhouse`

### tools/weather.py
- `get_temperature(city)`: Query Open-Meteo API for current weather
- Returns: temperature in Celsius or error message
- Handles: geocoding + weather lookup

### tools/rag.py
- `search_knowledge_base(query, top_k=3)`: Vector similarity search
- Returns: formatted summary with source and relevance scores
- Integration: Calls `VectorStore` from `vector_db/chroma_store.py`
- Output: RAG summary + guidance to choose analysis tool

### tools/sql_generator.py
- `fetch_data_from_clickhouse(sql_query)`: Execute ClickHouse queries
  - Handles: connection pooling, date serialization, error handling
  - Returns: JSON with data rows and count
  
- `analyze_cc_users_drop(...)`: Playbook-driven analysis
  - Compares: current date vs. previous month same date
  - Triggers investigation: if drop > 5% threshold
  - Returns: structured analysis with raw data and segment summaries

### vector_db/chroma_store.py
- **VectorStore** class:
  - `_load_knowledge_base()`: Auto-loads all `.md` files from `knowledge/` on init
  - `search(query, top_k)`: Vector similarity search using hash-based embeddings
  - `add_document(content, metadata)`: Add new documents dynamically
  - `_create_embedding()`: Hash-based embeddings (production: use sentence-transformers)
  - `_cosine_similarity()`: Compute similarity between vectors

### knowledge/*.md
- Markdown documents for knowledge base
- Auto-loaded and indexed on startup
- Examples:
  - `online_mobile_cc_users_playbook.md` → for cc_users drop analysis
  - `data_fetching_guide.md` → for data query guidance
  - Add more playbooks for domain-specific analysis

---

## Router Logic (Intelligent Tool Selection)

The router prioritizes tools intelligently:

```python
1. Weather keywords (temperature, weather) → get_temperature
2. cc_users analysis (cc_users without SQL keywords) → analyze_cc_users_drop
3. Analysis keywords (analyze, investigate, drop, trend, etc.) → search_knowledge_base
4. SQL keywords (select, query, fetch, sql) → fetch_data_from_clickhouse
5. No match → send all tools to LLM for auto selection
```

This ensures:
- Weather queries run immediately without unnecessary RAG search
- cc_users analysis uses the playbook tool instead of raw SQL
- Investigation queries benefit from knowledge base context first
- Raw SQL queries bypass RAG and go directly to ClickHouse

---

## How to Add More Tools

### 1. Create tool function
```python
# tools/my_tool.py
def my_function(param: str) -> str:
    """Do something useful"""
    return f"Result for {param}"

my_tool_schema = {
    "name": "my_function",
    "description": "Description of what this tool does",
    "parameters": {
        "type": "object",
        "properties": {
            "param": {
                "type": "string",
                "description": "Parameter description"
            }
        },
        "required": ["param"]
    }
}
```

### 2. Register in main.py
```python
from tools.my_tool import my_function, my_tool_schema

# In main.py __main__ block
agent.register_tool(my_tool_schema)
```

### 3. (Optional) Update Router
```python
# In Router.should_use_tool()
if "my_keyword" in query_lower:
    return "my_function"
```

---

## How to Expand Knowledge Base

### 1. Create new markdown file
```bash
# knowledge/new_playbook.md
```

### 2. Add content
```markdown
# Playbook Name

## Process Steps
1. Step one
2. Step two

## Queries

### Diagnostic Query
SELECT ...

### Investigation Query
SELECT ...
```

### 3. Automatic loading
- VectorStore automatically loads all `.md` files on startup
- No code changes needed

---

## System Prompt & LLM Behavior

The orchestrator uses this system prompt:

> "You are a helpful assistant that can use tools and a knowledge base to answer questions. For analysis or investigation queries, first retrieve relevant documentation using the search_knowledge_base tool. Return a short formatted summary of the relevant knowledge, then use that summary to select the best analysis or data tool for the user. If the user asks for a report, include a clear summary before proceeding with analysis."

This guides the LLM to:
1. Use RAG for context on analysis queries
2. Provide formatted summaries
3. Choose the right tool based on retrieved knowledge
4. Generate structured reports

---

## Running the Project

### Basic execution
```bash
uv run main.py
```

### What happens
1. Loads 4 knowledge documents from `knowledge/`
2. Initializes orchestrator with all tools
3. Processes 3 test queries:
   - Weather query → `get_temperature`
   - Data fetch query → `fetch_data_from_clickhouse`
   - Analysis query → `analyze_cc_users_drop`
4. Returns formatted responses

### Example run
```
Query: What is the temperature in mumbai now?
→ Calling tool: get_temperature({'city': 'mumbai'})
→ Tool result: 34.4°C...
Response: The current temperature in Mumbai is 34.4°C.

Query: Fetch daily cc_users for online_mobile on 14 May 2026...
→ Calling tool: analyze_cc_users_drop(...)
→ Tool result: comparison + investigation data...
Response: [Formatted analysis report]
```

---

## Configuration

### Environment Variables (.env)
```
CLICKHOUSE_HOST=172.31.54.184
PORT=9000
USER=default
PASSWORD=<password>
DATABASE=snapmint_analytics

HF_API_TOKEN=<huggingface_token>
HF_MODEL=Qwen/Qwen2.5-7B-Instruct
```

### Model Selection
- Default: `Qwen/Qwen2.5-7B-Instruct` (Hugging Face)
- Must support:
  - Tool calling (function calling)
  - System prompts
  - Multi-message conversations

---

## Error Handling

The orchestrator handles:
- ✅ Missing databases → graceful error + guidance
- ✅ Invalid SQL queries → returns error message
- ✅ Weather API failures → falls back to error message
- ✅ Tool schema format variations → normalizes both root and function-wrapped schemas
- ✅ Model rate limits → error propagation

---

## Architecture Decisions

### 1. Intelligent Routing
- Router prefilters queries before LLM
- Avoids unnecessary tool exploration
- Faster, more predictable responses

### 2. RAG-First for Analysis
- Knowledge base consulted before raw data queries
- Ensures playbook compliance
- Structured decision-making

### 3. Tool Schema Flexibility
- Supports both old (`{"name": ...}`) and new (`{"type": "function", "function": {...}}`) schemas
- Handles mixed tool schemas
- Backward compatible

### 4. Playbook-Driven Analysis
- `analyze_cc_users_drop` encodes domain logic
- Triggered on cc_users queries
- Returns structured investigation results

---

## Future Enhancements

- [ ] Replace hash-based embeddings with sentence-transformers
- [ ] Add tool execution history & logging
- [ ] Implement tool result caching
- [ ] Support for streaming responses
- [ ] Multi-turn conversation memory
- [ ] Dynamic tool registration via API
- [ ] Advanced error recovery with tool fallbacks

---

## Testing

Run the project to test all tools:
```bash
uv run main.py
```

Expected outputs:
- Weather query returns temperature
- SQL query either returns data or ClickHouse connection error
- Analysis query returns investigation report (if db available) or guidance
