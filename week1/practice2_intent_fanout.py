"""
Practice 2: Intent Detection → Dynamic Fan-out
================================================
Step 1: Intent agent classifies customer message into multiple intents
Step 2: Only matching specialist agents run in parallel
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
    ResponseFormatJsonSchema,
    ResponseFormatJsonSchemaType,
)
from azure.identity.aio import DefaultAzureCredential

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()


# --- All available specialists ---
SPECIALISTS = {
    "sales": {
        "name": "sales-analyst",
        "instructions": """Analyze from a SALES perspective.
        - Upsell/cross-sell opportunities
        - Revenue impact
        - Next best offer
        Keep to 3-4 bullet points.""",
    },
    "support": {
        "name": "support-analyst",
        "instructions": """Analyze from a SUPPORT perspective.
        - Identify the technical issue
        - Satisfaction risk (Low/Medium/High)
        - Proactive actions to resolve
        Keep to 3-4 bullet points.""",
    },
    "competitive": {
        "name": "competitive-analyst",
        "instructions": """Analyze from a COMPETITIVE perspective.
        - Churn risk
        - What competitors would offer
        - Retention strategy
        Keep to 3-4 bullet points.""",
    },
    "billing": {
        "name": "billing-analyst",
        "instructions": """Analyze from a BILLING perspective.
        - Payment or refund actions needed
        - Financial risk
        - Resolution timeline
        Keep to 3-4 bullet points.""",
    },
    "legal": {
        "name": "legal-analyst",
        "instructions": """Analyze from a LEGAL/COMPLIANCE perspective.
        - Any legal risk in this scenario
        - Compliance concerns
        - Recommended actions to protect the company
        Keep to 3-4 bullet points.""",
    },
}


async def detect_intents(client, user_message):
    """Step 1: Intent agent returns structured JSON using response_format."""

    available_intents = list(SPECIALISTS.keys())

    # Define the schema — agent MUST return this exact structure
    intent_schema = ResponseFormatJsonSchema(
        name="intent_response",
        schema={
            "type": "object",
            "properties": {
                "intents": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": available_intents,
                    },
                },
                "reasoning": {
                    "type": "string",
                    "description": "Brief explanation of why these intents were detected",
                },
            },
            "required": ["intents", "reasoning"],
            "additionalProperties": False,
        },
    )

    intent_agent = await client.create_agent(
        model=os.getenv("MODEL_DEPLOYMENT_NAME"),
        name="intent-detector",
        instructions=f"""You are an intent classifier.
        Detect ALL relevant intents from the customer message.
        Available intents: {available_intents}
        A message can have MULTIPLE intents.""",
        response_format=ResponseFormatJsonSchemaType(json_schema=intent_schema),
    )

    run = await client.create_thread_and_process_run(
        agent_id=intent_agent.id,
        thread=AgentThreadCreationOptions(
            messages=[ThreadMessageOptions(role="user", content=user_message)]
        ),
    )

    # Response is guaranteed to be valid JSON matching our schema
    response = ""
    messages = client.messages.list(thread_id=run.thread_id)
    async for msg in messages:
        if msg.role == "assistant":
            response = msg.content[0].text.value
            break

    await client.delete_agent(intent_agent.id)

    # Parse structured JSON — no guessing, no keyword matching
    parsed = json.loads(response)
    print(f"Reasoning: {parsed['reasoning']}")

    # Filter only valid intents
    detected = [i for i in parsed["intents"] if i in SPECIALISTS]
    return detected


async def run_specialist(client, intent, config, user_message):
    """Run a single specialist agent."""
    agent = await client.create_agent(
        model=os.getenv("MODEL_DEPLOYMENT_NAME"),
        name=config["name"],
        instructions=config["instructions"],
    )

    run = await client.create_thread_and_process_run(
        agent_id=agent.id,
        thread=AgentThreadCreationOptions(
            messages=[ThreadMessageOptions(role="user", content=user_message)]
        ),
    )

    response = ""
    messages = client.messages.list(thread_id=run.thread_id)
    async for msg in messages:
        if msg.role == "assistant":
            response = msg.content[0].text.value
            break

    await client.delete_agent(agent.id)
    return intent, response


async def main():
    credential = DefaultAzureCredential()

    async with AgentsClient(
        endpoint=os.getenv("PROJECT_ENDPOINT"),
        credential=credential,
    ) as client:

        user_message = input("You: ")

        # Step 1: Detect intents
        print("\nDetecting intents...")
        intents = await detect_intents(client, user_message)
        print(f"Detected intents: {intents}")

        if not intents:
            print("No intents detected. Please rephrase.")
            await credential.close()
            return

        # Step 2: Run ONLY matching specialists in parallel
        print(f"Running {len(intents)} specialist(s) in parallel...\n")
        results = await asyncio.gather(
            *[
                run_specialist(client, intent, SPECIALISTS[intent], user_message)
                for intent in intents
            ]
        )

        # Step 3: Print results
        for intent, response in results:
            print(f"=== {intent.upper()} ===")
            print(response)
            print()

    await credential.close()


if __name__ == "__main__":
    asyncio.run(main())
