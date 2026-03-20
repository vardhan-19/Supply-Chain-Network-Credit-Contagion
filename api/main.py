from fastapi import FastAPI

# --- Initializing the FastAPI Application Skeleton ---
# Goal: Create a foundational web API structure to host health-checks and future endpoints.

app = FastAPI(title="Supply Chain Network Credit Contagion API")

@app.get("/")
def read_root():
    """
    Health check endpoint.
    Returns a simple JSON status object to verify the API is running correctly.
    """
    return {
        "status": "running",
        "message": "Supply Chain Contagion API",
        "version": "0.1.0"
    }

# How to run the server:
# uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
