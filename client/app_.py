from fastapi import FastAPI
from pydantic import BaseModel
from client.router import handle_query

app = FastAPI()

class QueryRequest(BaseModel):
    query: str

@app.post("/query")
def query_endpoint(req: QueryRequest):
    return handle_query(req.query)
