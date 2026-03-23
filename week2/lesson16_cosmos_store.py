"""
Lesson 16 - Part 1: Cosmos DB — Store Agent Conversations
==========================================================
Creates database + container, stores conversation history and agent run logs.
"""

import os
import sys
from dotenv import load_dotenv
from azure.cosmos import CosmosClient, PartitionKey

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()


def main():
    # --- Step 1: Connect to Cosmos DB ---
    client = CosmosClient(
        url=os.getenv("COSMOS_ENDPOINT"),
        credential=os.getenv("COSMOS_KEY"),
    )

    # --- Step 2: Create database ---
    database = client.create_database_if_not_exists("agent-memory")
    print(f"Database: {database.id}")

    # --- Step 3: Create containers ---
    conversations = database.create_container_if_not_exists(
        id="conversations",
        partition_key=PartitionKey(path="/user_id"),
    )
    print(f"Container: {conversations.id}")

    run_logs = database.create_container_if_not_exists(
        id="run-logs",
        partition_key=PartitionKey(path="/agent"),
    )
    print(f"Container: {run_logs.id}")

    # --- Step 4: Store conversation history ---
    print("\nStoring conversation history...")

    messages = [
        {
            "id": "msg-001",
            "user_id": "CUST-12345",
            "session_id": "sess-abc",
            "role": "user",
            "content": "Where is my order ORD-001?",
            "timestamp": "2026-03-23T10:00:00Z",
        },
        {
            "id": "msg-002",
            "user_id": "CUST-12345",
            "session_id": "sess-abc",
            "role": "assistant",
            "content": "Your order ORD-001 has been shipped and will arrive on March 25, 2026.",
            "timestamp": "2026-03-23T10:00:05Z",
        },
        {
            "id": "msg-003",
            "user_id": "CUST-12345",
            "session_id": "sess-abc",
            "role": "user",
            "content": "Can I return it?",
            "timestamp": "2026-03-23T10:01:00Z",
        },
        {
            "id": "msg-004",
            "user_id": "CUST-12345",
            "session_id": "sess-abc",
            "role": "assistant",
            "content": "Yes, ORD-001 is eligible for return until April 24, 2026.",
            "timestamp": "2026-03-23T10:01:05Z",
        },
        {
            "id": "msg-005",
            "user_id": "CUST-67890",
            "session_id": "sess-xyz",
            "role": "user",
            "content": "My laptop screen is flickering",
            "timestamp": "2026-03-23T11:00:00Z",
        },
        {
            "id": "msg-006",
            "user_id": "CUST-67890",
            "session_id": "sess-xyz",
            "role": "assistant",
            "content": "Try updating your graphics drivers. If the issue persists, visit a service center.",
            "timestamp": "2026-03-23T11:00:05Z",
        },
    ]

    for msg in messages:
        conversations.upsert_item(msg)
    print(f"  Stored {len(messages)} messages")

    # --- Step 5: Store agent run logs ---
    print("\nStoring agent run logs...")

    runs = [
        {
            "id": "run-001",
            "agent": "order-specialist",
            "user_id": "CUST-12345",
            "query": "Where is my order ORD-001?",
            "tools_called": ["get_order_status"],
            "tool_inputs": {"order_id": "ORD-001"},
            "tool_outputs": {"status": "Shipped", "delivery": "March 25, 2026"},
            "response": "Your order is shipped, arriving March 25.",
            "tokens_used": 450,
            "latency_ms": 1200,
            "status": "success",
            "timestamp": "2026-03-23T10:00:05Z",
        },
        {
            "id": "run-002",
            "agent": "order-specialist",
            "user_id": "CUST-12345",
            "query": "Can I return it?",
            "tools_called": ["check_return_eligibility"],
            "tool_inputs": {"order_id": "ORD-001"},
            "tool_outputs": {"eligible": True, "deadline": "April 24, 2026"},
            "response": "Yes, eligible for return until April 24.",
            "tokens_used": 380,
            "latency_ms": 1100,
            "status": "success",
            "timestamp": "2026-03-23T10:01:05Z",
        },
        {
            "id": "run-003",
            "agent": "tech-specialist",
            "user_id": "CUST-67890",
            "query": "My laptop screen is flickering",
            "tools_called": ["diagnose_technical_issue"],
            "tool_inputs": {"product": "laptop", "issue": "screen flickering"},
            "tool_outputs": {"diagnosis": "Display driver issue", "severity": "Medium"},
            "response": "Try updating graphics drivers.",
            "tokens_used": 520,
            "latency_ms": 1500,
            "status": "success",
            "timestamp": "2026-03-23T11:00:05Z",
        },
        {
            "id": "run-004",
            "agent": "order-specialist",
            "user_id": "CUST-99999",
            "query": "Where is ORD-999?",
            "tools_called": ["get_order_status"],
            "tool_inputs": {"order_id": "ORD-999"},
            "tool_outputs": {"error": "Order not found"},
            "response": "Sorry, I couldn't find that order.",
            "tokens_used": 300,
            "latency_ms": 800,
            "status": "failed",
            "timestamp": "2026-03-23T12:00:00Z",
        },
    ]

    for run in runs:
        run_logs.upsert_item(run)
    print(f"  Stored {len(runs)} run logs")

    print("\nDone! Data ready for querying.")


if __name__ == "__main__":
    main()
