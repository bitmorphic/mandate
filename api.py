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
    total_blocked = 0
    total_findings = 0
    total_reviews = len(recent_reviews)
    
    for review in reversed(recent_reviews[-10:]):
        blocked = review.get("blocked", 0)
        findings = review.get("findings", 0)
        total_blocked += blocked
        total_findings += findings
        
        status_icon = "🛡️" if blocked > 0 else "✅"
        border_color = "#f97316" if blocked > 0 else "#22c55e"
        
        raw_out = review.get('raw_output', '')
        safe_raw_out = raw_out.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        
        error_html = ""
        if review.get("error"):
            error_html = f'<span style="color:#ef4444; font-size:12px; margin-left:8px;">⚠️ {review["error"]}</span>'
        
        details_html = ""
        if safe_raw_out:
            details_html = f"""
            <details style="margin-top:10px; cursor:pointer;">
                <summary style="color:#f97316; font-size:13px; font-weight:bold;">▶ Show full MANDATE console output</summary>
                <div style="background:#0d1117; padding:12px; border-radius:6px; margin-top:8px; overflow-x:auto; border:1px solid #30363d; max-height:500px; overflow-y:auto;">
                    <pre style="color:#e6edf3; font-size:11px; line-height:1.4; margin:0; white-space:pre-wrap; word-wrap:break-word;">{safe_raw_out}</pre>
                </div>
            </details>
            """
            
        reviews_html += f"""
        <div style="background:linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); border-left:3px solid {border_color}; border-radius:8px; padding:16px; margin:10px 0; transition:transform 0.2s;" onmouseover="this.style.transform='translateX(4px)'" onmouseout="this.style.transform='translateX(0)'">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <strong style="font-size:15px;">{status_icon} {review.get('repo', 'unknown')}</strong>
                    <span style="color:#888; margin-left:12px; font-size:13px;">{review.get('branch', '')}</span>
                    {error_html}
                </div>
                <span style="color:#555; font-size:12px;">{review.get('time', '')}</span>
            </div>
            <div style="margin-top:8px; display:flex; gap:16px;">
                <span style="background:#1e293b; padding:4px 10px; border-radius:12px; font-size:12px; color:#94a3b8;">📊 Findings: {review.get('findings', 0)}</span>
                <span style="background:{'#7f1d1d' if blocked > 0 else '#14532d'}; padding:4px 10px; border-radius:12px; font-size:12px; color:{'#fca5a5' if blocked > 0 else '#86efac'};">{'🚫' if blocked > 0 else '✅'} Blocked: {blocked}</span>
            </div>
            {details_html}
        </div>
        """

    if not reviews_html:
        reviews_html = '''
        <div style="text-align:center; padding:40px 20px; background:#161b22; border:1px dashed #30363d; border-radius:12px;">
            <p style="font-size:40px; margin:0;">⏳</p>
            <p style="color:#888; font-size:14px; margin-top:12px;">No reviews yet. Push code to a connected repo to trigger a review.</p>
            <p style="color:#555; font-size:12px;">Waiting for GitHub webhook...</p>
        </div>'''

    protection_rate = int((total_blocked / max(total_reviews, 1)) * 100) if total_reviews > 0 else 0

    return f"""
    <html>
    <head>
        <title>MANDATE — Governed AI Dashboard</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
        <style>
            * {{ margin:0; padding:0; box-sizing:border-box; }}
            body {{ background:#0d1117; color:#e6edf3; font-family:'Inter',system-ui,sans-serif; }}
            @keyframes pulse {{ 0%,100% {{ opacity:1; }} 50% {{ opacity:0.5; }} }}
            @keyframes slideIn {{ from {{ opacity:0; transform:translateY(20px); }} to {{ opacity:1; transform:translateY(0); }} }}
            @keyframes glow {{ 0%,100% {{ box-shadow:0 0 5px #f97316; }} 50% {{ box-shadow:0 0 20px #f97316, 0 0 40px rgba(249,115,22,0.3); }} }}
            .container {{ max-width:900px; margin:0 auto; padding:20px; }}
            .hero {{ text-align:center; padding:40px 0 20px; animation:slideIn 0.6s ease-out; }}
            .ascii-logo {{ color:#f97316; font-family:'JetBrains Mono',monospace; font-size:10px; line-height:1.15; letter-spacing:1px; }}
            .tagline {{ font-size:22px; font-weight:700; margin-top:12px; background:linear-gradient(90deg,#e6edf3,#f97316); -webkit-background-clip:text; -webkit-text-fill-color:transparent; }}
            .subtitle {{ color:#8b949e; font-size:14px; margin-top:6px; }}
            .badge {{ display:inline-block; background:#21262d; border:1px solid #30363d; padding:3px 10px; border-radius:12px; font-size:11px; color:#8b949e; margin:2px; font-family:'JetBrains Mono',monospace; }}
            .badge-orange {{ border-color:#f97316; color:#f97316; }}
            .stats {{ display:grid; grid-template-columns:repeat(3,1fr); gap:12px; margin:24px 0; animation:slideIn 0.8s ease-out; }}
            .stat-card {{ background:linear-gradient(135deg,#161b22,#1a1f2e); border:1px solid #30363d; border-radius:12px; padding:20px; text-align:center; transition:border-color 0.3s; }}
            .stat-card:hover {{ border-color:#f97316; }}
            .stat-number {{ font-size:32px; font-weight:700; font-family:'JetBrains Mono',monospace; }}
            .stat-label {{ color:#8b949e; font-size:12px; margin-top:4px; text-transform:uppercase; letter-spacing:1px; }}
            .status-bar {{ background:#161b22; border:1px solid #30363d; border-radius:12px; padding:16px 20px; margin:16px 0; display:flex; justify-content:space-between; align-items:center; animation:slideIn 0.7s ease-out; }}
            .status-dot {{ width:10px; height:10px; border-radius:50%; background:#22c55e; display:inline-block; margin-right:8px; animation:pulse 2s infinite; }}
            .section-title {{ font-size:16px; font-weight:700; margin:28px 0 12px; display:flex; align-items:center; gap:8px; }}
            .arch-grid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:8px; margin:16px 0; }}
            .arch-step {{ background:#161b22; border:1px solid #30363d; border-radius:8px; padding:12px; text-align:center; font-size:12px; transition:all 0.3s; }}
            .arch-step:hover {{ border-color:#f97316; transform:translateY(-2px); }}
            .arch-step .step-icon {{ font-size:24px; margin-bottom:6px; }}
            .arch-step .step-title {{ font-weight:600; font-size:11px; color:#e6edf3; }}
            .arch-step .step-desc {{ color:#8b949e; font-size:10px; margin-top:4px; }}
            .footer {{ text-align:center; padding:30px 0; color:#30363d; font-size:12px; border-top:1px solid #21262d; margin-top:30px; }}
            .footer a {{ color:#f97316; text-decoration:none; }}
            code {{ background:#1e293b; padding:3px 8px; border-radius:4px; font-family:'JetBrains Mono',monospace; font-size:12px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="hero">
                <pre class="ascii-logo">
  ███╗   ███╗ █████╗ ███╗   ██╗██████╗  █████╗ ████████╗███████╗
  ████╗ ████║██╔══██╗████╗  ██║██╔══██╗██╔══██╗╚══██╔══╝██╔════╝
  ██╔████╔██║███████║██╔██╗ ██║██║  ██║███████║   ██║   █████╗
  ██║╚██╔╝██║██╔══██║██║╚██╗██║██║  ██║██╔══██║   ██║   ██╔══╝
  ██║ ╚═╝ ██║██║  ██║██║ ╚████║██████╔╝██║  ██║   ██║   ███████╗
  ╚═╝     ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝╚═════╝ ╚═╝  ╚═╝   ╚═╝   ╚══════╝</pre>
                <p class="tagline">Autonomous AI. Governed by Authority.</p>
                <p class="subtitle">Powered by <strong style="color:#f97316;">ArmorIQ SDK</strong> — Cryptographic Intent Enforcement</p>
                <div style="margin-top:12px;">
                    <span class="badge badge-orange">Python 3.10+</span>
                    <span class="badge">ArmorIQ SDK</span>
                    <span class="badge">Groq LLM</span>
                    <span class="badge">Ed25519</span>
                    <span class="badge">Docker</span>
                    <span class="badge">GitHub Actions</span>
                </div>
            </div>

            <div class="stats">
                <div class="stat-card">
                    <div class="stat-number" style="color:#3b82f6;">{total_reviews}</div>
                    <div class="stat-label">Total Reviews</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" style="color:#ef4444;">{total_blocked}</div>
                    <div class="stat-label">Writes Blocked</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" style="color:#22c55e;">{protection_rate}%</div>
                    <div class="stat-label">Protection Rate</div>
                </div>
            </div>

            <div class="status-bar">
                <div>
                    <span class="status-dot"></span>
                    <strong>Server Status: Active</strong>
                </div>
                <div style="display:flex; gap:12px;">
                    <span style="color:#8b949e; font-size:13px;">Webhook: <code>POST /webhook</code></span>
                    <span style="color:#8b949e; font-size:13px;">Health: <code>GET /health</code></span>
                </div>
            </div>

            <div class="section-title">🏗️ Architecture Pipeline</div>
            <div class="arch-grid">
                <div class="arch-step">
                    <div class="step-icon">🔔</div>
                    <div class="step-title">Webhook Trigger</div>
                    <div class="step-desc">GitHub push event fires</div>
                </div>
                <div class="arch-step">
                    <div class="step-icon">🔐</div>
                    <div class="step-title">Mint Token</div>
                    <div class="step-desc">Ed25519 IntentToken signed</div>
                </div>
                <div class="arch-step">
                    <div class="step-icon">🤖</div>
                    <div class="step-title">3 AI Agents</div>
                    <div class="step-desc">Linter · Security · Perf</div>
                </div>
                <div class="arch-step">
                    <div class="step-icon">🛡️</div>
                    <div class="step-title">Proxy Enforce</div>
                    <div class="step-desc">ArmorIQ blocks violations</div>
                </div>
            </div>

            <div class="section-title">📋 Recent Reviews</div>
            {reviews_html}

            <div class="footer">
                <p>MANDATE — Team BRUTE FORCE · NIT Delhi</p>
                <p style="margin-top:6px;"><a href="https://github.com/bitmorphic/mandate" target="_blank">GitHub Repository</a> · ArmorIQ Track · Automate India Hackathon</p>
                <p style="margin-top:8px; color:#555; font-style:italic;">"Capability is not authority. MANDATE proves it."</p>
            </div>
        </div>
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

    # Run the review synchronously to prevent Zop.dev serverless container from freezing the background task
    run_real_review(
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
            "raw_output": review_result.stdout or "No output generated.",
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
