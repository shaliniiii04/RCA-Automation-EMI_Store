"""
Orchestrator Agent - Main Entry Point

This is the main orchestrator that coordinates:
1. Tools (weather, RAG, etc.)
2. Knowledge base (vector store)
3. LLM (language model)

Flow:
User Query -> Orchestrator -> Router -> Tool/Knowledge -> LLM -> Response
"""

import os
import json
from typing import Dict, Any, List, Optional

from huggingface_hub import InferenceClient
from huggingface_hub.errors import HfHubHTTPError
from dotenv import load_dotenv

# Import tools
from tools.weather import get_temperature, weather_tool_schema
from tools.rag import search_knowledge_base, rag_tool_schema
from tools.sql_generator import (
    fetch_data_from_clickhouse,
    analyze_cc_users_drop,
    sql_generator_tool_schema,
    analyze_cc_users_drop_tool_schema,
)

# Disable SSL warnings (for corporate proxies)
os.environ["HF_HUB_DISABLE_SSL_VERIFICATION"] = "1"
os.environ["HF_HUB_DISABLE_HTTP2"] = "1"

load_dotenv()
DEFAULT_MODEL = os.getenv("HF_MODEL", "Qwen/Qwen2.5-7B-Instruct")
client = InferenceClient(api_key=os.getenv("HF_API_TOKEN"))


# ============================================================================
# ORCHESTRATOR AGENT
# ============================================================================


class OrchestratorAgent:
    """
    The Orchestrator Agent coordinates between:
    - User queries
    - Available tools
    - Knowledge base (RAG)
    - Language Model
    """

    def __init__(
        self,
        client: InferenceClient,  ## for connecting HF token and load model
        model: Optional[str] = None,
        system_prompt: str = "",
    ):
        self.client = client
        self.model = model or DEFAULT_MODEL
        self.messages: List[Dict[str, Any]] = []
        self.tools = []  # Will be populated by register_tool()

        if system_prompt:
            self.messages.append({"role": "system", "content": system_prompt})

    def register_tool(self, tool_schema: Dict[str, Any]):  ## tools loading
        """Register a tool schema for the agent to use"""
        self.tools.append(tool_schema)

    def get_tool_name(self, tool_schema: Dict[str, Any]) -> Optional[str]:
        """Return the tool name from a schema with either root or function structure."""
        if isinstance(tool_schema, dict):
            if "function" in tool_schema and isinstance(tool_schema["function"], dict):
                return tool_schema["function"].get("name")
            return tool_schema.get("name")
        return None

    def get_tool_schema_by_name(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Return the registered tool schema by its name."""
        for tool in self.tools:
            if self.get_tool_name(tool) == tool_name:
                return tool
        return None

    def execute_tool(self, function_name: str, function_args: Dict[str, Any]) -> str:
        """
        Execute a tool function by name.
        Tools are looked up in globals() - in production, use a registry.
        """
        tool_output_content = f"Tool '{function_name}' not found."  ## suggestion by llm
        if function_name in globals() and callable(
            globals()[function_name]
        ):  ## check if function exists and is callable
            function_to_call = globals()[function_name]
            executed_output = function_to_call(**function_args)
            if isinstance(executed_output, (dict, list)):
                tool_output_content = json.dumps(executed_output)
            else:
                tool_output_content = str(executed_output)
        return tool_output_content

    def run(self, user_query: str) -> str:
        """
        Main entry point - process a user query through the orchestrator.
        """
        # Reset messages for new conversation
        self.messages = [
            {
                "role": "system",
                "content": (
                    "You are a helpful assistant that can use tools and a knowledge base to answer questions. "
                    "For analysis or investigation queries, first retrieve relevant documentation using the "
                    "search_knowledge_base tool. Return a short formatted summary of the relevant knowledge, "
                    "then use that summary to select the best analysis or data tool for the user. "
                    "If the user asks for a report, include a clear summary before proceeding with analysis."
                ),
            }
        ]

        self.messages.append({"role": "user", "content": user_query})

        # Decide whether this query should use a tool
        tool_choice = "auto"
        available_tool_names = [
            self.get_tool_name(tool) for tool in self.tools if self.get_tool_name(tool)
        ]
        selected_tool = Router.should_use_tool(user_query, available_tool_names)
        if selected_tool:
            tool_choice = "required"
            tools_to_pass = [self.get_tool_schema_by_name(selected_tool)]
        else:
            tools_to_pass = self.tools

        # Route through tool calling loop
        max_rounds = 5
        round_count = 0
        while round_count < max_rounds:
            round_count += 1
            try:
                completion = self.client.chat.completions.create(
                    model=self.model,
                    messages=self.messages,
                    tools=tools_to_pass,
                    tool_choice=tool_choice,
                )
            except HfHubHTTPError as exc:
                response = getattr(exc, "response", None)
                status_code = getattr(response, "status_code", None)
                if status_code == 402:
                    raise RuntimeError(
                        "Hugging Face request failed because your account has exhausted its available credits. "
                        "Purchase pre-paid credits or use a different provider/model."
                    ) from exc
                raise RuntimeError(
                    f"Failed to create a chat completion with model '{self.model}'. "
                    "Please confirm that this model is supported by your Hugging Face provider "
                    "and/or set HF_MODEL in your .env file."
                ) from exc
            except Exception as exc:
                raise RuntimeError(
                    f"Failed to create a chat completion with model '{self.model}'. "
                    "Please confirm that this model is supported by your Hugging Face provider "
                    "and/or set HF_MODEL in your .env file."
                ) from exc

            response_message = completion.choices[0].message
            # response_message=completion.choices

            # If tool is called, execute and continue
            if response_message.tool_calls:
                self.messages.append(response_message)

                tool_outputs = []
                for tool_call in response_message.tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)

                    print(f"  → Calling tool: {function_name}({function_args})")

                    output = self.execute_tool(function_name, function_args)
                    print(f"  → Tool result: {output[:100]}...")

                    tool_outputs.append(
                        {
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": function_name,
                            "content": output,
                        }
                    )

                self.messages.extend(tool_outputs)
                tool_choice = "auto"
                continue

            response_content = getattr(response_message, "content", None)
            if not response_content and hasattr(response_message, "additional_kwargs"):
                response_content = response_message.additional_kwargs.get("content")

            if not response_content:
                return (
                    "No response was returned by the model. "
                    "Check the chosen model and your Hugging Face provider settings."
                )

            return response_content

        raise RuntimeError(
            "Exceeded the maximum number of tool-call rounds. "
            "This may indicate the model keeps requesting the same tool."
        )


# ============================================================================
# ROUTER - Decides which tool/knowledge to use
# ============================================================================


class Router:  ## for this rag will be used
    """
    The Router decides whether to:
    - Use a tool (weather, calculator, etc.)
    - Search the knowledge base (RAG)
    - Answer directly without external calls
    """

    @staticmethod
    def should_use_tool(query: str, available_tools: List[str]) -> Optional[str]:
        """Decide if a tool should be used based on the query"""
        query_lower = query.lower()

        # Simple keyword-based routing
        if "temperature" in query_lower or "weather" in query_lower:
            return "get_temperature"
        if "cc_users" in query_lower and "same date" in query_lower:
            return "analyze_cc_users_drop"
        if "cc_users" in query_lower and "previous month" in query_lower:
            return "analyze_cc_users_drop"
        if (
            "cc_users" in query_lower
            and "select" not in query_lower
            and "sql" not in query_lower
        ):
            return "analyze_cc_users_drop"
        if any(
            keyword in query_lower
            for keyword in [
                "analyze",
                "analysis",
                "investigate",
                "investigation",
                "drop",
                "trend",
                "compare",
                "summary",
                "why",
                "playbook",
                "knowledge",
                "document",
                "process",
                "explain",
                "define",
                "guidance",
            ]
        ):
            return "search_knowledge_base"
        if any(
            keyword in query_lower
            for keyword in [
                "select",
                "query",
                "fetch",
                "data",
                "table",
                "database",
                "sql",
            ]
        ):
            return "fetch_data_from_clickhouse"

        return None


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    # Create orchestrator agent
    agent = OrchestratorAgent(client=client)

    # Register available tools
    agent.register_tool(weather_tool_schema)
    # agent.register_tool(rag_tool_schema)
    agent.register_tool(sql_generator_tool_schema)
    agent.register_tool(analyze_cc_users_drop_tool_schema)

    print("=" * 60)
    print("ORCHESTRATOR AGENT - Multi-Tool System")
    print("=" * 60)
    print("\nAvailable tools:")
    print("  1. get_temperature - Get weather for a city")
    print("  2. search_knowledge_base - Search knowledge base")
    print("  3. fetch_data_from_clickhouse - Query ClickHouse database")
    print(
        "  4. analyze_cc_users_drop - Analyze online_mobile cc_users drop using playbook workflow"
    )
    print("\n" + "=" * 60 + "\n")

    # Test queries
    queries = [
        "What is the temperature in mumbai now?",
        "Fetch created_at, id, and user_id from loan_applications_silver with user_id 58905225 and also merchant_id",
        "Fetch daily cc_users for online_mobile on 14 May 2026 of new users-is_repeat=0 and investigate the drop relative to previous month same day",
    ]

    for query in queries:
        print(f" Query: {query}")
        print("-" * 40)
        response = agent.run(query)
        print(f" Response: {response}\n")
