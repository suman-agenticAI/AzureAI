"""
Lesson 10 - Project Tools: Shared functions for the support system
"""

import json


def get_order_status(order_id: str) -> str:
    """Check the delivery status of a customer order."""
    orders = {
        "ORD-001": {"status": "Shipped", "delivery": "March 25, 2026", "carrier": "BlueDart", "amount": 85000},
        "ORD-002": {"status": "Processing", "delivery": "March 28, 2026", "carrier": "Pending", "amount": 65000},
        "ORD-003": {"status": "Delivered", "delivery": "March 20, 2026", "carrier": "DTDC", "amount": 25000},
        "ORD-004": {"status": "Cancelled", "delivery": "N/A", "carrier": "N/A", "amount": 150000},
        "ORD-005": {"status": "Shipped", "delivery": "March 26, 2026", "carrier": "Delhivery", "amount": 43500},
    }
    order = orders.get(order_id)
    if order:
        return json.dumps(order)
    return json.dumps({"error": f"Order {order_id} not found"})


def check_return_eligibility(order_id: str) -> str:
    """Check if an order is eligible for return."""
    eligibility = {
        "ORD-001": {"eligible": True, "reason": "Within 30-day window", "deadline": "April 24, 2026"},
        "ORD-002": {"eligible": False, "reason": "Order not yet delivered"},
        "ORD-003": {"eligible": True, "reason": "Within 30-day window", "deadline": "April 19, 2026"},
        "ORD-004": {"eligible": False, "reason": "Order was cancelled"},
        "ORD-005": {"eligible": True, "reason": "Within 30-day window", "deadline": "April 25, 2026"},
    }
    result = eligibility.get(order_id)
    if result:
        return json.dumps(result)
    return json.dumps({"error": f"Order {order_id} not found"})


def create_support_ticket(customer_name: str, issue: str, priority: str = "medium") -> str:
    """Create a support ticket for issues needing human follow-up."""
    ticket_id = "TKT-" + str(abs(hash(customer_name + issue)) % 100000)
    return json.dumps({
        "ticket_id": ticket_id,
        "status": "Created",
        "priority": priority,
        "message": f"Ticket {ticket_id} created for {customer_name}. "
                   f"Priority: {priority}. Our team will respond within "
                   f"{'4 hours' if priority == 'high' else '24 hours'}.",
    })
