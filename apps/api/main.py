"""Start the REST API and the team MCP server. Same as `uvicorn api:app --reload`."""
import uvicorn

if __name__ == "__main__":
    uvicorn.run("api:app", reload=True)
