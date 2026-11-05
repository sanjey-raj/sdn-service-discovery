# Finish the submission

1. Add team member names and roll numbers in docs/REPORT.md.
2. Publish to your own GitHub repository and put its URL into the report.
3. Include the source, docs and selected measured results; results/ is ignored
   by .gitignore, so explicitly stage evidence as shown below.
4. Read docs/DEMO.md and practice explaining advertisements, expiry, correlation,
   priorities, controller choice and the measured latency overhead.

Do not overwrite your working folder without a backup. The updated package
preserves the original source and adds analysis/documentation. The core application
was not changed for these measurements.

From the project root, after creating an empty GitHub repository:

```bash
git init
git add .
git add -f results
git status
```

Review the staged files, then use the README commit/remote/push instructions.
Raw results contain lab addresses and local path metadata; inspect before making
public. Do not stage Unix sockets or caches. Only fill in Git identity when Git
asks, using your own name and email. No credentials belong in the source.
