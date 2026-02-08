#!/usr/bin/env python3
"""Planka API helper — handles auth and API calls without bash token issues."""

import json
import ssl
import sys
import urllib.request
import base64
import os

ENV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env_claude")
BASE_URL = "https://prod.aten:8243/planka/1.0.0"
TOKEN_URL = "https://prod.aten:9443/oauth2/token"
CTX = ssl._create_unverified_context()

PROJECT_ID = "1527549879151232611"
BOARD_ID = "1527550069992064613"
LIST_TODO = "1527558345773287025"
LIST_IN_PROGRESS = "1527558484982236786"
LIST_REVIEW_ME = "1705799394755872536"
LIST_DONE = "1527558498966046323"


def read_env():
    env = {}
    with open(ENV_FILE) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            # handle both "key=value" and "key: value" formats
            if ": " in line:
                k, v = line.split(": ", 1)
            elif "=" in line:
                k, v = line.split("=", 1)
            else:
                continue
            env[k.strip()] = v.strip()
    return env


def write_env(env):
    lines = []
    # Preserve format: key=value for simple, key: value for labeled
    key_format = {
        "key": "key={v}",
        "secret": "secret={v}",
        "token_endpoint": "token_endpoint: {v}",
        "planka_username": "planka_username: {v}",
        "planka_password": "planka_password: {v}",
        "APIM_TOKEN": "APIM_TOKEN: {v}",
        "planka_token": "planka_token: {v}",
    }
    for k in ["key", "secret", "token_endpoint", "planka_username", "planka_password", "APIM_TOKEN", "planka_token"]:
        if k in env:
            lines.append(key_format.get(k, f"{k}={{}}")
                         .format(v=env[k]))
    lines.append("")  # trailing newline
    with open(ENV_FILE, "w") as f:
        f.write("\n".join(lines))


def api_request(url, method="GET", data=None, headers=None):
    if data is not None and isinstance(data, dict):
        data = json.dumps(data).encode()
    elif data is not None and isinstance(data, str):
        data = data.encode()
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    try:
        resp = urllib.request.urlopen(req, context=CTX)
    except urllib.error.HTTPError as e:
        err_body = e.read().decode()
        print(f"HTTP {e.code} {e.reason}: {err_body}", file=sys.stderr)
        raise
    body = resp.read().decode()
    return json.loads(body) if body else {}


def get_apim_token(env):
    creds = base64.b64encode(f"{env['key']}:{env['secret']}".encode()).decode()
    result = api_request(
        TOKEN_URL,
        method="POST",
        data="grant_type=client_credentials",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {creds}",
        },
    )
    return result["access_token"]


def get_planka_token(apim_token, env):
    result = api_request(
        f"{BASE_URL}/access-tokens",
        method="POST",
        data={"emailOrUsername": env["planka_username"], "password": env["planka_password"]},
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {apim_token}",
        },
    )
    return result["item"]


def authenticate():
    """Full auth flow: get APIM token + Planka JWT. Returns (apim_token, planka_token)."""
    env = read_env()

    # Try existing APIM token first
    apim_token = env.get("APIM_TOKEN", "")
    if apim_token:
        try:
            planka_token = env.get("planka_token", "")
            if planka_token:
                # Test if both tokens work
                api_request(
                    f"{BASE_URL}/projects/{PROJECT_ID}",
                    headers={"Authorization": f"Bearer {apim_token}", "XAuth": planka_token},
                )
                return apim_token, planka_token
        except Exception:
            pass

    # Get fresh APIM token
    apim_token = get_apim_token(env)
    env["APIM_TOKEN"] = apim_token

    # Try existing Planka token with new APIM token
    planka_token = env.get("planka_token", "")
    if planka_token:
        try:
            api_request(
                f"{BASE_URL}/projects/{PROJECT_ID}",
                headers={"Authorization": f"Bearer {apim_token}", "XAuth": planka_token},
            )
            write_env(env)
            return apim_token, planka_token
        except Exception:
            pass

    # Get fresh Planka token
    planka_token = get_planka_token(apim_token, env)
    env["planka_token"] = planka_token
    write_env(env)
    return apim_token, planka_token


def planka_call(path, method="GET", data=None):
    """Make an authenticated Planka API call."""
    apim_token, planka_token = authenticate()
    headers = {"Authorization": f"Bearer {apim_token}", "XAuth": planka_token}
    if data is not None:
        headers["Content-Type"] = "application/json"
    url = f"{BASE_URL}{path}" if path.startswith("/") else f"{BASE_URL}/{path}"
    return api_request(url, method=method, data=data, headers=headers)


def get_board_data():
    """Get full board data including lists, cards, tasks."""
    return planka_call(f"/boards/{BOARD_ID}")


def get_todo_cards():
    """Get cards from the To Do list, sorted by position."""
    data = get_board_data()
    cards = data.get("included", {}).get("cards", [])
    todo = [c for c in cards if c.get("listId") == LIST_TODO]
    todo.sort(key=lambda c: c.get("position", 0))
    return todo, data


def get_card_details(card_id):
    """Get full card details including description, tasks, labels."""
    return planka_call(f"/cards/{card_id}")


def move_card(card_id, list_id, position=65536):
    """Move a card to a different list."""
    return planka_call(f"/cards/{card_id}", method="PATCH", data={"listId": list_id, "position": position})


def add_comment(card_id, text):
    """Add a comment to a card."""
    return planka_call(f"/cards/{card_id}/comments", method="POST", data={"text": text})


def update_task(task_id, is_completed=True):
    """Check off a task on a card."""
    return planka_call(f"/tasks/{task_id}", method="PATCH", data={"isCompleted": is_completed})


# CLI interface
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: planka_api.py <command> [args]")
        print("Commands: todo, card <id>, move <id> <list_id>, comment <id> <text>")
        print("          check-task <task_id>, project")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "todo":
        cards, _ = get_todo_cards()
        print(json.dumps(cards, indent=2))

    elif cmd == "project":
        data = planka_call(f"/projects/{PROJECT_ID}")
        print(json.dumps(data, indent=2))

    elif cmd == "card":
        data = get_card_details(sys.argv[2])
        print(json.dumps(data, indent=2))

    elif cmd == "move":
        data = move_card(sys.argv[2], sys.argv[3])
        print(json.dumps(data, indent=2))

    elif cmd == "comment":
        data = add_comment(sys.argv[2], sys.argv[3])
        print(json.dumps(data, indent=2))

    elif cmd == "check-task":
        data = update_task(sys.argv[2])
        print(json.dumps(data, indent=2))

    elif cmd == "call":
        # Generic: planka_api.py call <method> <path> [json_body]
        method = sys.argv[2]
        path = sys.argv[3]
        body = json.loads(sys.argv[4]) if len(sys.argv) > 4 else None
        data = planka_call(path, method=method, data=body)
        print(json.dumps(data, indent=2))

    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
