import azure.functions as func
import json

app = func.FunctionApp()


@app.route(route="hello", methods=["GET", "POST"])
def hello(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET  /api/hello?name=Suman
    POST /api/hello  {"name": "Suman"}
    """
    name = req.params.get("name")

    if not name:
        try:
            body = req.get_json()
            name = body.get("name")
        except:
            pass

    if name:
        return func.HttpResponse(
            json.dumps({"message": f"Hello, {name}! Your Azure Function is working."}),
            mimetype="application/json",
        )
    else:
        return func.HttpResponse(
            json.dumps({"message": "Hello! Pass a name in query or body."}),
            mimetype="application/json",
        )
