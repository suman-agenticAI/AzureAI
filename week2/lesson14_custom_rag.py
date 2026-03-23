"""
Lesson 14: Custom RAG Pipeline (End-to-End)
=============================================
Full pipeline: User question → Embed → Hybrid search + rerank → GPT-4o generates answer

Uses the product-catalog index from Lesson 12.
"""

import os
import sys
import asyncio
from dotenv import load_dotenv
from openai import AsyncAzureOpenAI
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery, QueryType, QueryCaptionType
from azure.core.credentials import AzureKeyCredential

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()


async def embed_query(openai_client, query):
    """Step 1: Convert user query to vector."""
    response = await openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=[query],
    )
    return response.data[0].embedding


def search_index(search_client, query, query_vector, top=3, filter_expr=None):
    """Step 2: Hybrid search + semantic rerank."""
    results = search_client.search(
        search_text=query,
        vector_queries=[
            VectorizedQuery(
                vector=query_vector,
                k_nearest_neighbors=top,
                fields="description_vector",
            )
        ],
        query_type=QueryType.SEMANTIC,
        semantic_configuration_name="product-semantic-config",
        query_caption=QueryCaptionType.EXTRACTIVE,
        filter=filter_expr,
        top=top,
    )
    return results


def format_context(results):
    """Step 3: Format search results as context for GPT-4o."""
    context_parts = []
    for r in results:
        part = f"Product: {r['name']}\n"
        part += f"Category: {r['category']}\n"
        part += f"Price: Rs.{r['price']}\n"
        part += f"Description: {r['description']}\n"
        captions = r.get("@search.captions", [])
        if captions:
            part += f"Relevant excerpt: {captions[0].text}\n"
        context_parts.append(part)
    return "\n---\n".join(context_parts)


async def generate_answer(openai_client, query, context):
    """Step 4: GPT-4o generates answer grounded in search results."""
    response = await openai_client.chat.completions.create(
        model="gpt-4o",
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": """You are a product advisor for TechCorp Electronics.
                Answer the customer's question using ONLY the product information provided.
                Rules:
                - Only recommend products from the context
                - Include price in INR
                - If the context doesn't have a good match, say so
                - Be concise — 3-4 sentences max""",
            },
            {
                "role": "user",
                "content": f"Product catalog:\n{context}\n\nCustomer question: {query}",
            },
        ],
    )
    return response.choices[0].message.content, response.usage


async def main():
    base_endpoint = os.getenv("PROJECT_ENDPOINT").split("/api/")[0]
    openai_client = AsyncAzureOpenAI(
        azure_endpoint=base_endpoint,
        api_key=os.getenv("AZURE_API_KEY"),
        api_version="2024-06-01",
    )

    search_client = SearchClient(
        endpoint=os.getenv("SEARCH_ENDPOINT"),
        index_name="product-catalog",
        credential=AzureKeyCredential(os.getenv("SEARCH_ADMIN_KEY")),
    )

    print("=== TechCorp Product Advisor (RAG) ===")
    print("Type 'quit' to exit\n")

    while True:
        query = input("You: ")
        if query.lower() == "quit":
            break

        # Step 1: Embed
        query_vector = await embed_query(openai_client, query)

        # Step 2: Search (hybrid + semantic rerank)
        results = search_index(search_client, query, query_vector)

        # Step 3: Format context
        context = format_context(results)

        # Step 4: Generate answer
        answer, usage = await generate_answer(openai_client, query, context)

        print(f"\nAdvisor: {answer}")
        print(f"  [Tokens: prompt={usage.prompt_tokens}, completion={usage.completion_tokens}]\n")

    await openai_client.close()


if __name__ == "__main__":
    asyncio.run(main())
