#!/usr/bin/env python3
"""Tiny laptop-side relay. Polls this git branch for relay/jobs/*.json, runs each
allowlisted command in this repo folder, and pushes the output to relay/results/.

Safety: allowlisted programs only, no shell, runs inside the repo folder, 5-minute
timeout, and you must type y to approve every command (unless you pass --auto).
Stop it any time with Ctrl+C.

Usage:  python relay/laptop_agent.py [--branch claude/friendly-lamport-y8hz5r] [--auto]
"""
import argparse, json, os, shlex, subprocess, sys, time

ALLOWED = {"git", "vercel", "npm", "npx", "ls", "dir", "cat", "type"}
BAD = set(";&|><`$\n\r")
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def git(*a):
    return subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True)


def check(cmd):
    if any(c in BAD for c in cmd):
        return "shell metacharacters are not allowed"
    parts = shlex.split(cmd)
    if not parts or os.path.basename(parts[0]).lower() not in ALLOWED:
        return "program not on allowlist: " + (parts[0] if parts else "")
    for p in parts[1:]:
        if os.path.isabs(p) or ".." in p.replace("\\", "/").split("/"):
            return "paths must stay inside the repo folder: " + p
    return None


def run(job, auto):
    cmd = job["cmd"]
    err = check(cmd)
    if err:
        return {"ok": False, "error": err}
    print(f"\nClaude wants to run in {ROOT}:\n  {cmd}")
    if not auto and input("Allow? [y/N] ").strip().lower() != "y":
        return {"ok": False, "error": "declined by user"}
    try:
        r = subprocess.run(shlex.split(cmd), cwd=ROOT, capture_output=True, text=True,
                           timeout=300, shell=False)
        return {"ok": r.returncode == 0, "code": r.returncode,
                "stdout": r.stdout[-20000:], "stderr": r.stderr[-20000:]}
    except Exception as e:
        return {"ok": False, "error": repr(e)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--branch", default="claude/friendly-lamport-y8hz5r")
    ap.add_argument("--auto", action="store_true", help="skip per-command prompts (not recommended)")
    a = ap.parse_args()
    git("checkout", a.branch)
    print("Relay running on", a.branch, "- Ctrl+C to stop")
    while True:
        git("pull", "--ff-only", "origin", a.branch)
        jobs, results = (os.path.join(ROOT, "relay", d) for d in ("jobs", "results"))
        os.makedirs(results, exist_ok=True)
        done = False
        for f in sorted(os.listdir(jobs)) if os.path.isdir(jobs) else []:
            if not f.endswith(".json") or os.path.exists(os.path.join(results, f)):
                continue
            job = json.load(open(os.path.join(jobs, f)))
            out = run(job, a.auto)
            json.dump(out, open(os.path.join(results, f), "w"), indent=1)
            git("add", "relay/results")
            git("commit", "-m", f"relay result {f}")
            done = True
        if done:
            git("push", "origin", a.branch)
        time.sleep(10)


if __name__ == "__main__":
    main()
