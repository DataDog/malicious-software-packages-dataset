#!/usr/bin/env bash
# Commits synchronized samples in size-capped batches, pushes after each batch, then opens a PR.
# GitHub rejects any single push whose pack exceeds 2 GiB, which a large sync can easily reach
# in one commit. Pushing incrementally to the same branch keeps every pack below the limit.
#
# Requires GH_TOKEN (to open the PR) and a git remote "origin" that accepts pushes.
set -euo pipefail

MAX_BATCH_BYTES=${MAX_BATCH_BYTES:-$((1024 * 1024 * 1024))}
BASE_BRANCH=${BASE_BRANCH:-main}
COMMIT_MESSAGE="Auto-synchronize malicious packages"
TRACKED_PATHS=(samples/ README.md)
REVIEWERS="christophetd,sobregosodd,ikretz,tesnim5hamdouni"

if [[ -z "$(git status --porcelain -- "${TRACKED_PATHS[@]}")" ]]; then
  echo "No changes to synchronize"
  exit 0
fi

branch="create-pull-request/patch-$(date +%s)"
git checkout -b "$branch"
git config user.name "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"

commit_and_push() {
  git commit --quiet -m "$COMMIT_MESSAGE"
  git push origin "$branch"
}

# Modifications and deletions of tracked files are small, so they go in the first batch.
git add --update -- "${TRACKED_PATHS[@]}"

batch_bytes=0
while IFS= read -r -d '' file; do
  size=$(wc -c < "$file")
  if (( batch_bytes > 0 && batch_bytes + size > MAX_BATCH_BYTES )); then
    commit_and_push
    batch_bytes=0
  fi
  git add -- "$file"
  batch_bytes=$((batch_bytes + size))
done < <(git ls-files -z --others --exclude-standard -- "${TRACKED_PATHS[@]}")

if ! git diff --cached --quiet; then
  commit_and_push
fi

gh pr create \
  --base "$BASE_BRANCH" \
  --head "$branch" \
  --title "[Bot] $COMMIT_MESSAGE" \
  --body "Automated synchronization of malicious packages samples." \
  --label sync \
  --reviewer "$REVIEWERS"
