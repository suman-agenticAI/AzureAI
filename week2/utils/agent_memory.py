"""
Agent Memory Utility — Generic Cosmos DB wrapper for any agent.
Usage:
    from utils.agent_memory import AgentMemory

    memory = AgentMemory()
    memory.save_message(user_id, session_id, "user", "Hello")
    memory.save_run(agent, user_id, query, response, tokens, latency_ms)
    history = memory.get_history(user_id, limit=10)
"""

import os
import time
from datetime import datetime, timezone
from dotenv import load_dotenv
from azure.cosmos import CosmosClient, PartitionKey

load_dotenv()


class AgentMemory:
    """Generic Cosmos DB memory — plug into any agent."""

    def __init__(self, database_name="agent-memory"):
        self.client = CosmosClient(
            url=os.getenv("COSMOS_ENDPOINT"),
            credential=os.getenv("COSMOS_KEY"),
        )
        db = self.client.create_database_if_not_exists(database_name)
        self.conversations = db.create_container_if_not_exists(
            id="conversations",
            partition_key=PartitionKey(path="/user_id"),
        )
        self.run_logs = db.create_container_if_not_exists(
            id="run-logs",
            partition_key=PartitionKey(path="/agent"),
        )

    # --- Message operations ---

    def save_message(self, user_id, session_id, role, content):
        """Save one message (user or assistant)."""
        self.conversations.upsert_item({
            "id": f"msg-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}",
            "user_id": user_id,
            "session_id": session_id,
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def save_turn(self, user_id, session_id, user_message, agent_response):
        """Save a full turn (user + agent) in one call."""
        self.save_message(user_id, session_id, "user", user_message)
        self.save_message(user_id, session_id, "assistant", agent_response)

    # --- Run log operations ---

    def save_run(self, agent_name, user_id, query, response, tokens=0, latency_ms=0, status="success"):
        """Log an agent run for debugging."""
        self.run_logs.upsert_item({
            "id": f"run-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}",
            "agent": agent_name,
            "user_id": user_id,
            "query": query,
            "response": response,
            "tokens_used": tokens,
            "latency_ms": latency_ms,
            "status": status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    # --- Query operations ---

    def get_history(self, user_id, limit=10):
        """Get last N messages for a user (across all sessions)."""
        query = f"SELECT TOP {limit} * FROM c WHERE c.user_id = @user_id ORDER BY c.timestamp DESC"
        items = list(self.conversations.query_items(
            query=query,
            parameters=[{"name": "@user_id", "value": user_id}],
            partition_key=user_id,
        ))
        items.reverse()
        return items

    def get_session_history(self, user_id, session_id, limit=20):
        """Get messages from a specific session."""
        query = (
            f"SELECT TOP {limit} * FROM c "
            f"WHERE c.user_id = @user_id AND c.session_id = @session_id "
            f"ORDER BY c.timestamp DESC"
        )
        items = list(self.conversations.query_items(
            query=query,
            parameters=[
                {"name": "@user_id", "value": user_id},
                {"name": "@session_id", "value": session_id},
            ],
            partition_key=user_id,
        ))
        items.reverse()
        return items

    def get_history_as_text(self, user_id, limit=10):
        """Get past history formatted as text — inject into agent instructions."""
        history = self.get_history(user_id, limit)
        if not history:
            return "No prior interactions."
        lines = []
        for msg in history:
            role = "Customer" if msg["role"] == "user" else "Agent"
            lines.append(f"  {role}: {msg['content']}")
        return "Previous conversations:\n" + "\n".join(lines)

    def get_failed_runs(self, agent_name=None):
        """Get failed runs — for debugging."""
        if agent_name:
            query = "SELECT * FROM c WHERE c.status = 'failed' AND c.agent = @agent"
            params = [{"name": "@agent", "value": agent_name}]
        else:
            query = "SELECT * FROM c WHERE c.status = 'failed'"
            params = []
        return list(self.run_logs.query_items(
            query=query,
            parameters=params,
            enable_cross_partition_query=True,
        ))

    def get_token_usage(self):
        """Get total token usage per agent."""
        query = "SELECT c.agent, SUM(c.tokens_used) as total_tokens FROM c GROUP BY c.agent"
        return list(self.run_logs.query_items(
            query=query,
            enable_cross_partition_query=True,
        ))


# --- Timer utility for measuring latency ---
class Timer:
    """Usage: with Timer() as t: ... then t.ms gives milliseconds."""
    def __enter__(self):
        self.start = time.time()
        return self

    def __exit__(self, *args):
        self.ms = int((time.time() - self.start) * 1000)
