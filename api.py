from fastapi import FastAPI, BackgroundTasks
import subprocess
import os

app = FastAPI(title="MANDATE Governance API")

@app.get("/")
def read_root():
    return {"message": "MANDATE Agent is active and governed by ArmorIQ."}

@app.get("/health")
def health_check():
    """Zop.dev and Kubernetes health check endpoint."""
    return {"status": "healthy"}

@app.post("/run-review")
def trigger_review(background_tasks: BackgroundTasks):
    """
    Endpoint to trigger a MANDATE code review manually or via webhook.
    Since Zop.dev might kill the request if it takes too long, we run it in the background.
    """
    def run_script():
        # Runs the local ungoverned or governed review depending on your choice
        # Here we just run the demo for demonstration on Zop.dev
        script_path = os.path.join(os.path.dirname(__file__), "demo", "run_governed.py")
        if os.path.exists(script_path):
            subprocess.run(["python", script_path], check=False)
            
    background_tasks.add_task(run_script)
    return {"status": "Review triggered in the background"}

if __name__ == "__main__":
    import uvicorn
    # When deployed, Zop.dev will look for the server on a specific port (usually 80 or 8080)
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
