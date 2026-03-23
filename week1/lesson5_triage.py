"""
Lesson 5 - Part B: Triage + Route to Existing Specialists
==========================================================
Uses pre-created specialist agents (from Part A).
This is the production pattern -- agents created once, reused forever.
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

# Import specialist functions (needed for auto function calls)
sys.path.insert(0, "week1")
from lesson5_tools import (
    check_order_status,
    diagnose_technical_issue,
    process_billing_request,
)


async def main(user_message: str):
    credential = DefaultAzureCredential()

    # --- Load pre-created agent IDs ---
    with open("week1/agent_config.json", "r") as f:
        config = json.load(f)
    print(f"Loaded specialist agents from config")

    async with AgentsClient(
        endpoint=os.getenv("PROJECT_ENDPOINT"),
        credential=credential,
    ) as client:

        # --- Create Triage Agent (temporary, just for routing) ---
        def route_to_specialist(department: str, customer_message: str) -> str:
            """Route the customer to the appropriate specialist department."""
            return json.dumps({
                "routed_to": department,
                "message": customer_message,
            })

        triage_toolset = ToolSet()
        triage_toolset.add(FunctionTool({route_to_specialist}))
        client.enable_auto_function_calls({route_to_specialist})

        triage_agent = await client.create_agent(
            model=os.getenv("MODEL_DEPLOYMENT_NAME"),
            name="triage-agent",
            instructions="""You are a customer support triage agent for TechCorp.
            Your job is to understand the customer's issue and route to the right department.

            Use route_to_specialist with one of these departments:
            - "orders" -- for order tracking, delivery status, shipping questions
            - "technical" -- for product issues, troubleshooting, defects
            - "billing" -- for refunds, invoices, payment problems

            Always route. Do not try to answer yourself.""",
            toolset=triage_toolset,
        )
        print(f"Triage Agent created: {triage_agent.id}")

        # --- Step 1: Triage ---
        print(f"\n--- Customer: {user_message} ---\n")

        triage_run = await client.create_thread_and_process_run(
            agent_id=triage_agent.id,
            thread=AgentThreadCreationOptions(
                messages=[ThreadMessageOptions(role="user", content=user_message)]
            ),
        )

        triage_messages = client.messages.list(thread_id=triage_run.thread_id)
        routing = ""
        async for msg in triage_messages:
            if msg.role == "assistant":
                routing = msg.content[0].text.value
                print(f"Triage Agent: {routing}")
                break

        # --- Step 2: Route to existing specialist ---
        if "order" in routing.lower():
            specialist_id = config["order_agent_id"]
            specialist_tools = {check_order_status}
            print(">> Routed to: Order Specialist")
        elif "technical" in routing.lower() or "tech" in routing.lower():
            specialist_id = config["tech_agent_id"]
            specialist_tools = {diagnose_technical_issue}
            print(">> Routed to: Technical Specialist")
        elif "billing" in routing.lower() or "refund" in routing.lower():
            specialist_id = config["billing_agent_id"]
            specialist_tools = {process_billing_request}
            print(">> Routed to: Billing Specialist")
        else:
            specialist_id = config["tech_agent_id"]
            specialist_tools = {diagnose_technical_issue}
            print(">> Routed to: Technical Specialist (default)")

        client.enable_auto_function_calls(specialist_tools)

        # --- Step 3: Specialist handles request ---
        specialist_run = await client.create_thread_and_process_run(
            agent_id=specialist_id,
            thread=AgentThreadCreationOptions(
                messages=[ThreadMessageOptions(role="user", content=user_message)]
            ),
        )

        spec_messages = client.messages.list(thread_id=specialist_run.thread_id)
        async for msg in spec_messages:
            if msg.role == "assistant":
                print(f"\nSpecialist: {msg.content[0].text.value}")
                break

        # Only delete triage agent -- specialists stay alive
        await client.delete_agent(triage_agent.id)
        print("\nTriage agent deleted. Specialists still alive for next request.")

    await credential.close()


if __name__ == "__main__":
    user_input = input("You: ")
    asyncio.run(main(user_input))
