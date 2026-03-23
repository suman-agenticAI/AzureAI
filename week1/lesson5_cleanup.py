"""
Lesson 5 - Part C: Cleanup Specialist Agents
=============================================
Run this when you're done with lesson 5 to delete all agents.
"""

import os
import sys
import json
import asyncio
from dotenv import load_dotenv
from azure.ai.agents.aio import AgentsClient
from azure.identity.aio import DefaultAzureCredential

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()


async def main():
    credential = DefaultAzureCredential()

    with open("week1/agent_config.json", "r") as f:
        config = json.load(f)

    async with AgentsClient(
        endpoint=os.getenv("PROJECT_ENDPOINT"),
        credential=credential,
    ) as client:
        for name, agent_id in config.items():
            await client.delete_agent(agent_id)
            print(f"Deleted {name}: {agent_id}")

    await credential.close()

    # Remove config file
    os.remove("week1/agent_config.json")
    print("\nAll specialist agents deleted. Config removed.")


if __name__ == "__main__":
    asyncio.run(main())
