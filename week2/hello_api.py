"""
Quick test: FastAPI endpoint — test from Postman
Run: uvicorn week2.hello_api:app --reload
URL: http://localhost:8000
"""

from fastapi import FastAPI

app = FastAPI()


@app.get("/api/hello")
def hello_get(name: str = "World"):
    return {"message": f"Hello, {name}! Your API is working."}


@app.post("/api/hello")
def hello_post(body: dict):
    name = body.get("name", "World")
    return {"message": f"Hello, {name}! Your API is working."}
