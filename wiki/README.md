# Wiki sources

These Markdown files are the ClipsFlow wiki, kept in-repo so they version with
the code and can be reviewed in PRs. They use the GitHub wiki layout
(`Home.md` landing page, `_Sidebar.md` navigation, page names as links).

## Publish to the GitHub wiki

The GitHub wiki is a separate git repo. To publish these pages to it:

```bash
# Enable the wiki once in repo Settings → Features → Wikis, and create the
# first page in the UI so the wiki repo exists.
git clone https://github.com/FriskyDevelopments/ClipsFlow.wiki.git
cp wiki/*.md ClipsFlow.wiki/
cd ClipsFlow.wiki && git add -A && git commit -m "Sync wiki from main repo" && git push
```

Relative links to `../README.md`, `../SPEC.md`, `../DEPLOY.md` resolve when
browsing the folder in the repo; when published to the GitHub wiki, point
those at the repo's blob URLs instead, or move the canonical docs into the
wiki.
