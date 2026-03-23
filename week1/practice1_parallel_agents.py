"""
Practice 1: Dynamic Parallel Agents
====================================
Agents defined in a list. Runs all in parallel with asyncio.gather.
Add/remove agents without changing code.
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
)
from azure.identity.aio import DefaultAzureCredential

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()


# --- Define agents as a list (add/remove without changing code) ---
AGENT_CONFIG = [
    {
        "name": "sales-analyst",
        "instructions": """Analyze this customer scenario from a SALES perspective.
        - Identify upsell/cross-sell opportunities
        - Estimate customer lifetime value
        - Suggest next best offer
        Keep response to 3-4 bullet points.""",
    },
    {
        "name": "support-analyst",
        "instructions": """Analyze this customer scenario from a SUPPORT perspective.
        - Identify potential issues before they escalate
        - Rate customer satisfaction risk (Low/Medium/High)
        - Suggest proactive support actions
        Keep response to 3-4 bullet points.""",
    },
    {
        "name": "competitive-analyst",
        "instructions": """Analyze this customer scenario from a COMPETITIVE perspective.
        - Identify churn risk
        - What would competitors offer this customer?
        - How to retain this customer
        Keep response to 3-4 bullet points.""",
    },
]

CUSTOMER_SCENARIO = """Customer: Suman Rao, Enterprise account.
- Bought 50 laptops last quarter (ORD-001, total 42.5L INR)
- Support tickets: 3 in last month (screen issues)
- Contract renewal in 60 days
- Competitor (Dell) pitched them last week"""


async def run_agent(client, agent_config, scenario):
    """Create agent, run it, return result."""
    agent = await client.create_agent(
        model=os.getenv("MODEL_DEPLOYMENT_NAME"),
        name=agent_config["name"],
        instructions=agent_config["instructions"],
    )

    run = await client.create_thread_and_process_run(
        agent_id=agent.id,
        thread=AgentThreadCreationOptions(
            messages=[ThreadMessageOptions(role="user", content=scenario)]
        ),
    )

    # Get response
    response = ""
    messages = client.messages.list(thread_id=run.thread_id)
    async for msg in messages:
        if msg.role == "assistant":
            response = msg.content[0].text.value
            break

    await client.delete_agent(agent.id)
    return agent_config["name"], response


async def main():
    credential = DefaultAzureCredential()

    async with AgentsClient(
        endpoint=os.getenv("PROJECT_ENDPOINT"),
        credential=credential,
    ) as client:

        # Run ALL agents in parallel -- works for any list size
        results = await asyncio.gather(
            *[run_agent(client, config, CUSTOMER_SCENARIO) for config in AGENT_CONFIG]
        )

        # Print results
        for name, response in results:
            print(f"\n=== {name.upper()} ===")
            print(response)

    await credential.close()


if __name__ == "__main__":
    asyncio.run(main())
