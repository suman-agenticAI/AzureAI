"""
Lesson 1 - Part 1: Your First Azure AI Agent (Async)
=====================================================
A simple agent with no tools — proves your setup works.

Key concepts:
- AgentsClient (async): connects to Azure AI Agent Service
- Agent: the AI assistant with instructions (like AutoGen's AssistantAgent)
- Thread: a conversation session (Azure manages state — unlike AutoGen where YOU managed it)
- Run: executes the agent on a thread and waits for completion

Flow: Create Agent → Create Thread with Message → Run → Read Response → Cleanup
"""

import os
import asyncio
from dotenv import load_dotenv
from azure.ai.agents.aio import AgentsClient
from azure.ai.agents.models import AgentThreadCreationOptions, ThreadMessageOptions
from azure.identity.aio import DefaultAzureCredential

load_dotenv()


async def main(user_message: str):
    # --- Step 1: Connect to Azure AI Agent Service ---
    # DefaultAzureCredential tries multiple auth methods:
    # az login → environment vars → managed identity (in production)
    credential = DefaultAzureCredential()

    async with AgentsClient(
        endpoint=os.getenv("PROJECT_ENDPOINT"),
        credential=credential,
    ) as client:
        print("Step 1: Connected to Azure AI Agent Service")

        # --- Step 2: Create an Agent ---
        # Think of this as defining an employee with a job description.
        # The agent persists on Azure until you delete it.
        agent = await client.create_agent(
            model=os.getenv("MODEL_DEPLOYMENT_NAME"),
            name="support-greeter",
            instructions="""You are a customer support agent for TechCorp, an electronics company.
            - Be professional and helpful
            - If you don't know something, say so honestly
            - Keep responses concise (2-3 sentences max)""",
        )
        print(f"Step 2: Agent created — ID: {agent.id}")

        # --- Step 3: Create a Thread with a Message, and Run the Agent ---
        # In AutoGen: you create agents, add them to a team, then run.
        # Here: you create a thread (with messages) and run the agent on it — all in one call.
        run = await client.create_thread_and_process_run(
            agent_id=agent.id,
            thread=AgentThreadCreationOptions(
                messages=[
                    ThreadMessageOptions(
                        role="user",
                        content=user_message,
                    )
                ]
            ),
        )
        print(f"Step 3: Run completed — Status: {run.status}")

        # --- Step 4: Read the response ---
        messages = client.messages.list(thread_id=run.thread_id)
        async for msg in messages:
            role = "User" if msg.role == "user" else "Agent"
            print(f"\n{role}: {msg.content[0].text.value}")

        # --- Step 5: Cleanup ---
        await client.delete_agent(agent.id)
        print(f"\nCleanup: Agent deleted")

    await credential.close()


if __name__ == "__main__":
    user_input = input("You: ")
    asyncio.run(main(user_input))
