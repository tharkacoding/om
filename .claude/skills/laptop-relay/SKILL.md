---
name: laptop-relay
description: Run commands on the user's own laptop from a cloud Claude session through a git-based relay (relay/jobs then relay/results on branch claude/friendly-lamport-y8hz5r of tharkacoding/om). Use whenever the user says to work on, take control of, or run something on "my laptop", asks to deploy to Vercel from their machine, check files/state on their computer, or says the cloud session can't reach their local environment - even if they never mention the relay.
---

# laptop-relay

The cloud session cannot reach the user's computer directly. This skill uses the repo as a mailbox: you push a command, a small agent on the laptop pulls it, **asks the user to approve it**, runs it, and pushes the output back.

## How it works
- Jobs: `relay/jobs/NNN.json` containing `{"cmd": "<one command>"}` on branch `claude/friendly-lamport-y8hz5r`.
- Results: `relay/results/NNN.json` with `ok`, `code`, `stdout`, `stderr` (or `error`).
- The agent (`relay/laptop_agent.py`) polls every ~10 s, runs inside the repo folder, no shell, allowlisted programs only (`git vercel npm npx ls dir cat type`), 5-minute timeout.

## Workflow
1. Make sure the user has the agent running (they paste the command from `scripts/laptop_setup.sh`). Ask once if unsure.
2. Queue a job: `bash .claude/skills/laptop-relay/scripts/queue_job.sh "git status --short"` (prints the job id).
3. Wait for the result: `bash .claude/skills/laptop-relay/scripts/read_result.sh <id>` (polls up to ~3 min, prints JSON). Tell the user a prompt is waiting on their laptop; nothing runs until they type `y`.
4. Chain steps: look first (`ls sites`, `cat sites/x/index.html`), then act. Edit files here in the cloud checkout and push - the agent pulls them - rather than trying to write files through commands. Deploy with `vercel deploy --prod --yes` run from the relevant folder.
5. Report faithfully: if a result says declined, failed or timed out, say so and do not retry the same command without asking.

## Safety rules (the reason this is acceptable at all)
- Per-command approval on the laptop stays on. Never suggest `--auto`, never try to bypass the prompt or the allowlist, and do not chain commands with `;`, `|`, `&` or `$()` to sneak around it.
- Never put secrets, tokens or passwords in a command or in the repo; results are committed to git and visible to anyone with repo access. Keep the repo private.
- Keep commands small and explain to the user what each one does before queueing it; they are approving it blind otherwise.
- The relay is for the user's own machine and their stated task only.
