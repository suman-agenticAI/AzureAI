"""
Lesson 13: Semantic Ranking — Reranker + Captions + Answers
============================================================
Adds semantic ranking on top of hybrid search.
Updates the existing product-catalog index with semantic config.
"""

import os
import sys
import asyncio
from dotenv import load_dotenv
from openai import AsyncAzureOpenAI
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SemanticConfiguration,
    SemanticSearch,
    SemanticPrioritizedFields,
    SemanticField,
)
from azure.search.documents import SearchClient
from azure.search.documents.models import (
    VectorizedQuery,
    QueryType,
    QueryCaptionType,
    QueryAnswerType,
)
from azure.core.credentials import AzureKeyCredential

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()


async def get_query_vector(openai_client, query):
    response = await openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=[query],
    )
    return response.data[0].embedding


async def main():
    # --- Step 1: Add semantic config to existing index ---
    print("Step 1: Adding semantic config to index...\n")

    index_client = SearchIndexClient(
        endpoint=os.getenv("SEARCH_ENDPOINT"),
        credential=AzureKeyCredential(os.getenv("SEARCH_ADMIN_KEY")),
    )

    # Get existing index
    index = index_client.get_index("product-catalog")

    # Add semantic configuration — tells the reranker which fields matter
    index.semantic_search = SemanticSearch(
        configurations=[
            SemanticConfiguration(
                name="product-semantic-config",
                prioritized_fields=SemanticPrioritizedFields(
                    title_field=SemanticField(field_name="name"),
                    content_fields=[SemanticField(field_name="description")],
                    keywords_fields=[SemanticField(field_name="category")],
                ),
            )
        ]
    )

    index_client.create_or_update_index(index)
    print("  Semantic config added: title=name, content=description, keywords=category\n")

    # --- Step 2: Search with all methods and compare ---
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
    query_vector = await get_query_vector(openai_client, query)

    # --- A: Hybrid search (no reranking) ---
    print("\n=== A: HYBRID SEARCH (no reranking) ===")
    results = search_client.search(
        search_text=query,
        vector_queries=[
            VectorizedQuery(vector=query_vector, k_nearest_neighbors=5, fields="description_vector")
        ],
        top=5,
    )
    for r in results:
        print(f"  {r['name']} | Rs.{r['price']} | Score: {r['@search.score']:.4f}")

    # --- B: Hybrid + Semantic Reranking ---
    print("\n=== B: HYBRID + SEMANTIC RERANKING ===")
    results = search_client.search(
        search_text=query,
        vector_queries=[
            VectorizedQuery(vector=query_vector, k_nearest_neighbors=5, fields="description_vector")
        ],
        query_type=QueryType.SEMANTIC,
        semantic_configuration_name="product-semantic-config",
        top=5,
    )
    for r in results:
        reranker_score = r.get("@search.reranker_score", "N/A")
        print(f"  {r['name']} | Rs.{r['price']} | Reranker: {reranker_score}")

    # --- C: Hybrid + Semantic + Captions ---
    print("\n=== C: HYBRID + SEMANTIC + CAPTIONS ===")
    results = search_client.search(
        search_text=query,
        vector_queries=[
            VectorizedQuery(vector=query_vector, k_nearest_neighbors=5, fields="description_vector")
        ],
        query_type=QueryType.SEMANTIC,
        semantic_configuration_name="product-semantic-config",
        query_caption=QueryCaptionType.EXTRACTIVE,
        top=5,
    )
    for r in results:
        reranker_score = r.get("@search.reranker_score", "N/A")
        print(f"  {r['name']} | Reranker: {reranker_score}")
        captions = r.get("@search.captions", [])
        if captions:
            print(f"    Caption: {captions[0].text}")

    # --- D: Hybrid + Semantic + Answers ---
    print("\n=== D: SEMANTIC ANSWERS ===")
    results = search_client.search(
        search_text=query,
        vector_queries=[
            VectorizedQuery(vector=query_vector, k_nearest_neighbors=5, fields="description_vector")
        ],
        query_type=QueryType.SEMANTIC,
        semantic_configuration_name="product-semantic-config",
        query_caption=QueryCaptionType.EXTRACTIVE,
        query_answer=QueryAnswerType.EXTRACTIVE,
        top=5,
    )

    # Semantic answers — direct answer extracted from docs
    answers = results.get_answers()
    if answers:
        for ans in answers:
            print(f"  Direct answer: {ans.text}")
            print(f"  Confidence: {ans.score:.4f}")
    else:
        print("  No direct answer extracted")

    # Still print results
    print("\n  Results:")
    for r in results:
        reranker_score = r.get("@search.reranker_score", "N/A")
        print(f"    {r['name']} | Reranker: {reranker_score}")

    await openai_client.close()


if __name__ == "__main__":
    asyncio.run(main())
