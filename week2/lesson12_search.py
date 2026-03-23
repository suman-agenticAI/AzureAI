"""
Lesson 12 - Part 2: Search the Index
======================================
Demonstrates 3 search types: keyword, vector, hybrid.
"""

import os
import sys
import asyncio
from dotenv import load_dotenv
from openai import AsyncAzureOpenAI
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from azure.core.credentials import AzureKeyCredential

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()


async def get_query_vector(openai_client, query):
    """Embed the search query."""
    response = await openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=[query],
    )
    return response.data[0].embedding


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

    query = input("Search: ")

    # --- 1. Keyword Search (BM25) ---
    print("\n=== KEYWORD SEARCH ===")
    results = search_client.search(search_text=query, top=3)
    for r in results:
        print(f"  {r['name']} | {r['category']} | Rs.{r['price']} | Score: {r['@search.score']:.4f}")

    # --- 2. Vector Search ---
    print("\n=== VECTOR SEARCH ===")
    query_vector = await get_query_vector(openai_client, query)
    results = search_client.search(
        search_text=None,
        vector_queries=[
            VectorizedQuery(
                vector=query_vector,
                k_nearest_neighbors=3,
                fields="description_vector",
            )
        ],
    )
    for r in results:
        print(f"  {r['name']} | {r['category']} | Rs.{r['price']} | Score: {r['@search.score']:.4f}")

    # --- 3. Hybrid Search (keyword + vector) ---
    print("\n=== HYBRID SEARCH ===")
    results = search_client.search(
        search_text=query,
        vector_queries=[
            VectorizedQuery(
                vector=query_vector,
                k_nearest_neighbors=3,
                fields="description_vector",
            )
        ],
        top=3,
    )
    for r in results:
        print(f"  {r['name']} | {r['category']} | Rs.{r['price']} | Score: {r['@search.score']:.4f}")

    # --- 4. Filtered Search (vector + category filter) ---
    print("\n=== FILTERED SEARCH (Accessories only) ===")
    results = search_client.search(
        search_text=None,
        vector_queries=[
            VectorizedQuery(
                vector=query_vector,
                k_nearest_neighbors=3,
                fields="description_vector",
            )
        ],
        filter="category eq 'Accessories'",
    )
    for r in results:
        print(f"  {r['name']} | {r['category']} | Rs.{r['price']} | Score: {r['@search.score']:.4f}")

    await openai_client.close()


if __name__ == "__main__":
    asyncio.run(main())
