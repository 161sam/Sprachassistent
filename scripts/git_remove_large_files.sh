#!/usr/bin/env bash
# Safety wrapper with instructions for removing large files introduced by mistake.
# This script does NOT rewrite history automatically. Read and run commands manually.

cat <<'DOC'
Option A: Remove files in a normal commit (no history rewrite)
-----------------------------------------------------------------
1) Remove unwanted files/directories:

   git rm -r --cached spk_cache/
   git rm -r --cached data/

   # If specific files were added elsewhere, remove them explicitly, e.g.:
   # git rm --cached path/to/bigfile.wav

2) Commit the removals:

   git commit -m "Cleanup: remove training/sample files from repo"

3) Push as usual (or open PR).


Option B: Rewrite history to purge large files (advanced, destructive)
-----------------------------------------------------------------
Use ONE of the following tools. Make sure all collaborators agree.

Using git filter-repo (recommended):

   pip install git-filter-repo  # or use distro package
   git filter-repo --invert-paths --path spk_cache/ --path data/
   # add more --path entries for specific large files

   # Review new history, then force push:
   git push --force-with-lease origin <branch>

Using BFG Repo-Cleaner:

   # Download BFG jar from https://rtyley.github.io/bfg-repo-cleaner/
   java -jar bfg.jar --delete-folders spk_cache --delete-folders data --no-blob-protection
   git reflog expire --expire=now --all && git gc --prune=now --aggressive
   git push --force-with-lease origin <branch>

Notes:
- Coordinate with collaborators before rewriting history.
- Update CI/build caches after force-pushing rewritten history.
DOC

