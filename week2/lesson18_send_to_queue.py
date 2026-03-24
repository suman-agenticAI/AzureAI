"""
Lesson 18 - Part 1: Send support requests to Service Bus queue
===============================================================
Simulates customers submitting support requests.
Messages go into the queue — agents will process them later.
"""

import os
import sys
import json
import asyncio
from dotenv import load_dotenv
from azure.servicebus.aio import ServiceBusClient
from azure.servicebus import ServiceBusMessage
from azure.servicebus.management import ServiceBusAdministrationClient

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()

QUEUE_NAME = "support-requests"


def create_queue_if_not_exists():
    """Create the queue if it doesn't exist."""
    admin_client = ServiceBusAdministrationClient.from_connection_string(
        os.getenv("SERVICE_BUS_CONNECTION")
    )
    try:
        admin_client.get_queue(QUEUE_NAME)
        print(f"Queue '{QUEUE_NAME}' already exists")
    except Exception:
        admin_client.create_queue(QUEUE_NAME)
        print(f"Queue '{QUEUE_NAME}' created")


async def main():
    # Create queue first
    create_queue_if_not_exists()

    # Sample support requests from different customers
    requests = [
        {
            "id": "REQ-001",
            "customer_id": "CUST-12345",
            "message": "Where is my order ORD-001?",
            "priority": "medium",
            "department": "orders",
        },
        {
            "id": "REQ-002",
            "customer_id": "CUST-67890",
            "message": "My laptop screen is flickering badly",
            "priority": "high",
            "department": "technical",
        },
        {
            "id": "REQ-003",
            "customer_id": "CUST-11111",
            "message": "I was overcharged on my last invoice",
            "priority": "high",
            "department": "billing",
        },
        {
            "id": "REQ-004",
            "customer_id": "CUST-22222",
            "message": "Can I return my order ORD-003?",
            "priority": "medium",
            "department": "orders",
        },
        {
            "id": "REQ-005",
            "customer_id": "CUST-33333",
            "message": "My laptop is not charging at all",
            "priority": "high",
            "department": "technical",
        },
    ]

    # Send all requests to the queue
    async with ServiceBusClient.from_connection_string(
        os.getenv("SERVICE_BUS_CONNECTION")
    ) as client:
        sender = client.get_queue_sender(queue_name=QUEUE_NAME)
        async with sender:
            for req in requests:
                message = ServiceBusMessage(
                    body=json.dumps(req),
                    subject=req["department"],
                    application_properties={
                        "customer_id": req["customer_id"],
                        "priority": req["priority"],
                    },
                )
                await sender.send_messages(message)
                print(f"  Sent: {req['id']} | {req['department']} | {req['message'][:40]}")

    print(f"\nAll {len(requests)} requests sent to queue '{QUEUE_NAME}'")


if __name__ == "__main__":
    asyncio.run(main())
