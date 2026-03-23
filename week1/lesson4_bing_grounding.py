"""
Lesson 4: Bing Grounding — Agent with Live Web Search
======================================================
Agent searches the internet in real-time to answer questions
with up-to-date information.

Real-world use case: Sales agent checks competitor pricing,
latest news, market trends — all live.
"""

import os
import sys
import asyncio
from dotenv import load_dotenv
from azure.ai.agents.aio import AgentsClient
from azure.ai.agents.models import (
    AgentThreadCreationOptions,
    ThreadMessageOptions,
    BingGroundingTool,
)
from azure.identity.aio import DefaultAzureCredential

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()

# Connection ID from .env — never hardcode Azure resource paths in code
BING_CONNECTION_ID = os.getenv("BING_CONNECTION_ID")


async def main(user_message: str):
    credential = DefaultAzureCredential()

    async with AgentsClient(
        endpoint=os.getenv("PROJECT_ENDPOINT"),
        credential=credential,
    ) as client:

        # --- Create Bing Grounding tool ---
        bing_tool = BingGroundingTool(connection_id=BING_CONNECTION_ID)

        # --- Create Agent with Bing ---
        agent = await client.create_agent(
            model=os.getenv("MODEL_DEPLOYMENT_NAME"),
            name="web-research-agent",
            instructions="""You are a market research agent for TechCorp Electronics.
            - Use Bing search to find current, real-time information
            - Always mention the source of your information
            - Compare data points when asked
            - Be factual — do not make up information
            - If search returns no results, say so clearly""",
            tools=bing_tool.definitions,
        )
        print(f"Agent created with Bing Grounding -- ID: {agent.id}")

        # --- Run ---
        run = await client.create_thread_and_process_run(
            agent_id=agent.id,
            thread=AgentThreadCreationOptions(
                messages=[ThreadMessageOptions(role="user", content=user_message)]
            ),
        )
        print(f"Run completed -- Status: {run.status}")

        # --- Read response ---
        messages = client.messages.list(thread_id=run.thread_id)
        async for msg in messages:
            if msg.role == "assistant":
                for content in msg.content:
                    if hasattr(content, "text"):
                        print(f"\nAgent: {content.text.value}")

        # --- Cleanup ---
        await client.delete_agent(agent.id)
        print("\nCleanup: Agent deleted")

    await credential.close()


if __name__ == "__main__":
    user_input = input("You: ")
    asyncio.run(main(user_input))
