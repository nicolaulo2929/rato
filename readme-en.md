# Consent-Based Telemetry Lab

A Python learning project for collecting **non-sensitive system telemetry** from
machines you own or are explicitly authorized to test.

The project demonstrates:

- Flask HTTP APIs
- Client registration and heartbeat tracking
- JSON telemetry ingestion
- Local JSONL storage
- Task queues limited to safe diagnostic actions
- Basic health checks
- Input validation and request-size limits
- Explicit authorization and audit controls

> This project is designed for local labs, classroom exercises, and authorized
> testing. It does not collect passwords, cookies, browser tokens, keystrokes,
> screenshots, private files, or microphone/webcam data.

## Contents

- [Architecture](#architecture)
- [Requirements](#requirements)
- [Project Structure](#project-structure)
- [Server Setup](#server-setup)
- [Client Setup](#client-setup)
- [Running the Lab](#running-the-lab)
- [Safe Commands](#safe-commands)
- [API Reference](#api-reference)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [Security Practices](#security-practices)
- [Development](#development)
- [License](#license)

## Architecture

```text
+------------------+              HTTP               +------------------+
| Telemetry client |  ------------------------------> | Flask server     |
|                  |                                  |                  |
| - Hostname       |                                  | - Registration   |
| - OS metadata    |                                  | - Heartbeats     |
| - CPU/RAM usage  |                                  | - Telemetry logs |
| - Disk usage     |                                  | - Safe tasks     |
+------------------+                                  +------------------+
                                                               |
                                                               v
                                                        +--------------+
                                                        | Local storage|
                                                        | logs/        |
                                                        | tasks/       |
                                                        | results/     |
                                                        +--------------+
```

## Requirements

### Server

- Python 3.10 or newer
- Flask

### Client

- Python 3.10 or newer
- `requests`
- `psutil`

### Optional

- PyInstaller for packaging a transparent, consent-based client executable
- `pytest` for tests
- `ruff` for linting

## Project Structure

```text
telemetry-lab/
├── server/
│   ├── telemetry_server.py
│   └── requirements.txt
├── client/
│   ├── telemetry_client.py
│   └── requirements.txt
├── tests/
│   ├── test_server.py
│   └── test_client.py
├── docs/
│   └── API.md
├── .env.example
├── .gitignore
├── LICENSE
└── README.md
```

## Server Setup

Create and activate a virtual environment:

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### Linux or macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install flask
```

Start the server:

```bash
python server/telemetry_server.py
```

The development server listens on:

```text
http://127.0.0.1:8080
```

For a local network lab, configure the bind address explicitly and only expose
the port to a trusted private network.

## Client Setup

Install client dependencies:

```bash
python -m pip install requests psutil
```

Open `client/telemetry_client.py` and configure the server URL:

```python
SERVER_URL = "http://127.0.0.1:8080"
CLIENT_ID = "lab-client-01"
```

Run the client:

```bash
python client/telemetry_client.py
```

The client sends only non-sensitive telemetry:

- Client identifier
- Hostname
- Operating-system name
- Python version
- CPU utilization
- Memory utilization
- Disk utilization
- Collection timestamp

## Running the Lab

Start the server first:

```bash
python server/telemetry_server.py
```

In a second terminal, start the client:

```bash
python client/telemetry_client.py
```

Check the server health:

```text
GET http://127.0.0.1:8080/health
```

List registered clients:

```text
GET http://127.0.0.1:8080/list
```

View a client's telemetry:

```text
GET http://127.0.0.1:8080/logs/lab-client-01
```

## Safe Commands

The task endpoint is intentionally limited to diagnostic operations:

| Command | Purpose |
|---|---|
| `health` | Return client health information |
| `telemetry` | Collect a fresh non-sensitive telemetry snapshot |
| `version` | Return client version and runtime information |

The project deliberately excludes:

- Arbitrary shell execution
- Credential extraction
- Cookie or session-token access
- Keylogging
- Screen capture
- Webcam or microphone access
- Private-file collection
- Persistence mechanisms
- Evasion or obfuscation
- Unauthorized remote control

## API Reference

### `GET /health`

Returns server health.

Example response:

```json
{
  "status": "ok",
  "time": "2026-09-09T19:00:00+00:00"
}
```

### `POST /register`

Registers a client.

Request:

```json
{
  "client_id": "lab-client-01"
}
```

Response:

```json
{
  "status": "ok",
  "client_id": "lab-client-01"
}
```

### `POST /heartbeat`

Updates a client's last-seen timestamp.

Request:

```json
{
  "client_id": "lab-client-01"
}
```

Response:

```json
{
  "status": "ok"
}
```

### `POST /log`

Stores a telemetry message.

Request:

```json
{
  "client_id": "lab-client-01",
  "message": {
    "hostname": "lab-host",
    "cpu_percent": 12.4,
    "memory_percent": 48.7
  }
}
```

The server accepts structured JSON messages and enforces a maximum request
size.

### `GET /list`

Lists registered clients and their online status.

Example response:

```json
{
  "lab-client-01": {
    "registered_at": "2026-09-09T18:55:00+00:00",
    "last_seen": "2026-09-09T19:00:00+00:00",
    "online": true
  }
}
```

### `GET /logs/<client_id>`

Returns stored telemetry for one client.

Example:

```text
[2026-09-09T19:00:00+00:00] {"hostname":"lab-host","cpu_percent":12.4}
```

### `POST /task`

Queues an allowlisted diagnostic task.

Request:

```json
{
  "client_id": "lab-client-01",
  "command": "telemetry"
}
```

Response:

```json
{
  "status": "ok",
  "task_id": "generated-task-id"
}
```

### `GET /tasks/<client_id>`

The client polls for its next pending task.

Response:

```json
{
  "status": "ok",
  "task": {
    "task_id": "generated-task-id",
    "command": "telemetry",
    "created_at": "2026-09-09T19:00:00+00:00"
  }
}
```

### `POST /result`

The client submits the result of a safe task.

Request:

```json
{
  "task_id": "generated-task-id",
  "client_id": "lab-client-01",
  "status": "success",
  "output": {
    "cpu_percent": 12.4,
    "memory_percent": 48.7
  },
  "error": ""
}
```

### `GET /results/<task_id>`

Returns a stored task result.

## Configuration

The server uses these values:

```python
HOST = "127.0.0.1"
PORT = 8080
MAX_LOG_SIZE = 1_000_000
MAX_TASK_PAYLOAD = 64_000
```

For a local-only lab, keep:

```python
HOST = "127.0.0.1"
```

For a trusted private test network, use:

```python
HOST = "0.0.0.0"
```

When binding to all interfaces, apply a firewall rule that allows access only
from the intended private network and protect the API with authentication.

## Storage

The server creates these directories:

```text
logs/
├── lab-client-01.log

tasks/
├── lab-client-01.json

results/
├── generated-task-id.json
```

Do not commit real telemetry, hostnames, IP addresses, or test data:

```gitignore
logs/
tasks/
results/
*.log
.env
.venv/
__pycache__/
dist/
build/
```

## Troubleshooting

### The client does not appear in `/list`

Check the following:

1. The server is running.
2. `SERVER_URL` is correct.
3. The client can reach the server.
4. The server port is allowed by the local firewall.
5. The client debug log contains no connection errors.

Windows PowerShell:

```powershell
Test-NetConnection -ComputerName 127.0.0.1 -Port 8080
```

### The server returns `400`

Confirm that the request has:

```text
Content-Type: application/json
```

and that the body is valid JSON.

### The server returns `413`

The submitted message or task is larger than the configured limit. Reduce the
payload or increase the limit only for a controlled local test.

### The client exits immediately

Run it with Python instead of a hidden-console executable:

```bash
python client/telemetry_client.py
```

This exposes the traceback directly.

### PowerShell blocks a local script

Prefer running the Python file directly:

```powershell
python .\client\telemetry_client.py
```

## Security Practices

- Run this project only on systems you own or are authorized to test.
- Keep the server bound to `127.0.0.1` during development.
- Do not expose the development server directly to the public internet.
- Add authentication before using a private network deployment.
- Use HTTPS for any non-local connection.
- Keep secrets in environment variables, never in source files.
- Do not commit logs, screenshots, credentials, or tokens.
- Rotate credentials immediately if they are accidentally committed.
- Review every task handler before adding a new command.
- Maintain an audit log for administrative actions.

## Development

Install development tools:

```bash
python -m pip install pytest ruff
```

Run linting:

```bash
ruff check .
```

Run tests:

```bash
pytest -q
```

Format code:

```bash
ruff format .
```

## Packaging the Client

For a transparent lab executable:

```bash
python -m pip install pyinstaller
python -m PyInstaller --onefile --name telemetry-client client/telemetry_client.py
```

The output is written to:

```text
dist/telemetry-client.exe
```

Do not use hidden execution, evasion, fake metadata, persistence, or
credential-access features.

## Contributing

1. Fork the repository.
2. Create a branch:

   ```bash
   git checkout -b feature/telemetry-dashboard
   ```

3. Make a focused change.
4. Add or update tests.
5. Run linting and tests.
6. Open a pull request with:
   - A clear description
   - Reproduction steps
   - Test results
   - Security impact

## License

MIT License

Copyright (c) 2026

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
