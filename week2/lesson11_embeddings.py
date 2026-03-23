"""
Lesson 11: Embeddings + Chunking Strategies
============================================
Part 1: Generate embeddings with Azure OpenAI
Part 2: Compare chunking strategies
Part 3: Similarity search (without any vector DB)
"""

import os
import sys
import asyncio
import numpy as np
from dotenv import load_dotenv
from openai import AsyncAzureOpenAI

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()


async def main():
    # --- Connect to Azure OpenAI ---
    # Using OpenAI SDK directly for embeddings (not the agents SDK)
    # For OpenAI SDK, use the base resource endpoint (not the project endpoint)
    base_endpoint = os.getenv("PROJECT_ENDPOINT").split("/api/")[0]
    client = AsyncAzureOpenAI(
        azure_endpoint=base_endpoint,
        api_key=os.getenv("AZURE_API_KEY"),
        api_version="2024-06-01",
    )

    # --- Part 1: Generate embeddings ---
    print("=== Part 1: Generating Embeddings ===\n")

    texts = [
        "How to return a damaged laptop",
        "Laptop return policy for defective items",
        "Best restaurants in Hyderabad",
    ]

    response = await client.embeddings.create(
        model="text-embedding-3-small",
        input=texts,
    )

    for i, item in enumerate(response.data):
        vector = item.embedding
        print(f"Text: '{texts[i]}'")
        print(f"  Dimensions: {len(vector)}")
        print(f"  First 5 values: {vector[:5]}")
        print()

    # --- Compare similarity ---
    # Cosine similarity: 1.0 = identical, 0.0 = unrelated
    v1 = np.array(response.data[0].embedding)
    v2 = np.array(response.data[1].embedding)
    v3 = np.array(response.data[2].embedding)

    sim_12 = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
    sim_13 = np.dot(v1, v3) / (np.linalg.norm(v1) * np.linalg.norm(v3))

    print("=== Similarity Scores ===")
    print(
        f"'return damaged laptop' vs 'laptop return policy':  {sim_12:.4f}  (should be HIGH)"
    )
    print(
        f"'return damaged laptop' vs 'restaurants Hyderabad': {sim_13:.4f}  (should be LOW)"
    )

    # --- Part 2: Configurable dimensions ---
    print("\n=== Part 2: Dimension Comparison ===\n")

    for dims in [256, 512, 1536]:
        resp = await client.embeddings.create(
            model="text-embedding-3-small",
            input=["How to return a damaged laptop"],
            dimensions=dims,
        )
        print(f"Dimensions: {dims} | Vector size: {len(resp.data[0].embedding)}")

    # --- Part 3: Chunking strategies ---
    print("\n=== Part 3: Chunking Strategies ===\n")

    document = """TechCorp Return Policy

Standard Returns: Items can be returned within 30 days of delivery. Items must be in original packaging and unused condition. Refund will be processed within 5-7 business days.

Damaged Items: Report damage within 48 hours of delivery. Photo evidence required. Free replacement or full refund offered. No need to return damaged item.

Non-Returnable Items: Software licenses once activated. Custom-built or configured items. Items without original packaging. Items purchased during clearance sales.

Return Shipping: Free return shipping for defective items. Customer pays return shipping for change-of-mind returns. Return shipping label provided via email within 24 hours."""

    # Strategy 1: Fixed size chunks
    def chunk_fixed(text, chunk_size=200, overlap=50):
        words = text.split()
        chunks = []
        for i in range(0, len(words), chunk_size - overlap):
            chunk = " ".join(words[i : i + chunk_size])
            if chunk:
                chunks.append(chunk)
        return chunks

    # Strategy 2: Paragraph-based chunks
    def chunk_by_paragraph(text):
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        return paragraphs

    # Strategy 3: Sentence-based chunks (group every N sentences)
    def chunk_by_sentences(text, sentences_per_chunk=3):
        import re

        sentences = re.split(r"(?<=[.!?])\s+", text)
        chunks = []
        for i in range(0, len(sentences), sentences_per_chunk):
            chunk = " ".join(sentences[i : i + sentences_per_chunk])
            if chunk:
                chunks.append(chunk)
        return chunks

    strategies = {
        "Fixed (200 words, 50 overlap)": chunk_fixed(document, 200, 50),
        "Paragraph-based": chunk_by_paragraph(document),
        "Sentence-based (3 per chunk)": chunk_by_sentences(document, 3),
    }

    for name, chunks in strategies.items():
        print(f"\n--- {name} ---")
        print(f"Number of chunks: {len(chunks)}")
        for i, chunk in enumerate(chunks):
            word_count = len(chunk.split())
            print(f"  Chunk {i+1}: {word_count} words | '{chunk[:60]}...'")

    # --- Part 4: Which chunking gives best search results? ---
    print("\n=== Part 4: Search Quality by Strategy ===\n")

    query = "Can I return a damaged item?"
    query_resp = await client.embeddings.create(
        model="text-embedding-3-small",
        input=[query],
    )
    query_vector = np.array(query_resp.data[0].embedding)

    for name, chunks in strategies.items():
        # Embed all chunks
        chunk_resp = await client.embeddings.create(
            model="text-embedding-3-small",
            input=chunks,
        )

        # Find best match
        best_score = 0
        best_chunk = ""
        for i, item in enumerate(chunk_resp.data):
            chunk_vector = np.array(item.embedding)
            score = np.dot(query_vector, chunk_vector) / (
                np.linalg.norm(query_vector) * np.linalg.norm(chunk_vector)
            )
            if score > best_score:
                best_score = score
                best_chunk = chunks[i]

        print(f"Strategy: {name}")
        print(f"  Best match score: {best_score:.4f}")
        print(f"  Best chunk: '{best_chunk[:80]}...'")
        print()

    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
