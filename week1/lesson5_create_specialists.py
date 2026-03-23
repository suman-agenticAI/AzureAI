"""
Lesson 5 - Part A: Create Specialist Agents (run once)
======================================================
Creates 3 specialist agents on Azure and saves their IDs.
These agents persist — you don't need to create them every time.
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
load_dotenv()


# --- Specialist Functions ---

def check_order_status(order_id: str) -> str:
    """Check the delivery status of a customer order."""
    orders = {
        "ORD-001": {"status": "Shipped", "delivery": "March 25, 2026", "carrier": "BlueDart"},
        "ORD-002": {"status": "Processing", "delivery": "March 28, 2026", "carrier": "Pending"},
        "ORD-003": {"status": "Delivered", "delivery": "March 20, 2026", "carrier": "DTDC"},
    }
    order = orders.get(order_id)
    if order:
        return json.dumps(order)
    return json.dumps({"error": f"Order {order_id} not found"})


def diagnose_technical_issue(product: str, issue: str) -> str:
    """Diagnose a technical issue and provide troubleshooting steps."""
    solutions = {
        "screen_flickering": {
            "diagnosis": "Display driver issue or hardware fault",
            "steps": [
                "1. Update graphics drivers from Device Manager",
                "2. Check display cable connection",
                "3. Test with external monitor",
                "4. If persists, likely hardware -- needs service center visit",
            ],
            "severity": "Medium",
        },
        "slow_performance": {
            "diagnosis": "Resource bottleneck",
            "steps": [
                "1. Check Task Manager for high CPU/RAM usage",
                "2. Run disk cleanup and disable startup programs",
                "3. Check for malware with Windows Defender scan",
                "4. Consider RAM upgrade if consistently above 90%",
            ],
            "severity": "Low",
        },
        "not_charging": {
            "diagnosis": "Power delivery issue",
            "steps": [
                "1. Try a different power outlet",
                "2. Check charger cable for damage",
                "3. Reset battery: hold power button 30 seconds",
                "4. If no improvement, charger or battery replacement needed",
            ],
            "severity": "High",
        },
    }
    for key, solution in solutions.items():
        if key.replace("_", " ") in issue.lower() or any(
            word in issue.lower() for word in key.split("_")
        ):
            return json.dumps(solution)
    return json.dumps({
        "diagnosis": "Unknown issue",
        "steps": ["Please describe the issue in more detail or visit a service center"],
        "severity": "Unknown",
    })


def process_billing_request(request_type: str, order_id: str = "", amount: str = "") -> str:
    """Handle billing requests like refunds, invoice copies, payment issues."""
    if request_type == "refund":
        return json.dumps({
            "status": "Refund initiated",
            "reference": f"REF-{hash(order_id) % 100000}",
            "timeline": "5-7 business days",
            "amount": amount or "Full order amount",
        })
    elif request_type == "invoice":
        return json.dumps({
            "status": "Invoice sent",
            "message": f"Invoice for {order_id} has been sent to your registered email",
        })
    else:
        return json.dumps({
            "status": "Escalated",
            "message": "Your billing query has been forwarded to the finance team",
        })


async def main():
    credential = DefaultAzureCredential()

    async with AgentsClient(
        endpoint=os.getenv("PROJECT_ENDPOINT"),
        credential=credential,
    ) as client:

        # --- Create Order Specialist ---
        order_toolset = ToolSet()
        order_toolset.add(FunctionTool({check_order_status}))
        order_agent = await client.create_agent(
            model=os.getenv("MODEL_DEPLOYMENT_NAME"),
            name="order-specialist",
            instructions="""You are an order tracking specialist.
            - Use check_order_status to look up orders
            - Provide delivery dates and carrier info
            - Be concise and helpful""",
            toolset=order_toolset,
        )
        print(f"Order Agent created: {order_agent.id}")

        # --- Create Technical Specialist ---
        tech_toolset = ToolSet()
        tech_toolset.add(FunctionTool({diagnose_technical_issue}))
        tech_agent = await client.create_agent(
            model=os.getenv("MODEL_DEPLOYMENT_NAME"),
            name="tech-specialist",
            instructions="""You are a technical support specialist.
            - Use diagnose_technical_issue to troubleshoot problems
            - Provide step-by-step solutions
            - Mention severity level
            - Recommend service center if severity is High""",
            toolset=tech_toolset,
        )
        print(f"Tech Agent created: {tech_agent.id}")

        # --- Create Billing Specialist ---
        billing_toolset = ToolSet()
        billing_toolset.add(FunctionTool({process_billing_request}))
        billing_agent = await client.create_agent(
            model=os.getenv("MODEL_DEPLOYMENT_NAME"),
            name="billing-specialist",
            instructions="""You are a billing specialist.
            - Use process_billing_request for refunds, invoices, payment issues
            - Always provide a reference number for tracking
            - Be empathetic about billing issues""",
            toolset=billing_toolset,
        )
        print(f"Billing Agent created: {billing_agent.id}")

        # --- Save IDs to config file ---
        agent_config = {
            "order_agent_id": order_agent.id,
            "tech_agent_id": tech_agent.id,
            "billing_agent_id": billing_agent.id,
        }
        with open("week1/agent_config.json", "w") as f:
            json.dump(agent_config, f, indent=2)

        print(f"\nAgent IDs saved to week1/agent_config.json")
        print("These agents are now LIVE on Azure -- reuse them anytime.")

    await credential.close()


if __name__ == "__main__":
    asyncio.run(main())
