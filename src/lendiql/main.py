"""Entry point for ``uvicorn`` — re-exports the FastAPI ``app``."""

from lendiql.app import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("lendiql.app:app", host="0.0.0.0", port=8000, reload=True)
