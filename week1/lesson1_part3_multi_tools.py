import os
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

load_dotenv()


# --- Tool 1: Order Status ---
def get_order_status(order_id: str) -> str:
    orders = {
        "ORD-001": {"status": "Shipped", "delivery": "March 25, 2026"},
        "ORD-002": {"status": "Processing", "delivery": "March 28, 2026"},
        "ORD-003": {"status": "Delivered", "delivery": "March 20, 2026"},
    }
    order = orders.get(order_id)
    if order:
        return json.dumps(order)
    return json.dumps({"error": f"Order {order_id} not found"})


# --- Tool 2: Return Eligibility ---
def check_return_eligibility(order_id: str) -> str:
    policies = {
        "ORD-001": {
            "eligible": True,
            "reason": "Within 30-day return window",
            "deadline": "April 20, 2026",
        },
        "ORD-002": {"eligible": False, "reason": "Order not yet delivered"},
        "ORD-003": {
            "eligible": True,
            "reason": "Within 30-day return window",
            "deadline": "April 19, 2026",
        },
    }
    policy = policies.get(order_id)
    if policy:
        return json.dumps(policy)
    return json.dumps({"error": f"Order {order_id} not found"})


# --- Tool 3: Create Support Ticket ---
def create_support_ticket(customer_name: str, issue: str, order_id: str = "") -> str:
    ticket_id = "TKT-" + str(hash(customer_name + issue))[-6:]
    return json.dumps(
        {
            "ticket_id": ticket_id,
            "status": "Created",
            "message": f"Ticket {ticket_id} created for {customer_name}. Our team will respond within 24 hours.",
        }
    )


async def main(user_message: str):
    credential = DefaultAzureCredential()

    async with AgentsClient(
        endpoint=os.getenv("PROJECT_ENDPOINT"),
        credential=credential,
    ) as client:

        toolset = ToolSet()
        toolset.add(
            FunctionTool(
                {get_order_status, check_return_eligibility, create_support_ticket}
            )
        )
        client.enable_auto_function_calls(
            {get_order_status, check_return_eligibility, create_support_ticket}
        )

        agent = await client.create_agent(
            model=os.getenv("MODEL_DEPLOYMENT_NAME"),
            name="full-support-agent",
            instructions="""You are a customer support agent for TechCorp Electronics.
            You have 3 tools:
            - get_order_status: Check order delivery status
            - check_return_eligibility: Check if an order can be returned
            - create_support_ticket: Create a ticket for issues that need human follow-up
            
            Rules:
            - Always ask for order ID if the customer doesn't provide one
            - If a customer wants to return, check eligibility FIRST before advising
            - Create a support ticket for complex issues you cannot resolve
            - Be professional and concise""",
            toolset=toolset,
        )
        print(f"Agent created with 3 tools -- ID: {agent.id}")

        run = await client.create_thread_and_process_run(
            agent_id=agent.id,
            thread=AgentThreadCreationOptions(
                messages=[ThreadMessageOptions(role="user", content=user_message)]
            ),
        )
        print(f"Run completed -- Status: {run.status}")

        messages = client.messages.list(thread_id=run.thread_id)
        async for msg in messages:
            if msg.role == "assistant":
                print(f"\nAgent: {msg.content[0].text.value}")

        await client.delete_agent(agent.id)
        print("\nCleanup: Agent deleted")

    await credential.close()


if __name__ == "__main__":
    user_input = input("You: ")
    asyncio.run(main(user_input))
