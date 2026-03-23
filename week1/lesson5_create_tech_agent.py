"""
Lesson 5: Create Technical Specialist Agent
"""

import os
import sys
import json
import asyncio
from dotenv import load_dotenv
from azure.ai.agents.aio import AgentsClient
from azure.ai.agents.models import FunctionTool, ToolSet
from azure.identity.aio import DefaultAzureCredential

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, "week1")
load_dotenv()

from lesson5_tools import diagnose_technical_issue


async def main():
    credential = DefaultAzureCredential()

    async with AgentsClient(
        endpoint=os.getenv("PROJECT_ENDPOINT"),
        credential=credential,
    ) as client:

        toolset = ToolSet()
        toolset.add(FunctionTool({diagnose_technical_issue}))

        agent = await client.create_agent(
            model=os.getenv("MODEL_DEPLOYMENT_NAME"),
            name="tech-specialist",
            instructions="""You are a technical support specialist.
            - Use diagnose_technical_issue to troubleshoot problems
            - Provide step-by-step solutions
            - Mention severity level
            - Recommend service center if severity is High""",
            toolset=toolset,
        )
        print(f"Tech Agent created: {agent.id}")

        # Save to config
        config_path = "week1/agent_config.json"
        config = {}
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                config = json.load(f)
        config["tech_agent_id"] = agent.id
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
        print("Saved to agent_config.json")

    await credential.close()


if __name__ == "__main__":
    asyncio.run(main())
