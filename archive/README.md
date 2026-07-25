Archived preview and build artifacts

This folder documents preview pages and build artifacts that were removed from the main release tree to keep the release focused on research source, data, and documentation.

Files and folders that were archived (removed from top-level):

- `benchmark/` — interactive benchmark HTML harnesses (preview pages removed)
- `dashboard/` — offline dashboard visualizations
- `dist/` — compiled WebAssembly and JS loader (recreated by `make all`)
- `index.html`, `RELEASE.html` — project preview pages

Why archived?
- These files were primarily for interactive previews and committed build artifacts. To keep the release lean and review-friendly, they were removed from the top-level. They remain available in the git history and tags.

How to recover
- To restore a removed file from the repository history, run:

```bash
# show commits that touched the file (example)
git log -- repo-release/benchmark/pure-js.html

# restore a specific file from the last commit that contained it
git checkout HEAD~1 -- repo-release/benchmark/pure-js.html
```

If you prefer these assets to be kept in-tree, tell us and we will move them into this `archive/` directory instead of removing them.
