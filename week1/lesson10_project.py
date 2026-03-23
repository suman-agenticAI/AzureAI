"""
Lesson 10: End-to-End Support Agent System (Week 1 Project)
============================================================
Combines: Multi-agent, Function calling, File Search,
Code Interpreter, Streaming, Error handling, Tracing
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
    FileSearchTool,
    CodeInterpreterTool,
    FilePurpose,
    TruncationObject,
)
from azure.identity.aio import DefaultAzureCredential
from azure.core.exceptions import HttpResponseError

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, "week1")
load_dotenv()

from lesson10_project_tools import (
    get_order_status,
    check_return_eligibility,
    create_support_ticket,
)


# --- Retry utility (from Lesson 9) ---
async def run_with_retry(client, agent_id, user_message, max_retries=3):
    for attempt in range(1, max_retries + 1):
        try:
            run = await client.create_thread_and_process_run(
                agent_id=agent_id,
                thread=AgentThreadCreationOptions(
                    messages=[ThreadMessageOptions(role="user", content=user_message)]
                ),
                metadata={"channel": "cli-chat"},
            )
            if run.status == "failed":
                if attempt < max_retries:
                    await asyncio.sleep(attempt * 2)
                    continue
                return None, "Run failed after retries"
            return run, None
        except HttpResponseError as e:
            if e.status_code == 429 and attempt < max_retries:
                await asyncio.sleep(attempt * 5)
            elif e.status_code >= 500 and attempt < max_retries:
                await asyncio.sleep(attempt * 2)
            else:
                return None, str(e.message)
    return None, "Max retries exceeded"


async def get_response(client, thread_id):
    """Get latest assistant response from a thread."""
    messages = client.messages.list(thread_id=thread_id)
    async for msg in messages:
        if msg.role == "assistant":
            return msg.content[0].text.value
    return "No response generated."


async def main():
    credential = DefaultAzureCredential()

    async with AgentsClient(
        endpoint=os.getenv("PROJECT_ENDPOINT"),
        credential=credential,
    ) as client:

        print("=== TechCorp Support System ===")
        print("Setting up agents...\n")

        # --- 1. Create Order Specialist ---
        order_tools = {get_order_status, check_return_eligibility, create_support_ticket}
        order_toolset = ToolSet()
        order_toolset.add(FunctionTool(order_tools))
        client.enable_auto_function_calls(order_tools)

        order_agent = await client.create_agent(
            model=os.getenv("MODEL_DEPLOYMENT_NAME"),
            name="order-specialist",
            instructions="""You are an order specialist for TechCorp Electronics.
            Tools: get_order_status, check_return_eligibility, create_support_ticket
            Rules:
            - Always ask for order ID if not provided
            - For returns, check eligibility FIRST
            - Create tickets for issues you cannot resolve
            - Format currency in INR
            - Keep responses to 3-4 sentences""",
            toolset=order_toolset,
        )
        print(f"  Order Specialist ready: {order_agent.id}")

        # --- 2. Create Knowledge Specialist (File Search) ---
        file1 = await client.files.upload(
            file_path="week1/data/azure_agent_service_overview.txt",
            purpose=FilePurpose.AGENTS,
        )
        file2 = await client.files.upload(
            file_path="week1/data/azure_agent_service_whats_new.txt",
            purpose=FilePurpose.AGENTS,
        )
        vector_store = await client.vector_stores.create_and_poll(
            name="techcorp-knowledge-base",
            file_ids=[file1.id, file2.id],
        )

        knowledge_agent = await client.create_agent(
            model=os.getenv("MODEL_DEPLOYMENT_NAME"),
            name="knowledge-specialist",
            instructions="""You are a knowledge base specialist for TechCorp.
            Rules:
            - Answer ONLY from the documents provided
            - Cite which document the info came from
            - If not in documents, say "I don't have that information"
            - Keep responses concise""",
            tools=FileSearchTool().definitions,
            tool_resources={"file_search": {"vector_store_ids": [vector_store.id]}},
        )
        print(f"  Knowledge Specialist ready: {knowledge_agent.id}")

        # --- 3. Create Data Analyst (Code Interpreter) ---
        sales_file = await client.files.upload(
            file_path="week1/data/q1_sales_data.csv",
            purpose=FilePurpose.AGENTS,
        )

        analyst_agent = await client.create_agent(
            model=os.getenv("MODEL_DEPLOYMENT_NAME"),
            name="data-analyst",
            instructions="""You are a data analyst for TechCorp.
            Rules:
            - Analyze the uploaded sales data using Python
            - Give exact numbers, not approximations
            - Format currency in INR
            - Show key insights briefly""",
            tools=CodeInterpreterTool().definitions,
            tool_resources={"code_interpreter": {"file_ids": [sales_file.id]}},
        )
        print(f"  Data Analyst ready: {analyst_agent.id}")

        # --- 4. Create Triage Agent ---
        def route_to_specialist(department: str, customer_message: str) -> str:
            """Route customer to the right department."""
            return json.dumps({"routed_to": department, "message": customer_message})

        triage_toolset = ToolSet()
        triage_toolset.add(FunctionTool({route_to_specialist}))
        client.enable_auto_function_calls({route_to_specialist})

        triage_agent = await client.create_agent(
            model=os.getenv("MODEL_DEPLOYMENT_NAME"),
            name="triage-agent",
            instructions="""You are the triage agent for TechCorp support.
            Route every message to ONE department using route_to_specialist:
            - "orders" -- order status, delivery, returns, refunds, complaints
            - "knowledge" -- product info, company policies, how-to questions
            - "analyst" -- sales data, revenue reports, analytics questions
            Always route. Never answer directly.""",
            toolset=triage_toolset,
        )
        print(f"  Triage Agent ready: {triage_agent.id}")

        # --- Agent map ---
        agent_map = {
            "orders": {"id": order_agent.id, "tools": order_tools},
            "knowledge": {"id": knowledge_agent.id, "tools": None},
            "analyst": {"id": analyst_agent.id, "tools": None},
        }

        print("\n=== System Ready ===")
        print("Type your question. Type 'quit' to exit.\n")

        # --- Chat Loop ---
        while True:
            user_input = input("You: ")
            if user_input.lower() == "quit":
                break

            # Step 1: Triage
            client.enable_auto_function_calls({route_to_specialist})
            triage_run, error = await run_with_retry(client, triage_agent.id, user_input)
            if error:
                print(f"Agent: Sorry, there's a temporary issue. Please try again.\n")
                continue

            routing = await get_response(client, triage_run.thread_id)

            # Determine department
            department = "orders"  # default
            for dept in ["orders", "knowledge", "analyst"]:
                if dept in routing.lower():
                    department = dept
                    break

            print(f"  [Routed to: {department}]")

            # Step 2: Specialist handles it
            specialist = agent_map[department]
            if specialist["tools"]:
                client.enable_auto_function_calls(specialist["tools"])

            specialist_run, error = await run_with_retry(
                client, specialist["id"], user_input
            )

            if error:
                print(f"Agent: Sorry, our {department} team is temporarily unavailable. "
                      f"Please try again in a few minutes.\n")
                continue

            # Print response + token usage
            response = await get_response(client, specialist_run.thread_id)
            print(f"Agent: {response}")
            print(f"  [Tokens: {specialist_run.usage.total_tokens}]\n")

        # --- Cleanup ---
        print("\nCleaning up...")
        for agent in [triage_agent, order_agent, knowledge_agent, analyst_agent]:
            await client.delete_agent(agent.id)
        await client.vector_stores.delete(vector_store.id)
        for f in [file1, file2, sales_file]:
            await client.files.delete(f.id)
        print("All agents and resources deleted. Goodbye!")

    await credential.close()


if __name__ == "__main__":
    asyncio.run(main())
