"""
Lesson 17: Memory Service — Azure Functions API
=================================================
Serverless API for agent memory. Any agent (any language) can call these endpoints.

Endpoints:
  POST /api/save-turn    — save user + agent message pair
  POST /api/save-run     — save agent run log
  GET  /api/history/{user_id}  — get past conversations
  GET  /api/runs/failed  — get failed runs
  GET  /api/runs/tokens  — get token usage per agent
"""

import os
import json
import logging
from datetime import datetime, timezone
import azure.functions as func
from azure.cosmos import CosmosClient, PartitionKey

app = func.FunctionApp()

# --- Cosmos DB connection (reused across all function calls) ---
cosmos_client = None
conversations_container = None
run_logs_container = None


def get_cosmos():
    """Lazy init Cosmos DB connection — reused across invocations."""
    global cosmos_client, conversations_container, run_logs_container
    if cosmos_client is None:
        cosmos_client = CosmosClient(
            url=os.getenv("COSMOS_ENDPOINT"),
            credential=os.getenv("COSMOS_KEY"),
        )
        db = cosmos_client.create_database_if_not_exists("agent-memory")
        conversations_container = db.create_container_if_not_exists(
            id="conversations",
            partition_key=PartitionKey(path="/user_id"),
        )
        run_logs_container = db.create_container_if_not_exists(
            id="run-logs",
            partition_key=PartitionKey(path="/agent"),
        )
    return conversations_container, run_logs_container


# --- Endpoint 1: Save a conversation turn ---
@app.route(route="save-turn", methods=["POST"])
def save_turn(req: func.HttpRequest) -> func.HttpResponse:
    """
    POST /api/save-turn
    Body: {"user_id": "...", "session_id": "...", "user_message": "...", "agent_response": "..."}
    """
    try:
        body = req.get_json()
        conversations, _ = get_cosmos()

        now = datetime.now(timezone.utc)

        # Save user message
        conversations.upsert_item({
            "id": f"msg-{now.strftime('%Y%m%d%H%M%S%f')}-user",
            "user_id": body["user_id"],
            "session_id": body["session_id"],
            "role": "user",
            "content": body["user_message"],
            "timestamp": now.isoformat(),
        })

        # Save agent response
        conversations.upsert_item({
            "id": f"msg-{now.strftime('%Y%m%d%H%M%S%f')}-agent",
            "user_id": body["user_id"],
            "session_id": body["session_id"],
            "role": "assistant",
            "content": body["agent_response"],
            "timestamp": now.isoformat(),
        })

        return func.HttpResponse(
            json.dumps({"status": "saved", "messages": 2}),
            mimetype="application/json",
        )
    except Exception as e:
        logging.error(f"save-turn error: {e}")
        return func.HttpResponse(json.dumps({"error": str(e)}), status_code=500)


# --- Endpoint 2: Save an agent run log ---
@app.route(route="save-run", methods=["POST"])
def save_run(req: func.HttpRequest) -> func.HttpResponse:
    """
    POST /api/save-run
    Body: {"agent": "...", "user_id": "...", "query": "...", "response": "...",
           "tokens_used": 0, "latency_ms": 0, "status": "success"}
    """
    try:
        body = req.get_json()
        _, run_logs = get_cosmos()

        now = datetime.now(timezone.utc)
        body["id"] = f"run-{now.strftime('%Y%m%d%H%M%S%f')}"
        body["timestamp"] = now.isoformat()

        run_logs.upsert_item(body)

        return func.HttpResponse(
            json.dumps({"status": "saved", "run_id": body["id"]}),
            mimetype="application/json",
        )
    except Exception as e:
        logging.error(f"save-run error: {e}")
        return func.HttpResponse(json.dumps({"error": str(e)}), status_code=500)


# --- Endpoint 3: Get conversation history ---
@app.route(route="history/{user_id}", methods=["GET"])
def get_history(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/history/CUST-12345?limit=10&session_id=sess-abc
    """
    try:
        user_id = req.route_params.get("user_id")
        limit = int(req.params.get("limit", "10"))
        session_id = req.params.get("session_id")

        conversations, _ = get_cosmos()

        if session_id:
            query = (
                f"SELECT TOP {limit} * FROM c "
                f"WHERE c.user_id = @user_id AND c.session_id = @session_id "
                f"ORDER BY c.timestamp DESC"
            )
            params = [
                {"name": "@user_id", "value": user_id},
                {"name": "@session_id", "value": session_id},
            ]
        else:
            query = (
                f"SELECT TOP {limit} * FROM c "
                f"WHERE c.user_id = @user_id "
                f"ORDER BY c.timestamp DESC"
            )
            params = [{"name": "@user_id", "value": user_id}]

        items = list(conversations.query_items(
            query=query,
            parameters=params,
            partition_key=user_id,
        ))
        items.reverse()

        return func.HttpResponse(
            json.dumps(items, default=str),
            mimetype="application/json",
        )
    except Exception as e:
        logging.error(f"get-history error: {e}")
        return func.HttpResponse(json.dumps({"error": str(e)}), status_code=500)


# --- Endpoint 4: Get failed runs ---
@app.route(route="runs/failed", methods=["GET"])
def get_failed_runs(req: func.HttpRequest) -> func.HttpResponse:
    """GET /api/runs/failed?agent=order-specialist"""
    try:
        _, run_logs = get_cosmos()
        agent = req.params.get("agent")

        if agent:
            query = "SELECT * FROM c WHERE c.status = 'failed' AND c.agent = @agent"
            params = [{"name": "@agent", "value": agent}]
        else:
            query = "SELECT * FROM c WHERE c.status = 'failed'"
            params = []

        items = list(run_logs.query_items(
            query=query,
            parameters=params,
            enable_cross_partition_query=True,
        ))

        return func.HttpResponse(
            json.dumps(items, default=str),
            mimetype="application/json",
        )
    except Exception as e:
        logging.error(f"get-failed-runs error: {e}")
        return func.HttpResponse(json.dumps({"error": str(e)}), status_code=500)


# --- Endpoint 5: Get token usage per agent ---
@app.route(route="runs/tokens", methods=["GET"])
def get_token_usage(req: func.HttpRequest) -> func.HttpResponse:
    """GET /api/runs/tokens"""
    try:
        _, run_logs = get_cosmos()

        query = "SELECT c.agent, SUM(c.tokens_used) as total_tokens FROM c GROUP BY c.agent"
        items = list(run_logs.query_items(
            query=query,
            enable_cross_partition_query=True,
        ))

        return func.HttpResponse(
            json.dumps(items, default=str),
            mimetype="application/json",
        )
    except Exception as e:
        logging.error(f"get-token-usage error: {e}")
        return func.HttpResponse(json.dumps({"error": str(e)}), status_code=500)
