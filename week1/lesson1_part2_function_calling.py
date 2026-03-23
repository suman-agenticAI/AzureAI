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


# --- This function lives OUTSIDE main ---
# In production, this would query a database
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


# --- Everything else lives INSIDE main ---
async def main(user_message: str):
    credential = DefaultAzureCredential()

    async with AgentsClient(
        endpoint=os.getenv("PROJECT_ENDPOINT"),
        credential=credential,
    ) as client:

        # Bundle the function so the agent can call it
        toolset = ToolSet()
        toolset.add(FunctionTool({get_order_status}))

        # Register functions so SDK can auto-execute them
        client.enable_auto_function_calls({get_order_status})

        # Create agent with the tool attached
        agent = await client.create_agent(
            model=os.getenv("MODEL_DEPLOYMENT_NAME"),
            name="order-support-agent",
            instructions="""You are a customer support agent for TechCorp.
            - When customers ask about order status, use the get_order_status function
            - Always ask for the order ID if the customer doesn't provide one
            - Be professional and concise""",
            toolset=toolset,
        )
        print(f"Agent created with tools — ID: {agent.id}")

        # Run the agent — SDK auto-executes the function when agent calls it
        run = await client.create_thread_and_process_run(
            agent_id=agent.id,
            thread=AgentThreadCreationOptions(
                messages=[ThreadMessageOptions(role="user", content=user_message)]
            ),
        )
        print(f"Run completed — Status: {run.status}")

        # Read response
        messages = client.messages.list(thread_id=run.thread_id)
        async for msg in messages:
            if msg.role == "assistant":
                print(f"\nAgent: {msg.content[0].text.value}")

        # Cleanup — commented out so you can see the agent in Azure portal
        # await client.delete_agent(agent.id)
        # print("\nCleanup: Agent deleted")
        print(f"\nAgent still alive on Azure — ID: {agent.id}")
        print("Go to AI Foundry -> Agents (left sidebar) to see it")

    await credential.close()


# --- Entry point ---
if __name__ == "__main__":
    user_input = input("You: ")
    asyncio.run(main(user_input))
