import os
import sys
import asyncio

# Fix Windows Unicode printing
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
from azure.ai.agents.aio import AgentsClient
from azure.ai.agents.models import (
    AgentThreadCreationOptions,
    ThreadMessageOptions,
    FileSearchTool,
    FilePurpose,
)
from azure.identity.aio import DefaultAzureCredential

load_dotenv()


async def main(user_message: str):
    credential = DefaultAzureCredential()

    async with AgentsClient(
        endpoint=os.getenv("PROJECT_ENDPOINT"),
        credential=credential,
    ) as client:

        # --- Step 1: Upload files ---
        # These get uploaded to Azure's managed storage
        file1 = await client.files.upload(
            file_path="week1/data/azure_agent_service_overview.txt",
            purpose=FilePurpose.AGENTS,
        )
        file2 = await client.files.upload(
            file_path="week1/data/azure_agent_service_whats_new.txt",
            purpose=FilePurpose.AGENTS,
        )
        print(f"Files uploaded: {file1.id}, {file2.id}")

        # --- Step 2: Create a Vector Store ---
        # Azure chunks your files, creates embeddings, stores vectors
        # All automatic — no chunking strategy or embedding model to choose
        vector_store = await client.vector_stores.create_and_poll(
            name="azure-docs-store",
            file_ids=[file1.id, file2.id],
        )
        print(
            f"Vector store created: {vector_store.id} ({vector_store.file_counts.completed} files indexed)"
        )

        # --- Step 3: Create Agent with File Search tool ---
        agent = await client.create_agent(
            model=os.getenv("MODEL_DEPLOYMENT_NAME"),
            name="docs-search-agent",
            instructions="""You are an Azure AI documentation expert.
            - Answer questions using ONLY the documents provided via file search
            - Always cite which document the information came from
            - If the answer is not in the documents, say so clearly
            - Be concise and accurate""",
            tools=FileSearchTool().definitions,
            tool_resources={"file_search": {"vector_store_ids": [vector_store.id]}},
        )
        print(f"Agent created with File Search -- ID: {agent.id}")

        # --- Step 4: Run ---
        run = await client.create_thread_and_process_run(
            agent_id=agent.id,
            thread=AgentThreadCreationOptions(
                messages=[ThreadMessageOptions(role="user", content=user_message)]
            ),
        )
        print(f"Run completed -- Status: {run.status}")

        # --- Step 5: Read response ---
        messages = client.messages.list(thread_id=run.thread_id)
        async for msg in messages:
            if msg.role == "assistant":
                print(f"\nAgent: {msg.content[0].text.value}")

        # --- Cleanup ---
        await client.delete_agent(agent.id)
        await client.vector_stores.delete(vector_store.id)
        await client.files.delete(file1.id)
        await client.files.delete(file2.id)
        print("\nCleanup: Agent, vector store, and files deleted")

    await credential.close()


if __name__ == "__main__":
    user_input = input("You: ")
    asyncio.run(main(user_input))
