"""
Lesson 8: Enterprise Config — Managed Identity + Tracing
=========================================================
Production-grade setup with tracing via Application Insights.
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

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()


def get_order_status(order_id: str) -> str:
    """Check order status."""
    orders = {
        "ORD-001": {"status": "Shipped", "delivery": "March 25, 2026"},
        "ORD-002": {"status": "Processing", "delivery": "March 28, 2026"},
    }
    order = orders.get(order_id)
    if order:
        return json.dumps(order)
    return json.dumps({"error": f"Order {order_id} not found"})


async def main(user_message: str):
    # --- Managed Identity ---
    # DefaultAzureCredential works everywhere:
    #   Local dev:  uses az login
    #   Azure VM:   uses Managed Identity (no keys needed)
    #   Container:  uses Managed Identity
    #   App Service: uses Managed Identity
    # ZERO code changes between environments
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
            name="enterprise-agent",
            instructions="""You are a support agent for TechCorp.
            Use get_order_status to check orders.
            Be concise.""",
            toolset=toolset,
        )

        # --- Run with tracing metadata ---
        # Add metadata to track requests in production
        run = await client.create_thread_and_process_run(
            agent_id=agent.id,
            thread=AgentThreadCreationOptions(
                messages=[ThreadMessageOptions(role="user", content=user_message)]
            ),
            metadata={
                "customer_id": "CUST-12345",
                "channel": "web-chat",
                "session_id": "sess-abc-789",
            },
        )

        # --- Print run details (what you'd log in production) ---
        print("--- Run Details ---")
        print(f"Run ID: {run.id}")
        print(f"Thread ID: {run.thread_id}")
        print(f"Status: {run.status}")
        print(f"Model: {run.model}")
        print(
            f"Tokens - Prompt: {run.usage.prompt_tokens}, "
            f"Completion: {run.usage.completion_tokens}, "
            f"Total: {run.usage.total_tokens}"
        )
        print(f"Metadata: {run.metadata}")

        # --- Get run steps (the trace) ---
        print("\n--- Trace (Run Steps) ---")
        steps = client.run_steps.list(thread_id=run.thread_id, run_id=run.id)
        step_num = 1
        async for step in steps:
            print(f"Step {step_num}: {step.type} | Status: {step.status}")
            if step.type == "tool_calls":
                for tool_call in step.step_details.tool_calls:
                    if hasattr(tool_call, "function"):
                        print(
                            f"  Called: {tool_call.function.name}({tool_call.function.arguments})"
                        )
                        print(f"  Result: {tool_call.function.output}")
            step_num += 1

        # --- Agent response ---
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
