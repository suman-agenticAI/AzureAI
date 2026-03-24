"""
Lesson 18 - Part 2: Agent worker — processes requests from Service Bus queue
=============================================================================
Picks messages from queue → runs the appropriate agent → sends response.
This is how agents work in production — queue-based, reliable, scalable.
"""

import os
import sys
import json
import asyncio
from dotenv import load_dotenv
from azure.servicebus.aio import ServiceBusClient
from azure.servicebus import ServiceBusReceiveMode
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

QUEUE_NAME = "support-requests"


# --- Tool functions ---
def get_order_status(order_id: str) -> str:
    orders = {
        "ORD-001": {"status": "Shipped", "delivery": "March 25, 2026"},
        "ORD-003": {"status": "Delivered", "delivery": "March 20, 2026"},
    }
    order = orders.get(order_id)
    if order:
        return json.dumps(order)
    return json.dumps({"error": f"Order {order_id} not found"})


def diagnose_technical_issue(product: str, issue: str) -> str:
    solutions = {
        "flickering": {"diagnosis": "Display driver issue", "severity": "Medium"},
        "charging": {"diagnosis": "Power delivery issue", "severity": "High"},
    }
    for key, solution in solutions.items():
        if key in issue.lower():
            return json.dumps(solution)
    return json.dumps({"diagnosis": "Unknown issue", "severity": "Unknown"})


async def process_message(agent_client, message_body):
    """Process a single support request using the appropriate agent."""
    req = json.loads(str(message_body))
    department = req["department"]

    # Pick the right tools based on department
    if department == "orders":
        tools = {get_order_status}
        instructions = "You are an order specialist. Use get_order_status. Be concise."
    elif department == "technical":
        tools = {diagnose_technical_issue}
        instructions = "You are a tech specialist. Use diagnose_technical_issue. Be concise."
    else:
        tools = set()
        instructions = "You are a support agent. Help the customer. Be concise."

    toolset = ToolSet()
    if tools:
        toolset.add(FunctionTool(tools))
        agent_client.enable_auto_function_calls(tools)

    agent = await agent_client.create_agent(
        model=os.getenv("MODEL_DEPLOYMENT_NAME"),
        name=f"{department}-worker",
        instructions=instructions,
        toolset=toolset if tools else None,
    )

    run = await agent_client.create_thread_and_process_run(
        agent_id=agent.id,
        thread=AgentThreadCreationOptions(
            messages=[ThreadMessageOptions(role="user", content=req["message"])]
        ),
    )

    # Get response
    response = ""
    messages = agent_client.messages.list(thread_id=run.thread_id)
    async for msg in messages:
        if msg.role == "assistant":
            response = msg.content[0].text.value
            break

    await agent_client.delete_agent(agent.id)
    return req, response


async def main():
    credential = DefaultAzureCredential()

    async with AgentsClient(
        endpoint=os.getenv("PROJECT_ENDPOINT"),
        credential=credential,
    ) as agent_client:

        async with ServiceBusClient.from_connection_string(
            os.getenv("SERVICE_BUS_CONNECTION")
        ) as sb_client:
            receiver = sb_client.get_queue_receiver(
                queue_name=QUEUE_NAME,
                receive_mode=ServiceBusReceiveMode.RECEIVE_AND_DELETE,
            )

            async with receiver:
                print(f"Listening on queue '{QUEUE_NAME}'...\n")

                processed = 0
                while True:
                    # Pick ONE message at a time — process and complete before lock expires
                    messages = await receiver.receive_messages(
                        max_message_count=1,
                        max_wait_time=10,
                    )

                    if not messages:
                        break

                    msg = messages[0]
                    req, response = await process_message(agent_client, msg)

                    print(f"--- {req['id']} ({req['department']}) ---")
                    print(f"Customer: {req['message']}")
                    print(f"Agent: {response}")
                    print()

                    # No need to complete — RECEIVE_AND_DELETE mode auto-removes
                    processed += 1

                print(f"Done. Processed {processed} messages.")

    await credential.close()


if __name__ == "__main__":
    asyncio.run(main())
