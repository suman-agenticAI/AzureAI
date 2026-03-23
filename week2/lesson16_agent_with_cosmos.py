"""
Lesson 16 - Part 3: Agent with Cosmos DB Memory
=================================================
The order support agent from Week 1, now with:
- Conversation history stored in Cosmos DB
- Agent run logs for debugging
- Memory recall — agent can check past interactions
"""

import os
import sys
import json
import asyncio
from datetime import datetime, timezone
from dotenv import load_dotenv
from azure.ai.agents.aio import AgentsClient
from azure.ai.agents.models import (
    AgentThreadCreationOptions,
    ThreadMessageOptions,
    FunctionTool,
    ToolSet,
)
from azure.identity.aio import DefaultAzureCredential
from azure.cosmos import CosmosClient, PartitionKey

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()


# --- Cosmos DB helper class ---
class AgentMemory:
    """Handles all Cosmos DB operations for the agent."""

    def __init__(self):
        self.client = CosmosClient(
            url=os.getenv("COSMOS_ENDPOINT"),
            credential=os.getenv("COSMOS_KEY"),
        )
        db = self.client.create_database_if_not_exists("agent-memory")
        self.conversations = db.create_container_if_not_exists(
            id="conversations",
            partition_key=PartitionKey(path="/user_id"),
        )
        self.run_logs = db.create_container_if_not_exists(
            id="run-logs",
            partition_key=PartitionKey(path="/agent"),
        )

    def save_message(self, user_id, session_id, role, content):
        """Save a single message to conversation history."""
        msg_id = f"msg-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"
        self.conversations.upsert_item({
            "id": msg_id,
            "user_id": user_id,
            "session_id": session_id,
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def save_run_log(self, agent_name, user_id, query, response, tokens, latency_ms, status):
        """Save an agent run log for debugging."""
        run_id = f"run-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"
        self.run_logs.upsert_item({
            "id": run_id,
            "agent": agent_name,
            "user_id": user_id,
            "query": query,
            "response": response,
            "tokens_used": tokens,
            "latency_ms": latency_ms,
            "status": status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def get_conversation_history(self, user_id, limit=10):
        """Retrieve past messages for a user."""
        query = f"SELECT TOP {limit} * FROM c WHERE c.user_id = '{user_id}' ORDER BY c.timestamp DESC"
        items = list(self.conversations.query_items(query=query, partition_key=user_id))
        items.reverse()  # oldest first
        return items

    def get_past_interactions_summary(self, user_id):
        """Get a summary of past interactions to give the agent context."""
        history = self.get_conversation_history(user_id, limit=20)
        if not history:
            return "No prior interactions found for this customer."
        summary = "Previous conversation history:\n"
        for msg in history:
            role = "Customer" if msg["role"] == "user" else "Agent"
            summary += f"  {role}: {msg['content']}\n"
        return summary


# --- Tool functions ---
def get_order_status(order_id: str) -> str:
    """Check order delivery status."""
    orders = {
        "ORD-001": {"status": "Shipped", "delivery": "March 25, 2026", "amount": 85000},
        "ORD-002": {"status": "Processing", "delivery": "March 28, 2026", "amount": 65000},
        "ORD-003": {"status": "Delivered", "delivery": "March 20, 2026", "amount": 25000},
    }
    order = orders.get(order_id)
    if order:
        return json.dumps(order)
    return json.dumps({"error": f"Order {order_id} not found"})


def check_return_eligibility(order_id: str) -> str:
    """Check if order can be returned."""
    eligibility = {
        "ORD-001": {"eligible": True, "deadline": "April 24, 2026"},
        "ORD-002": {"eligible": False, "reason": "Not yet delivered"},
        "ORD-003": {"eligible": True, "deadline": "April 19, 2026"},
    }
    result = eligibility.get(order_id)
    if result:
        return json.dumps(result)
    return json.dumps({"error": f"Order {order_id} not found"})


async def main():
    credential = DefaultAzureCredential()

    # --- Initialize memory ---
    memory = AgentMemory()
    print("Cosmos DB memory connected\n")

    # Simulate a customer
    USER_ID = "CUST-12345"
    SESSION_ID = f"sess-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

    # --- Get past history (if any) ---
    past_context = memory.get_past_interactions_summary(USER_ID)
    print(f"Past context loaded: {len(past_context)} chars\n")

    async with AgentsClient(
        endpoint=os.getenv("PROJECT_ENDPOINT"),
        credential=credential,
    ) as client:

        tools = {get_order_status, check_return_eligibility}
        toolset = ToolSet()
        toolset.add(FunctionTool(tools))
        client.enable_auto_function_calls(tools)

        # Agent gets past history in its instructions
        agent = await client.create_agent(
            model=os.getenv("MODEL_DEPLOYMENT_NAME"),
            name="memory-agent",
            instructions=f"""You are a support agent for TechCorp Electronics.
            Tools: get_order_status, check_return_eligibility

            IMPORTANT — this customer has prior history with us:
            {past_context}

            Rules:
            - Reference past interactions when relevant
            - If customer already asked about an order, don't ask for ID again
            - Be concise — 2-3 sentences max""",
            toolset=toolset,
        )

        print("=== TechCorp Support (with Memory) ===")
        print(f"Customer: {USER_ID} | Session: {SESSION_ID}")
        print("Type 'quit' to exit\n")

        # --- Chat loop ---
        import time

        # First message
        user_input = input("You: ")
        if user_input.lower() == "quit":
            await client.delete_agent(agent.id)
            await credential.close()
            return

        # Save user message to Cosmos
        memory.save_message(USER_ID, SESSION_ID, "user", user_input)

        start = time.time()
        run = await client.create_thread_and_process_run(
            agent_id=agent.id,
            thread=AgentThreadCreationOptions(
                messages=[ThreadMessageOptions(role="user", content=user_input)]
            ),
        )
        latency = int((time.time() - start) * 1000)

        thread_id = run.thread_id

        # Get response
        response_text = ""
        messages = client.messages.list(thread_id=thread_id)
        async for msg in messages:
            if msg.role == "assistant":
                response_text = msg.content[0].text.value
                break

        # Save agent response + run log to Cosmos
        memory.save_message(USER_ID, SESSION_ID, "assistant", response_text)
        memory.save_run_log(
            agent_name="memory-agent",
            user_id=USER_ID,
            query=user_input,
            response=response_text,
            tokens=run.usage.total_tokens if run.usage else 0,
            latency_ms=latency,
            status="success" if run.status.value == "completed" else "failed",
        )

        print(f"Agent: {response_text}\n")

        # Follow-up messages
        while True:
            user_input = input("You: ")
            if user_input.lower() == "quit":
                break

            memory.save_message(USER_ID, SESSION_ID, "user", user_input)

            start = time.time()
            run = await client.runs.create_and_process(
                thread_id=thread_id,
                agent_id=agent.id,
                additional_messages=[
                    ThreadMessageOptions(role="user", content=user_input)
                ],
            )
            latency = int((time.time() - start) * 1000)

            response_text = ""
            messages = client.messages.list(thread_id=thread_id)
            async for msg in messages:
                if msg.role == "assistant":
                    response_text = msg.content[0].text.value
                    break

            memory.save_message(USER_ID, SESSION_ID, "assistant", response_text)
            memory.save_run_log(
                agent_name="memory-agent",
                user_id=USER_ID,
                query=user_input,
                response=response_text,
                tokens=run.usage.total_tokens if run.usage else 0,
                latency_ms=latency,
                status="success" if run.status.value == "completed" else "failed",
            )

            print(f"Agent: {response_text}\n")

        # Cleanup
        await client.delete_agent(agent.id)
        print("\nSession saved to Cosmos DB. Agent deleted.")

    await credential.close()


if __name__ == "__main__":
    asyncio.run(main())
