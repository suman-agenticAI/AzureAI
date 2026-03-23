"""
Lesson 6: Streaming — Real-time token-by-token responses
"""

import os
import sys
import asyncio
from dotenv import load_dotenv
from azure.ai.agents.aio import AgentsClient
from azure.ai.agents.models import ThreadMessageOptions
from azure.identity.aio import DefaultAzureCredential

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()


async def main(user_message: str):
    credential = DefaultAzureCredential()

    async with AgentsClient(
        endpoint=os.getenv("PROJECT_ENDPOINT"),
        credential=credential,
    ) as client:

        agent = await client.create_agent(
            model=os.getenv("MODEL_DEPLOYMENT_NAME"),
            name="streaming-agent",
            instructions="""You are a helpful assistant for TechCorp.
            Give detailed, thorough answers so the streaming effect is visible.""",
        )

        # --- Step 1: Create thread + add message ---
        thread = await client.threads.create()
        await client.messages.create(
            thread_id=thread.id,
            role="user",
            content=user_message,
        )

        # --- Step 2: Stream the response ---
        print("\nAgent: ", end="", flush=True)
        async with await client.runs.stream(
            thread_id=thread.id,
            agent_id=agent.id,
        ) as stream:
            async for event in stream:
                # event is a tuple: (event_type, event_data)
                # "thread.message.delta" events contain the streaming text
                if event[0] == "thread.message.delta":
                    delta = event[1].delta
                    if delta and delta.content:
                        for content in delta.content:
                            if hasattr(content, "text") and content.text:
                                print(content.text.value, end="", flush=True)
        print()

        # --- Cleanup ---
        await client.delete_agent(agent.id)
        print("\nCleanup: Agent deleted")

    await credential.close()


if __name__ == "__main__":
    user_input = input("You: ")
    asyncio.run(main(user_input))
