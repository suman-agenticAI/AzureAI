"""
Lesson 5: Create Billing Specialist Agent
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

from lesson5_tools import process_billing_request


async def main():
    credential = DefaultAzureCredential()

    async with AgentsClient(
        endpoint=os.getenv("PROJECT_ENDPOINT"),
        credential=credential,
    ) as client:

        toolset = ToolSet()
        toolset.add(FunctionTool({process_billing_request}))

        agent = await client.create_agent(
            model=os.getenv("MODEL_DEPLOYMENT_NAME"),
            name="billing-specialist",
            instructions="""You are a billing specialist.
            - Use process_billing_request for refunds, invoices, payment issues
            - Always provide a reference number for tracking
            - Be empathetic about billing issues""",
            toolset=toolset,
        )
        print(f"Billing Agent created: {agent.id}")

        # Save to config
        config_path = "week1/agent_config.json"
        config = {}
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                config = json.load(f)
        config["billing_agent_id"] = agent.id
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
        print("Saved to agent_config.json")

    await credential.close()


if __name__ == "__main__":
    asyncio.run(main())
