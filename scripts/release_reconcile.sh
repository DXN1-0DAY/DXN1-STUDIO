#!/bin/bash
# The reconcile law: every tag wears a release. Audits every tag (the
# initial sweep backfills the whole line; the runner's GITHUB_TOKEN
# comfortably mints ~120 lightweight calls); any tag without a release
# gets one — notes from the CHANGELOG when the section exists, the
# tag's commit message when it doesn't (scripts/release_notes.py owns
# that contract). Idempotent by design: runs on every master push and
# is a no-op when the ledger is honest.
#
# Needs GH_TOKEN in the environment (the workflow supplies the run's
# own GITHUB_TOKEN) and `gh` (preinstalled on GitHub runners).
set -u

cd "$(dirname "$0")/.." || exit 1

TAGS=$(git tag --sort=-v:refname)
if [ -z "$TAGS" ]; then
  echo "   ok  no tags on this clone — nothing to wrap"
  exit 0
fi

MISSING=0
for TAG in $TAGS; do
  if gh release view "$TAG" >/dev/null 2>&1; then
    echo "   ok  $TAG already wears its release"
    continue
  fi
  MISSING=$((MISSING + 1))
  NOTES="/tmp/notes-${TAG}.md"
  if python3 scripts/release_notes.py "$TAG" > "$NOTES" 2>/dev/null; then
    SRC="changelog"
  else
    echo "Release ${TAG} — see the tag's commit for the full story." > "$NOTES"
    SRC="commit"
  fi
  echo "   cut ${TAG} (notes: ${SRC})"
  gh release create "$TAG" --title "DXN1 STUDIO ${TAG}" \
    --notes-file "$NOTES" >/dev/null 2>&1 \
    || echo "   FAIL ${TAG} — the wrap did not take"
done

if [ "$MISSING" -eq 0 ]; then
  echo "   ok  reconcile: every tag already wears its release"
else
  echo "   done reconcile: ${MISSING} naked tag(s) wrapped"
fi
