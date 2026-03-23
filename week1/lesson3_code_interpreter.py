import os
import sys
import asyncio
from dotenv import load_dotenv
from azure.ai.agents.aio import AgentsClient
from azure.ai.agents.models import (
    AgentThreadCreationOptions,
    ThreadMessageOptions,
    CodeInterpreterTool,
    FilePurpose,
)
from azure.identity.aio import DefaultAzureCredential

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()


async def main(user_message: str):
    credential = DefaultAzureCredential()

    async with AgentsClient(
        endpoint=os.getenv("PROJECT_ENDPOINT"),
        credential=credential,
    ) as client:

        # --- Upload the sales data CSV ---
        sales_file = await client.files.upload(
            file_path="week1/data/q1_sales_data.csv",
            purpose=FilePurpose.AGENTS,
        )
        print(f"File uploaded: {sales_file.id}")

        # --- Create Agent with Code Interpreter + the file ---
        agent = await client.create_agent(
            model=os.getenv("MODEL_DEPLOYMENT_NAME"),
            name="data-analyst-agent",
            instructions="""You are a data analyst for TechCorp.
            - Analyze the uploaded sales data using Python code
            - Always show the code you run
            - Give exact numbers, not approximations
            - When comparing, show percentage differences
            - Format currency in Indian Rupees""",
            tools=CodeInterpreterTool().definitions,
            tool_resources={"code_interpreter": {"file_ids": [sales_file.id]}},
        )
        print(f"Agent created with Code Interpreter -- ID: {agent.id}")

        # --- Run ---
        run = await client.create_thread_and_process_run(
            agent_id=agent.id,
            thread=AgentThreadCreationOptions(
                messages=[ThreadMessageOptions(role="user", content=user_message)]
            ),
        )
        print(f"Run completed -- Status: {run.status}")

        # --- Read response (can have text + charts) ---
        messages = client.messages.list(thread_id=run.thread_id)
        async for msg in messages:
            if msg.role == "assistant":
                for content in msg.content:
                    if hasattr(content, "text"):
                        print(f"\nAgent: {content.text.value}")
                    elif hasattr(content, "image_file"):
                        print(
                            f"\n[Chart generated -- file ID: {content.image_file.file_id}]"
                        )

        # --- Cleanup ---
        await client.delete_agent(agent.id)
        await client.files.delete(sales_file.id)
        print("\nCleanup: Agent and file deleted")

    await credential.close()


if __name__ == "__main__":
    user_input = input("You: ")
    asyncio.run(main(user_input))
