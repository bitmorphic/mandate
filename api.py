"""
MANDATE — API Server for Zop.dev Deployment

This FastAPI server acts as a GitHub Webhook receiver.
When a developer pushes code or opens a Pull Request,
GitHub sends a POST request here, and MANDATE runs
the full governed code review on the real repository.
"""

from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import HTMLResponse
import subprocess
import tempfile
import shutil
import os
import sys
import json
import time
import logging

# Configure logging so Zop.dev can see all output
logging.basicConfig(level=logging.INFO, stream=sys.stdout, format="%(asctime)s | %(message)s")
logger = logging.getLogger("mandate")

app = FastAPI(title="MANDATE Governance API")

@app.on_event("startup")
async def startup():
    logger.info("🚀 MANDATE server started and ready to receive webhooks")

# Store recent review results for the dashboard
recent_reviews = []


@app.get("/", response_class=HTMLResponse)
def dashboard():
    """Landing page showing MANDATE status and recent reviews."""
    reviews_html = ""
    for review in reversed(recent_reviews[-10:]):
        status_icon = "🛡️" if review.get("blocked", 0) > 0 else "✅"
        reviews_html += f"""
        <div style="background:#1a1a2e; border:1px solid #333; border-radius:8px; padding:16px; margin:8px 0;">
            <strong>{status_icon} {review.get('repo', 'unknown')}</strong>
            <span style="color:#888; margin-left:12px;">{review.get('branch', '')}</span>
            <br/>
            <span style="color:#aaa; font-size:13px;">
                Findings: {review.get('findings', 0)} |
                Blocked writes: {review.get('blocked', 0)} |
                {review.get('time', '')}
            </span>
        </div>
        """

    if not reviews_html:
        reviews_html = '<p style="color:#888;">No reviews yet. Push code to a connected repo to trigger a review.</p>'

    return f"""
    <html>
    <head><title>MANDATE — Governed AI</title></head>
    <body style="background:#0d1117; color:#e6edf3; font-family:system-ui,sans-serif; max-width:800px; margin:40px auto; padding:0 20px;">
        <pre style="color:#f97316; font-size:11px; line-height:1.2;">
  ███╗   ███╗ █████╗ ███╗   ██╗██████╗  █████╗ ████████╗███████╗
  ████╗ ████║██╔══██╗████╗  ██║██╔══██╗██╔══██╗╚══██╔══╝██╔════╝
  ██╔████╔██║███████║██╔██╗ ██║██║  ██║███████║   ██║   █████╗
  ██║╚██╔╝██║██╔══██║██║╚██╗██║██║  ██║██╔══██║   ██║   ██╔══╝
  ██║ ╚═╝ ██║██║  ██║██║ ╚████║██████╔╝██║  ██║   ██║   ███████╗
  ╚═╝     ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝╚═════╝ ╚═╝  ╚═╝   ╚═╝   ╚══════╝
        </pre>
        <h2>Autonomous AI. Governed by Authority.</h2>
        <p style="color:#aaa;">Powered by <strong style="color:#f97316;">ArmorIQ SDK</strong> — Cryptographic Intent Enforcement</p>

        <div style="background:#161b22; border:1px solid #30363d; border-radius:8px; padding:20px; margin:20px 0;">
            <h3>🟢 Server Status: Active</h3>
            <p style="color:#aaa;">Webhook endpoint: <code style="background:#0d1117; padding:4px 8px; border-radius:4px;">POST /webhook</code></p>
            <p style="color:#aaa;">Health check: <code style="background:#0d1117; padding:4px 8px; border-radius:4px;">GET /health</code></p>
        </div>

        <h3>Recent Reviews</h3>
        {reviews_html}
    </body>
    </html>
    """


@app.get("/health")
def health_check():
    """Zop.dev and Kubernetes health check endpoint."""
    return {"status": "healthy", "service": "mandate", "governance": "armoriq"}


@app.post("/webhook")
async def github_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Receives GitHub webhook events (push or pull_request).
    Clones the real repository and runs the full MANDATE governed review.
    """
    try:
        payload = await request.json()
    except Exception:
        return {"error": "Invalid JSON payload"}

    # Extract repository info from the GitHub webhook payload
    repo_info = payload.get("repository", {})
    clone_url = repo_info.get("clone_url", "")
    repo_name = repo_info.get("full_name", "unknown/unknown")
    default_branch = repo_info.get("default_branch", "main")

    # Determine the branch that was pushed or the PR base
    ref = payload.get("ref", "")  # e.g., "refs/heads/feature-branch"
    branch = ref.replace("refs/heads/", "") if ref else default_branch

    if not clone_url:
        return {"error": "No clone_url found in webhook payload"}

    print(f"\n{'='*60}")
    print(f"🔔 WEBHOOK RECEIVED: {repo_name}")
    print(f"   Branch: {branch}")
    print(f"   Clone URL: {clone_url}")
    print(f"{'='*60}\n")

    # Run the review in the background so we respond to GitHub quickly
    background_tasks.add_task(
        run_real_review,
        clone_url=clone_url,
        repo_name=repo_name,
        branch=branch,
        default_branch=default_branch,
    )

    return {
        "status": "accepted",
        "message": f"MANDATE review triggered for {repo_name}",
        "branch": branch,
    }


@app.post("/run-review")
async def manual_review(request: Request, background_tasks: BackgroundTasks):
    """
    Manually trigger a review by providing a repo URL.
    POST body: {"clone_url": "https://github.com/user/repo.git", "branch": "main"}
    """
    try:
        body = await request.json()
    except Exception:
        return {"error": "Invalid JSON. Send: {\"clone_url\": \"...\", \"branch\": \"main\"}"}

    clone_url = body.get("clone_url", "")
    branch = body.get("branch", "main")
    repo_name = clone_url.split("/")[-1].replace(".git", "") if clone_url else "unknown"

    if not clone_url:
        return {"error": "clone_url is required"}

    background_tasks.add_task(
        run_real_review,
        clone_url=clone_url,
        repo_name=repo_name,
        branch=branch,
        default_branch=branch,
    )

    return {"status": "accepted", "message": f"Review triggered for {repo_name}"}


def run_real_review(clone_url: str, repo_name: str, branch: str, default_branch: str):
    """
    Clone a real repository into a temp directory and run the full
    MANDATE governed review pipeline on it.
    """
    tmp_dir = None
    try:
        # Create a temporary directory for the clone
        tmp_dir = tempfile.mkdtemp(prefix="mandate_review_")
        print(f"📁 Cloning {repo_name} into {tmp_dir}...")

        # Clone the repository
        clone_result = subprocess.run(
            ["git", "clone", clone_url, tmp_dir],
            capture_output=True, text=True, timeout=120,
        )

        if clone_result.returncode != 0:
            print(f"❌ Clone failed: {clone_result.stderr}")
            recent_reviews.append({
                "repo": repo_name, "branch": branch,
                "findings": 0, "blocked": 0,
                "time": time.strftime("%H:%M:%S"),
                "error": "Clone failed",
            })
            return

        print(f"✅ Clone successful.")

        # If the pushed branch differs from default, check it out so the diff works
        if branch and branch != default_branch:
            print(f"🌿 Checking out branch: {branch}")
            subprocess.run(
                ["git", "checkout", branch],
                capture_output=True, text=True, timeout=30, cwd=tmp_dir,
            )

        print(f"🔍 Running MANDATE review...")

        # Run the review using review_repo.py
        project_root = os.path.dirname(os.path.abspath(__file__))
        review_script = os.path.join(project_root, "review_repo.py")

        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"

        review_result = subprocess.run(
            [sys.executable, review_script, tmp_dir, "--branch", default_branch],
            capture_output=True, text=True, timeout=300,
            cwd=project_root, env=env,
            encoding="utf-8", errors="replace",
        )

        # Print the full output to Zop.dev logs
        if review_result.stdout:
            print(review_result.stdout)
        if review_result.stderr:
            print(review_result.stderr)

        # Parse results for the dashboard
        blocked = review_result.stdout.count("BLOCKED") if review_result.stdout else 0
        findings_line = [l for l in (review_result.stdout or "").split("\n") if "Total findings" in l]
        findings = 0
        if findings_line:
            try:
                findings = int("".join(c for c in findings_line[0].split(":")[-1] if c.isdigit()))
            except ValueError:
                pass

        recent_reviews.append({
            "repo": repo_name, "branch": branch,
            "findings": findings, "blocked": blocked,
            "time": time.strftime("%H:%M:%S"),
        })

        status = "🛡️ PROTECTED" if blocked > 0 else "✅ CLEAN"
        print(f"\n{'='*60}")
        print(f"   {status} — {repo_name}")
        print(f"   Findings: {findings} | Blocked writes: {blocked}")
        print(f"{'='*60}\n")

    except subprocess.TimeoutExpired:
        print(f"⏰ Review timed out for {repo_name}")
        recent_reviews.append({
            "repo": repo_name, "branch": branch,
            "findings": 0, "blocked": 0,
            "time": time.strftime("%H:%M:%S"),
            "error": "Timeout",
        })
    except Exception as e:
        print(f"❌ Error: {e}")
        recent_reviews.append({
            "repo": repo_name, "branch": branch,
            "findings": 0, "blocked": 0,
            "time": time.strftime("%H:%M:%S"),
            "error": str(e),
        })
    finally:
        # Clean up the temp directory
        if tmp_dir and os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
