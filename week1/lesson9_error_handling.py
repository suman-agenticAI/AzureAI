"""
Lesson 9: Error Handling — Production-grade resilience
"""

import os
import sys
import json
import asyncio
from dotenv import load_dotenv
from azure.ai.agents.aio import AgentsClient
from azure.ai.agents.models import (
    AgentThreadCreationOptions,
    ThreadMessageOptions,
    FunctionTool,
    ToolSet,
)
from azure.identity.aio import DefaultAzureCredential
from azure.core.exceptions import HttpResponseError, ServiceRequestError

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()


# --- Tool that can fail (simulates real-world) ---
call_count = 0


def get_order_status(order_id: str) -> str:
    """Simulates a flaky database connection."""
    global call_count
    call_count += 1

    # Simulate: fails on first call, works on retry
    if call_count == 1:
        raise Exception("Database connection timeout")

    orders = {
        "ORD-001": {"status": "Shipped", "delivery": "March 25, 2026"},
        "ORD-002": {"status": "Processing", "delivery": "March 28, 2026"},
    }
    order = orders.get(order_id)
    if order:
        return json.dumps(order)
    return json.dumps({"error": f"Order {order_id} not found"})


async def run_with_retry(client, agent_id, user_message, max_retries=3):
    """Run agent with retry logic — production pattern."""
    for attempt in range(1, max_retries + 1):
        try:
            print(f"Attempt {attempt}...")
            run = await client.create_thread_and_process_run(
                agent_id=agent_id,
                thread=AgentThreadCreationOptions(
                    messages=[ThreadMessageOptions(role="user", content=user_message)]
                ),
            )

            # Check if run failed
            if run.status == "failed":
                print(f"  Run failed: {run.last_error}")
                if attempt < max_retries:
                    wait = attempt * 2  # exponential backoff: 2s, 4s, 6s
                    print(f"  Retrying in {wait}s...")
                    await asyncio.sleep(wait)
                    continue
                else:
                    return None, "Agent failed after all retries"

            return run, None

        except HttpResponseError as e:
            # Rate limit (429) or server error (500+)
            print(f"  HTTP error: {e.status_code} - {e.message}")
            if e.status_code == 429:
                wait = attempt * 5  # longer wait for rate limits
                print(f"  Rate limited. Waiting {wait}s...")
                await asyncio.sleep(wait)
            elif e.status_code >= 500:
                wait = attempt * 2
                print(f"  Server error. Retrying in {wait}s...")
                await asyncio.sleep(wait)
            else:
                return None, f"Client error: {e.message}"

        except ServiceRequestError as e:
            # Network issues
            print(f"  Network error: {e}")
            if attempt < max_retries:
                await asyncio.sleep(attempt * 2)
            else:
                return None, "Network error after all retries"

    return None, "Max retries exceeded"


async def main(user_message: str):
    credential = DefaultAzureCredential()

    async with AgentsClient(
        endpoint=os.getenv("PROJECT_ENDPOINT"),
        credential=credential,
    ) as client:

        tools = {get_order_status}
        toolset = ToolSet()
        toolset.add(FunctionTool(tools))
        client.enable_auto_function_calls(tools)

        agent = await client.create_agent(
            model=os.getenv("MODEL_DEPLOYMENT_NAME"),
            name="resilient-agent",
            instructions="""You are a support agent for TechCorp.
            Use get_order_status to check orders.
            If a tool fails, tell the customer there's a temporary issue
            and ask them to try again in a few minutes.""",
            toolset=toolset,
        )

        # --- Run with retry ---
        run, error = await run_with_retry(client, agent.id, user_message)

        if error:
            print(f"\nFailed: {error}")
            print(
                "Fallback: Sorry, our systems are temporarily unavailable. "
                "Please try again in a few minutes."
            )
        else:
            messages = client.messages.list(thread_id=run.thread_id)
            async for msg in messages:
                if msg.role == "assistant":
                    print(f"\nAgent: {msg.content[0].text.value}")
                    break

        # Cleanup
        await client.delete_agent(agent.id)
        print("\nCleanup: Agent deleted")

    await credential.close()


if __name__ == "__main__":
    user_input = input("You: ")
    asyncio.run(main(user_input))
