---
name: commit
description: Review, stage, commit, and push all git changes with an auto-generated message
---

# Commit Workflow

Follow these steps exactly:

## 1. Clean up stale files

Check if a `nul` file exists in the project root. This is a Windows artifact that gets created accidentally. If it exists, delete it with `rm`.

## 2. Review changes

Run these commands **in parallel** to understand the current state:

- `git status` — see all modified/untracked files
- `git diff` — see unstaged changes (both staged and unstaged)
- `git log --oneline -10` — see recent commit messages to match the repo's style

## 3. Summarize changes to the user

Present a brief summary of what changed and in which files. Wait for the user to see it but do NOT ask for confirmation — proceed directly to committing.

## 4. Stage and commit

- Stage all relevant changed files **by name** (do NOT use `git add -A` or `git add .`)
- Do NOT stage files that contain secrets (.env, credentials, etc.) — warn the user if any are present
- Write a concise commit message that:
  - Follows the conventional commit style used in this repo (e.g., `feat:`, `fix:`, `chore:`, `docs:`)
  - Summarizes the "why" not just the "what"
  - Includes a body paragraph if changes span multiple concerns
  - Ends with `Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>`
- Pass the commit message via HEREDOC:

```
git commit -m "$(cat <<'EOF'
<message here>

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

## 5. Push

Push to the remote with `git push`.

## 6. Confirm

Report the commit hash and confirm the push succeeded.
