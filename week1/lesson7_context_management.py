"""
Lesson 7: Context Window Management + Prompt Engineering
========================================================
Shows how to control token usage and write effective prompts.
"""

import os
import sys
import asyncio
from dotenv import load_dotenv
from azure.ai.agents.aio import AgentsClient
from azure.ai.agents.models import (
    AgentThreadCreationOptions,
    ThreadMessageOptions,
    TruncationObject,
)
from azure.identity.aio import DefaultAzureCredential

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()


async def main():
    credential = DefaultAzureCredential()

    async with AgentsClient(
        endpoint=os.getenv("PROJECT_ENDPOINT"),
        credential=credential,
    ) as client:

        # --- Part A: Good vs Bad Prompt Engineering ---
        # BAD prompt: vague, no structure, no constraints
        bad_agent = await client.create_agent(
            model=os.getenv("MODEL_DEPLOYMENT_NAME"),
            name="bad-prompt-agent",
            instructions="You are a support agent. Help the customer.",
        )

        # GOOD prompt: specific role, rules, output format, constraints
        good_agent = await client.create_agent(
            model=os.getenv("MODEL_DEPLOYMENT_NAME"),
            name="good-prompt-agent",
            instructions="""You are a Level-1 support agent for TechCorp Electronics.

ROLE: Handle basic order and product queries. Escalate complex issues.

RULES:
- Answer in 2-3 sentences max
- Always include the order ID in your response if mentioned
- If you don't know, say "Let me escalate this" — never guess
- Never share internal pricing or margin data

OUTPUT FORMAT:
- Start with a one-line summary
- Follow with action items if any
- End with "Anything else I can help with?"

ESCALATION: If the issue involves refunds over 50000 INR, legal 
complaints, or data privacy, respond with "ESCALATE: [reason]"
""",
        )

        question = "Where is my order ORD-001? I've been waiting forever!"

        # Test BAD prompt
        bad_run = await client.create_thread_and_process_run(
            agent_id=bad_agent.id,
            thread=AgentThreadCreationOptions(
                messages=[ThreadMessageOptions(role="user", content=question)]
            ),
        )
        bad_messages = client.messages.list(thread_id=bad_run.thread_id)
        async for msg in bad_messages:
            if msg.role == "assistant":
                print(f"BAD prompt response:\n{msg.content[0].text.value}\n")
                break

        # Test GOOD prompt
        good_run = await client.create_thread_and_process_run(
            agent_id=good_agent.id,
            thread=AgentThreadCreationOptions(
                messages=[ThreadMessageOptions(role="user", content=question)]
            ),
        )
        good_messages = client.messages.list(thread_id=good_run.thread_id)
        async for msg in good_messages:
            if msg.role == "assistant":
                print(f"GOOD prompt response:\n{msg.content[0].text.value}\n")
                break

        # --- Part B: Token Budget Control ---
        budget_agent = await client.create_agent(
            model=os.getenv("MODEL_DEPLOYMENT_NAME"),
            name="budget-agent",
            instructions="You are a helpful assistant. Be concise.",
        )

        thread = await client.threads.create()

        # Simulate a long conversation — 10 messages
        for i in range(10):
            await client.messages.create(
                thread_id=thread.id,
                role="user",
                content=f"Message {i+1}: Tell me about product feature {i+1}",
            )

        # Run WITH token limits
        run = await client.runs.create_and_process(
            thread_id=thread.id,
            agent_id=budget_agent.id,
            # Truncation: only send last 4 messages to the LLM
            truncation_strategy=TruncationObject(
                type="last_messages",
                last_messages=4,
            ),
            # Token limits: cap how much the model can use
            max_prompt_tokens=2000,  # max input tokens
            max_completion_tokens=500,  # max output tokens
        )

        print("--- Token Budget Control ---")
        print(f"Status: {run.status}")
        print(f"Prompt tokens used: {run.usage.prompt_tokens}")
        print(f"Completion tokens used: {run.usage.completion_tokens}")
        print(f"Total tokens: {run.usage.total_tokens}")

        # Read response
        messages = client.messages.list(thread_id=thread.id)
        async for msg in messages:
            if msg.role == "assistant":
                print(f"\nAgent: {msg.content[0].text.value}")
                break

        # --- Cleanup ---
        for agent in [bad_agent, good_agent, budget_agent]:
            await client.delete_agent(agent.id)
        print("\nCleanup: All agents deleted")

    await credential.close()


if __name__ == "__main__":
    asyncio.run(main())
