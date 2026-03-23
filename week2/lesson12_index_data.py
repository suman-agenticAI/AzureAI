"""
Lesson 12 - Part 1: Create Index + Insert Data
================================================
Creates an Azure AI Search index with vector fields,
embeds documents, and pushes them to the index.
"""

import os
import sys
import asyncio
from dotenv import load_dotenv
from openai import AsyncAzureOpenAI
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents import SearchClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SearchField,
    SearchFieldDataType,
    SimpleField,
    SearchableField,
    VectorSearch,
    HnswAlgorithmConfiguration,
    VectorSearchProfile,
    SearchableField,
)
from azure.core.credentials import AzureKeyCredential

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()

# --- Sample product catalog data ---
PRODUCTS = [
    {
        "id": "1",
        "name": "Laptop Pro 15",
        "category": "Laptops",
        "price": 85000,
        "description": "High-performance laptop with 15-inch display, Intel i7 processor, 16GB RAM, 512GB SSD. Ideal for professionals and developers.",
    },
    {
        "id": "2",
        "name": "Desktop Elite",
        "category": "Desktops",
        "price": 65000,
        "description": "Powerful desktop computer with Intel i5 processor, 32GB RAM, 1TB HDD. Perfect for office work and multitasking.",
    },
    {
        "id": "3",
        "name": "Monitor Ultra 27",
        "category": "Monitors",
        "price": 25000,
        "description": "27-inch 4K UHD monitor with IPS panel, 99% sRGB coverage. Great for designers, video editors, and content creators.",
    },
    {
        "id": "4",
        "name": "Keyboard Pro Mechanical",
        "category": "Accessories",
        "price": 3500,
        "description": "Mechanical keyboard with Cherry MX switches, RGB backlight, USB-C connection. Built for fast typing and gaming.",
    },
    {
        "id": "5",
        "name": "Mouse Ergo Wireless",
        "category": "Accessories",
        "price": 1500,
        "description": "Ergonomic wireless mouse with 4000 DPI sensor, silent clicks, Bluetooth and USB receiver. Comfortable for long hours.",
    },
    {
        "id": "6",
        "name": "Laptop Budget 14",
        "category": "Laptops",
        "price": 42000,
        "description": "Affordable 14-inch laptop with AMD Ryzen 5, 8GB RAM, 256GB SSD. Good for students and everyday use.",
    },
    {
        "id": "7",
        "name": "Webcam HD Pro",
        "category": "Accessories",
        "price": 4500,
        "description": "Full HD 1080p webcam with built-in microphone, auto-focus, and low-light correction. Perfect for video calls and streaming.",
    },
    {
        "id": "8",
        "name": "Docking Station USB-C",
        "category": "Accessories",
        "price": 8500,
        "description": "USB-C docking station with dual HDMI output, 3 USB-A ports, Ethernet, and 100W power delivery. Expand your laptop connectivity.",
    },
]


async def generate_embeddings(openai_client, texts):
    """Generate embeddings for a list of texts."""
    response = await openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=texts,
    )
    return [item.embedding for item in response.data]


async def main():
    # --- Step 1: Create the search index ---
    print("Step 1: Creating search index...")

    index_client = SearchIndexClient(
        endpoint=os.getenv("SEARCH_ENDPOINT"),
        credential=AzureKeyCredential(os.getenv("SEARCH_ADMIN_KEY")),
    )

    # Define index schema — what fields the index has
    index = SearchIndex(
        name="product-catalog",
        fields=[
            SimpleField(name="id", type=SearchFieldDataType.String, key=True),
            SearchableField(name="name", type=SearchFieldDataType.String),
            SearchableField(name="category", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="price", type=SearchFieldDataType.Double, filterable=True, sortable=True),
            SearchableField(name="description", type=SearchFieldDataType.String),
            SearchField(
                name="description_vector",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                vector_search_dimensions=1536,
                vector_search_profile_name="default-profile",
            ),
        ],
        vector_search=VectorSearch(
            algorithms=[HnswAlgorithmConfiguration(name="default-algo")],
            profiles=[VectorSearchProfile(name="default-profile", algorithm_configuration_name="default-algo")],
        ),
    )

    # Create or update the index
    index_client.create_or_update_index(index)
    print(f"  Index 'product-catalog' created with {len(index.fields)} fields")

    # --- Step 2: Generate embeddings for all products ---
    print("\nStep 2: Generating embeddings...")

    base_endpoint = os.getenv("PROJECT_ENDPOINT").split("/api/")[0]
    openai_client = AsyncAzureOpenAI(
        azure_endpoint=base_endpoint,
        api_key=os.getenv("AZURE_API_KEY"),
        api_version="2024-06-01",
    )

    descriptions = [p["description"] for p in PRODUCTS]
    vectors = await generate_embeddings(openai_client, descriptions)
    print(f"  Generated {len(vectors)} embeddings ({len(vectors[0])} dimensions each)")

    # --- Step 3: Upload documents with vectors ---
    print("\nStep 3: Uploading documents to index...")

    search_client = SearchClient(
        endpoint=os.getenv("SEARCH_ENDPOINT"),
        index_name="product-catalog",
        credential=AzureKeyCredential(os.getenv("SEARCH_ADMIN_KEY")),
    )

    # Add vector to each product
    documents = []
    for i, product in enumerate(PRODUCTS):
        doc = {**product, "description_vector": vectors[i]}
        documents.append(doc)

    result = search_client.upload_documents(documents)
    succeeded = sum(1 for r in result if r.succeeded)
    print(f"  Uploaded {succeeded}/{len(documents)} documents")

    await openai_client.close()
    print("\nDone! Index is ready for searching.")


if __name__ == "__main__":
    asyncio.run(main())
