import os
from typing import List, Dict, Any
from vector_db.chroma_store import VectorStore

# Initialize vector store - loads from knowledge/ directory
vector_store = VectorStore()


# def search_knowledge_base(query: str, top_k: int = 3) -> str:
#     """
#     Search a knowledge base for information relevant to the query.
#     Uses vector similarity search to find relevant documents.

#     Args:
#         query: The search query to find relevant information.
#         top_k: Number of top results to return (default: 3)

#     Returns:
#         Formatted search results with similarity scores
#     """
#     results = vector_store.search(query, top_k)
#     if not results:
#         return "No relevant information found."

#     formatted_results = []
#     for i, result in enumerate(results, 1):
#         formatted_results.append(
#             f"[Result {i}] (similarity: {result['score']:.4f}):\n{result['content']}"
#         )

#     return "\n\n".join(formatted_results)


def search_knowledge_base(query: str, top_k: int = 3) -> str:
    """
    Search a knowledge base for information relevant to the query.
    Uses vector similarity search to find relevant documents.

    Args:
        query: The search query to find relevant information.
        top_k: Number of top results to return (default: 3)

    Returns:
        Formatted search results with similarity scores
    """

    results = vector_store.search(query, top_k)

    if not results:
        return "No relevant information found."

    formatted_results = ["RAG Summary: Relevant knowledge base results for your query."]

    for i, result in enumerate(results[:top_k], 1):
        source = result["metadata"].get("source", "unknown")
        snippet = result["content"].strip().replace("\n", " ")[:400]
        formatted_results.append(
            f"Result {i} (source: {source}, score: {result['score']:.4f}):\n{snippet}"
        )

    formatted_results.append(
        "\nUse this summary to choose the best analysis or data tool and provide an answer grounded in the retrieved documentation."
    )

    return "\n\n".join(formatted_results)


def add_document_to_knowledge(content: str, metadata: Dict[str, Any] = None) -> str:
    """
    Add a new document to the knowledge base.

    Args:
        content: The document content to add
        metadata: Optional metadata (source, tags, etc.)

    Returns:
        Success message
    """
    vector_store.add_document(content, metadata)
    return "Document added to knowledge base successfully."


# Tool schema for LLM
# rag_tool_schema = {
#     "type": "function",
#     "function": {
#         "name": "search_knowledge_base",
#         "description": "Search a knowledge base for information relevant to the user's question. Use this when the user asks about programming concepts, AI, machine learning, or general knowledge questions.",
#         "parameters": {
#             "type": "object",
#             "properties": {
#                 "query": {
#                     "type": "string",
#                     "description": "The search query to find relevant information.",
#                 },
#                 "top_k": {
#                     "type": "integer",
#                     "description": "Number of top results to return (default: 3)",
#                     "default": 3
#                 }
#             },
#             "required": ["query"],
#         },
#     },
# }
rag_tool_schema = {
    "name": "search_knowledge_base",
    "description": "Search the knowledge base for relevant information and return the most relevant documents.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query to find relevant information.",
            },
            "top_k": {
                "type": "integer",
                "description": "Number of top results to return.",
                "default": 3,
            },
        },
        "required": ["query"],
    },
}
