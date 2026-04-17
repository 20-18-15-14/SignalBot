# Branching and Upstream Sync

## Remotes

```
origin    https://github.com/20-18-15-14/SignalBot.git   (this fork, read/write)
upstream  https://github.com/CarmichaelAJ/SignalBot.git  (upstream, read-only)
```

If `upstream` is missing for a fresh clone:

```bash
git remote add upstream https://github.com/CarmichaelAJ/SignalBot.git
git fetch upstream
```

## Branch strategy

- `main` — mirrors `upstream/main`. No direct commits. Keep it clean so PRs back are trivially mergeable.
- `feature/<slug>` — all active work. One feature per branch. Rebased onto latest `main` before PR.
- `experiment/<slug>` — exploratory spikes that may not ship. Safe to delete.

## Syncing from upstream

Do this at least weekly, and always before starting a new feature branch:

```bash
git checkout main
git fetch upstream
git merge upstream/main
git push origin main
```

If `upstream/main` has diverged significantly and you have in-flight branches, rebase each feature branch:

```bash
git checkout feature/multi-model-router
git rebase main
```

## Starting a feature

```bash
git checkout main
git pull origin main                 # already synced from upstream above
git checkout -b feature/short-slug
```

## Opening a PR to upstream

When a feature slice is coherent, tested, and ready for review:

```bash
gh pr create --repo CarmichaelAJ/SignalBot \
  --base main \
  --head 20-18-15-14:feature/short-slug \
  --title "..." --body "..."
```

Draft PRs are encouraged for visibility while work is in progress.

## Running this fork independently

Until / unless a PR is merged, this fork can run as a standalone deployment. Docker Compose setup (`LOCAL_SETUP.md`) works identically on the fork. Configuration differences go in `.env`, not in code.
