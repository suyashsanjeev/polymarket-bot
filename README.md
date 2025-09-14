# Polymarket Signal Bot

**Automated monitor that detects newly listed Polymarket markets matching user-defined keywords and pushes concise alerts to Signal groups.**

---

## Contents

* [Features](#features)
* [Prerequisites](#prerequisites)
* [Quickstart (Docker signal-cli REST API)](#quickstart-docker-signal-cli-rest-api)
* [Alternative: native signal-cli setup (Linux/macOS)](#alternative-native-signal-cli-setup-linux--macos)
* [Install Python dependencies](#install-python-dependencies)
* [Configuration](#configuration)
* [Usage](#usage)
* [Recommended production / deployment notes](#recommended-production--deployment-notes)
* [Troubleshooting](#troubleshooting)
* [Security & privacy considerations](#security--privacy-considerations)
* [License](#license)

---

## Features

* Periodically fetches active Polymarket markets in parallel
* Lightweight keyword-based relevance filtering (case-insensitive)
* Persistent deduplication via a file-backed history store (prevents repeated alerts)
* Sends chunked messages to a Signal group using a signal-cli HTTP API/daemon
* CLI modes: `--send-summary`, `--monitor`, `--check-once`

---

## Prerequisites

* Linux, macOS, or WSL on Windows
* Python 3.10+ (3.11 recommended)
* git
* Docker (recommended for signal-cli REST API) **OR** ability to install `signal-cli` locally
* A phone number you own to register with Signal (required by `signal-cli`)

---

## Quickstart (Docker signal-cli REST API)

Using the community REST wrapper for `signal-cli` in Docker is the fastest way to get the HTTP daemon that this bot expects.

1. Install Docker ([https://docs.docker.com/get-docker/](https://docs.docker.com/get-docker/)).

2. Create a local data directory to persist your Signal state (so you don't re-register every time):

```bash
mkdir -p $HOME/.polymarket-signal-data
```

3. Run the signal-cli REST API in Docker (example):

```bash
docker run -d --name signal-cli-rest-api \
  -v $HOME/.polymarket-signal-data:/home/.local/share/signal-cli \
  -p 8080:8080 \
  bbernhard/signal-cli-rest-api:latest
```

> This runs a container that exposes an HTTP API (default `http://localhost:8080`). The bot in this repo calls `POST {daemon_url}/api/v1/rpc` by default. If you use a different image or version, confirm the API path in your `SignalSender` implementation.

4. Register your phone number with the running container (this will send the verification code to your phone):

```bash
# Replace +1YOURNUMBER with your E.164 phone number (e.g. +1425XXXXXXX)
docker exec -it signal-cli-rest-api signal-cli -u +1YOURNUMBER register
```

5. Verify using the verification code you receive via SMS (replace CODE):

```bash
docker exec -it signal-cli-rest-api signal-cli -u +1YOURNUMBER verify CODE
```

6. Create or find your Signal group ID. You can create a group on your phone and then list groups via the container to find the `groupId` string:

```bash
docker exec -it signal-cli-rest-api signal-cli -u +1YOURNUMBER listGroups
```

Copy the `groupId` value for use in `config.yaml`.

---

## Alternative: native signal-cli setup (Linux / macOS)

If you prefer not to use Docker, follow the upstream `signal-cli` installation instructions:

1. Install dependencies (varies by OS). On many Linux systems you can install via a package manager (or download the binary jar).
2. Register your number and verify using the CLI: `signal-cli -u +1YOURNUMBER register` then `signal-cli -u +1YOURNUMBER verify CODE`.
3. Optionally run a local HTTP wrapper (there are a few community projects) or implement a small HTTP-to-signal-cli adapter that accepts JSON-RPC and calls `signal-cli` locally.

> NOTE: the repo code expects a signal-cli *HTTP* daemon. If you run `signal-cli` only, you'll need to either adapt `SignalSender` to run the CLI directly or run a small wrapper to accept RPC requests.

---

## Install Python dependencies

From the project root:

```bash
# recommended: create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # macOS / Linux
# Windows (PowerShell): .\.venv\Scripts\Activate.ps1

# install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

If `requirements.txt` is not present, create it with at least:

```text
aiohttp
PyYAML
requests
```

You can also install dev tools:

```bash
pip install black mypy pytest
```

---

## Configuration

The project uses a `config.yaml` (example provided in the repo). Copy and edit it for your environment.

`config.yaml` example:

```yaml
signal:
  daemon_url: "http://localhost:8080"  # update if you ran the REST API on a different host/port
  number: "+1XXXXXXXXXX"               # your registered signal number (E.164 format)
  group_id: "<paste-your-group-id-here>"  # signal groupId as returned by signal-cli listGroups

keywords:
  - patrick
  - mahomes
  - goat
  - greatest of all time
  - chiefs
  - superbowl
  - dynasty

history_file: "./data/notified_markets.txt"
check_interval: 3600
```

**Tips:**

* Keep `keywords` lowercase and avoid accidental leading/trailing spaces.
* Use a path under `$HOME` for `history_file` if you run the container from various places.

---

## Usage

Run the monitor script from the project root. Use one of the three CLI modes:

* Send a one-time summary of all current relevant markets:

```bash
python polymarket-bot/monitor.py --send-summary --config config.yaml
```

* Check once for **new** markets and exit:

```bash
python polymarket-bot/monitor.py --check-once --config config.yaml
```

* Run continuous monitoring (will poll every `check_interval` seconds):

```bash
python polymarket-bot/monitor.py --monitor --config config.yaml
```

**Note:** the script prints status messages and logs. When running long-lived monitoring, run inside a process manager (systemd, Docker, or a supervised screen/tmux session).

---

## Recommended production / deployment notes

* **Run the whole system in Docker Compose**: one service for the bot, one for the signal-cli REST API, persistent volumes for the signal data and history file.
* **Use SQLite for history**: switching `FileHistory` to an SQLite table gives atomic writes and allows pruning and metadata (timestamp, reason).
* **Metrics & monitoring**: emit basic metrics (alerts sent, failures) to Prometheus/CloudWatch.
* **Backoffs & rate limits**: the code already uses exponential backoff — ensure you respect Polymarket API usage policies.

---

## Troubleshooting

* **Signal registration fails or verification code not received**: verify the phone number, check SMS delivery with your carrier, and inspect the container logs:

```bash
docker logs signal-cli-rest-api
```

* **Daemon unreachable (connection refused)**: ensure Docker is running and port 8080 is mapped. Confirm `daemon_url` in `config.yaml`.

* **Group ID not found**: create a group in the Signal app first, then run `signal-cli -u +1YOURNUMBER listGroups` in the container and copy the ID.

* **Bot sends duplicate alerts**: confirm `history_file` path is writable and that the slugs are being appended. If you run multiple bot instances against the same history file, consider migrating to SQLite.

* **Polymarket fetch errors / timeouts**: network issues or API changes. Check repository `polymarket/api.py` and add retries or reduce `page_size`.

---

## Security & privacy considerations

* Your registered Signal phone number and group ID are sensitive. Do **not** commit `config.yaml` with live secrets to git. Use environment variables or a secrets manager.
* The bot stores seen-market slugs on disk. If the history contains sensitive mappings you want to avoid, secure the `history_file` path and permissions.
* If you plan to run the bot on a public server, firewall the signal daemon port and use HTTPS/SSH tunnels.

---

## License

MIT

---
