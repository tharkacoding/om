#!/usr/bin/env python3
"""ntfy command runner.

Listens on an ntfy topic and, for every *authenticated* message, runs the
command it carries and posts the output back to the same topic. Standard
library only -- no pip install required.

====================  READ THIS BEFORE RUNNING  ====================
This program executes shell commands that arrive over the network. Running it
turns the machine into a remote shell controlled by whoever can post to the
topic. Protect it accordingly:

  * DO NOT use a public, passwordless topic. ntfy.sh topics are public by
    default: anyone who guesses the topic name can send commands. Use a topic
    protected by ntfy access control (https://docs.ntfy.sh/config/#access-control)
    or self-host ntfy, and set NTFY_AUTH_TOKEN below.
  * A shared secret (NTFY_CMD_SECRET) is REQUIRED. Every command message must
    begin with it or it is ignored. This only keeps out people who don't know
    the secret -- the secret AND all command output are visible to everyone
    subscribed to the topic, so treat it as a weak last line of defense, not
    real auth.
  * Run it somewhere disposable, as an unprivileged user, never as root.

The program refuses to start if NTFY_CMD_SECRET is not set.
====================================================================

Environment variables
  NTFY_TOPIC        topic to listen on            (required)
  NTFY_CMD_SECRET   secret every command must     (required)
                    start with
  NTFY_BASE         ntfy server base URL          (default: https://ntfy.sh)
  NTFY_AUTH_TOKEN   bearer token for a protected  (optional)
                    topic (recommended)
  CMD_TIMEOUT       seconds before a command is   (default: 30)
                    killed
  MAX_OUTPUT        max chars of output posted     (default: 3500)
                    back

Message format (what you send to the topic)
  <secret> ls -la
  <secret> command: df -h
The leading secret is stripped; an optional "command:" prefix is also stripped;
the rest is run with the system shell.

Example
  export NTFY_TOPIC=my-private-topic
  export NTFY_CMD_SECRET='a-long-random-string'
  export NTFY_AUTH_TOKEN='tk_...'     # from ntfy
  python3 ntfy_runner.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

BOT_TITLE = "runner"  # our own posts carry this title so we skip them


def _env(name: str, default: str | None = None, required: bool = False) -> str:
    value = os.environ.get(name, default)
    if required and not value:
        sys.exit(f"error: environment variable {name} is required (see docstring)")
    return value  # type: ignore[return-value]


def publish(base: str, topic: str, token: str | None, body: str) -> None:
    """Post a message back to the topic, tagged with BOT_TITLE."""
    req = urllib.request.Request(
        f"{base.rstrip('/')}/{topic}",
        data=body.encode("utf-8"),
        method="POST",
    )
    req.add_header("Title", BOT_TITLE)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        urllib.request.urlopen(req, timeout=15).read()
    except urllib.error.URLError as exc:
        print(f"[warn] could not publish reply: {exc}", file=sys.stderr)


def run_command(command: str, timeout: int, max_output: int) -> str:
    """Run a shell command, returning combined stdout/stderr (truncated)."""
    try:
        proc = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return f"[timed out after {timeout}s]"
    except Exception as exc:  # noqa: BLE001 - report anything back to the user
        return f"[failed to run: {exc}]"

    out = (proc.stdout or "") + (proc.stderr or "")
    out = out.strip() or "[no output]"
    header = f"$ {command}\n(exit {proc.returncode})\n"
    body = header + out
    if len(body) > max_output:
        body = body[:max_output] + "\n[...truncated]"
    return body


def handle_message(text: str, secret: str) -> str | None:
    """Return the command to run, or None if the message isn't for us."""
    text = text.strip()
    if not text.startswith(secret):
        return None  # missing/incorrect secret -> ignore silently
    rest = text[len(secret):].strip()
    if rest.lower().startswith("command:"):
        rest = rest[len("command:"):].strip()
    return rest or None


def listen(base: str, topic: str, token: str | None, secret: str,
           timeout: int, max_output: int) -> None:
    url = f"{base.rstrip('/')}/{topic}/json"
    print(f"listening on {url} (commands must start with the shared secret)")
    while True:
        req = urllib.request.Request(url)
        if token:
            req.add_header("Authorization", f"Bearer {token}")
        try:
            with urllib.request.urlopen(req) as stream:
                for raw in stream:
                    line = raw.decode("utf-8", "replace").strip()
                    if not line:
                        continue
                    try:
                        event = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if event.get("event") != "message":
                        continue
                    if event.get("title") == BOT_TITLE:
                        continue  # don't react to our own posts
                    command = handle_message(event.get("message", ""), secret)
                    if not command:
                        continue
                    print(f"[run] {command}")
                    result = run_command(command, timeout, max_output)
                    publish(base, topic, token, result)
        except urllib.error.URLError as exc:
            print(f"[warn] connection lost ({exc}); reconnecting in 5s",
                  file=sys.stderr)
            time.sleep(5)
        except KeyboardInterrupt:
            print("\nstopped.")
            return


def main() -> None:
    base = _env("NTFY_BASE", "https://ntfy.sh")
    topic = _env("NTFY_TOPIC", required=True)
    secret = _env("NTFY_CMD_SECRET", required=True)
    token = _env("NTFY_AUTH_TOKEN")
    timeout = int(_env("CMD_TIMEOUT", "30"))
    max_output = int(_env("MAX_OUTPUT", "3500"))
    listen(base, topic, token, secret, timeout, max_output)


if __name__ == "__main__":
    main()
