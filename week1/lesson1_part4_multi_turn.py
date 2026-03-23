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
    TruncationObject,
)
from azure.identity.aio import DefaultAzureCredential

load_dotenv()


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


def create_support_ticket(customer_name: str, issue: str, order_id: str = "") -> str:
    ticket_id = "TKT-" + str(hash(customer_name + issue))[-6:]
    return json.dumps(
        {
            "ticket_id": ticket_id,
            "status": "Created",
            "message": f"Ticket {ticket_id} created for {customer_name}. Our team will respond within 24 hours.",
        }
    )


async def main():
    credential = DefaultAzureCredential()

    async with AgentsClient(
        endpoint=os.getenv("PROJECT_ENDPOINT"),
        credential=credential,
    ) as client:

        tools = {get_order_status, check_return_eligibility, create_support_ticket}
        toolset = ToolSet()
        toolset.add(FunctionTool(tools))
        client.enable_auto_function_calls(tools)

        agent = await client.create_agent(
            model=os.getenv("MODEL_DEPLOYMENT_NAME"),
            name="chat-support-agent",
            instructions="""You are a customer support agent for TechCorp Electronics.
            You have 3 tools: get_order_status, check_return_eligibility, create_support_ticket.
            - Be professional and concise
            - Remember what the customer said earlier in the conversation
            - If they mention an order ID once, remember it for follow-up questions""",
            toolset=toolset,
        )
        print(f"Agent ready -- ID: {agent.id}")
        print("Type 'quit' to exit\n")

        # --- First message creates the thread ---
        user_input = input("You: ")
        if user_input.lower() == "quit":
            await client.delete_agent(agent.id)
            await credential.close()
            return

        run = await client.create_thread_and_process_run(
            agent_id=agent.id,
            thread=AgentThreadCreationOptions(
                messages=[ThreadMessageOptions(role="user", content=user_input)]
            ),
        )

        # Get the thread ID -- we'll reuse this for all follow-up messages
        thread_id = run.thread_id

        # Print agent response
        messages = client.messages.list(thread_id=thread_id)
        async for msg in messages:
            if msg.role == "assistant":
                print(f"Agent: {msg.content[0].text.value}\n")
                break  # Only print the latest response

        # --- Follow-up messages use the SAME thread ---
        while True:
            user_input = input("You: ")
            if user_input.lower() == "quit":
                break

            # Add message to existing thread and run
            # truncation_strategy: only send last 10 messages to LLM
            # Full history stays in thread, but saves tokens + avoids context overflow
            run = await client.runs.create_and_process(
                thread_id=thread_id,
                agent_id=agent.id,
                additional_messages=[
                    ThreadMessageOptions(role="user", content=user_input)
                ],
                truncation_strategy=TruncationObject(
                    type="last_messages",
                    last_messages=10,
                ),
            )

            # Print latest agent response
            messages = client.messages.list(thread_id=thread_id)
            async for msg in messages:
                if msg.role == "assistant":
                    print(f"Agent: {msg.content[0].text.value}\n")
                    break

        # Cleanup
        await client.delete_agent(agent.id)
        print("Session ended. Agent deleted.")

    await credential.close()


if __name__ == "__main__":
    asyncio.run(main())
