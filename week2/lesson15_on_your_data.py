"""
Lesson 15: Azure OpenAI "On Your Data" — Zero-code RAG
========================================================
One API call does: search your data + generate grounded answer.
Uses the product-catalog index we already created in Lesson 12.
"""

import os
import sys
import asyncio
from dotenv import load_dotenv
from openai import AsyncAzureOpenAI

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()


async def main():
    base_endpoint = os.getenv("PROJECT_ENDPOINT").split("/api/")[0]
    client = AsyncAzureOpenAI(
        azure_endpoint=base_endpoint,
        api_key=os.getenv("AZURE_API_KEY"),
        api_version="2024-06-01",
    )

    print("=== Azure OpenAI 'On Your Data' — Zero-code RAG ===")
    print("Type 'quit' to exit\n")

    while True:
        query = input("You: ")
        if query.lower() == "quit":
            break

        # One API call — Azure searches your index AND generates answer
        response = await client.chat.completions.create(
            model="gpt-4o",
            temperature=0,
            messages=[
                {"role": "system", "content": "You are a helpful product advisor for TechCorp."},
                {"role": "user", "content": query},
            ],
            extra_body={
                "data_sources": [
                    {
                        "type": "azure_search",
                        "parameters": {
                            "endpoint": os.getenv("SEARCH_ENDPOINT"),
                            "index_name": "product-catalog",
                            "authentication": {
                                "type": "api_key",
                                "key": os.getenv("SEARCH_ADMIN_KEY"),
                            },
                            "query_type": "vector_semantic_hybrid",
                            "embedding_dependency": {
                                "type": "deployment_name",
                                "deployment_name": "text-embedding-3-small",
                            },
                            "semantic_configuration": "product-semantic-config",
                            "top_n_documents": 3,
                        },
                    }
                ]
            },
        )

        answer = response.choices[0].message.content
        print(f"\nAdvisor: {answer}")

        # Show citations if available
        context = response.choices[0].message.model_extra
        if context and "context" in context:
            citations = context["context"].get("citations", [])
            if citations:
                print(f"\n  Sources:")
                for c in citations:
                    print(f"    - {c.get('title', 'N/A')}: {c.get('content', '')[:80]}...")

        print(f"  [Tokens: {response.usage.total_tokens}]\n")

    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
