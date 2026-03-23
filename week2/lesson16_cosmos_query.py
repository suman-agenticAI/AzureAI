"""
Lesson 16 - Part 2: Cosmos DB — Query Conversations + Debug Agent Runs
=======================================================================
Shows how to query stored data for debugging, analytics, and memory retrieval.
"""

import os
import sys
from dotenv import load_dotenv
from azure.cosmos import CosmosClient

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()


def main():
    client = CosmosClient(
        url=os.getenv("COSMOS_ENDPOINT"),
        credential=os.getenv("COSMOS_KEY"),
    )

    database = client.get_database_client("agent-memory")
    conversations = database.get_container_client("conversations")
    run_logs = database.get_container_client("run-logs")

    # --- Query 1: Get full conversation for a user ---
    print("=== Query 1: CUST-12345's conversation history ===\n")
    query = "SELECT * FROM c WHERE c.user_id = 'CUST-12345' ORDER BY c.timestamp"
    for item in conversations.query_items(query=query, enable_cross_partition_query=True):
        role = "User" if item["role"] == "user" else "Agent"
        print(f"  {role}: {item['content']}")

    # --- Query 2: Get last 2 messages in a session ---
    print("\n=== Query 2: Last 2 messages in sess-abc ===\n")
    query = "SELECT TOP 2 * FROM c WHERE c.session_id = 'sess-abc' ORDER BY c.timestamp DESC"
    for item in conversations.query_items(query=query, partition_key="CUST-12345"):
        print(f"  [{item['timestamp']}] {item['role']}: {item['content']}")

    # --- Query 3: Find all failed runs ---
    print("\n=== Query 3: Failed agent runs ===\n")
    query = "SELECT * FROM c WHERE c.status = 'failed'"
    for item in run_logs.query_items(query=query, enable_cross_partition_query=True):
        print(f"  Agent: {item['agent']}")
        print(f"  Query: {item['query']}")
        print(f"  Error: {item['tool_outputs']}")

    # --- Query 4: Token usage per agent ---
    print("\n=== Query 4: Token usage per agent ===\n")
    query = "SELECT c.agent, SUM(c.tokens_used) as total_tokens FROM c GROUP BY c.agent"
    for item in run_logs.query_items(query=query, enable_cross_partition_query=True):
        print(f"  {item['agent']}: {item['total_tokens']} tokens")

    # --- Query 5: Slow runs (latency > 1200ms) ---
    print("\n=== Query 5: Slow runs (>1200ms) ===\n")
    query = "SELECT c.agent, c.query, c.latency_ms FROM c WHERE c.latency_ms > 1200"
    for item in run_logs.query_items(query=query, enable_cross_partition_query=True):
        print(f"  {item['agent']} | {item['latency_ms']}ms | {item['query']}")

    # --- Query 6: All tools called for a specific user ---
    print("\n=== Query 6: Tools used for CUST-12345 ===\n")
    query = "SELECT c.tools_called, c.query FROM c WHERE c.user_id = 'CUST-12345'"
    for item in run_logs.query_items(query=query, enable_cross_partition_query=True):
        print(f"  Tools: {item['tools_called']} | Query: {item['query']}")


if __name__ == "__main__":
    main()
