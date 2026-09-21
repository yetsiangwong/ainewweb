# AI Signal Daily

An English, presentation-ready website for a daily global AI news briefing.

## What it does

- Shows the latest AI news briefing in a tech-style dashboard layout.
- Keeps previous daily briefings in the archive.
- Updates automatically every day at 08:00 Malaysia time using GitHub Actions.
- Deploys to GitHub Pages, so the website stays online even when your computer is off.

## How to publish it

1. Create a new GitHub repository.
2. Upload every file in this folder to the repository root.
3. In the GitHub repository, open `Settings` → `Pages`.
4. Under `Build and deployment`, set `Source` to `GitHub Actions`.
5. Open the `Actions` tab.
6. Run `Update AI Signal Daily` manually once.
7. After it finishes, GitHub will show the website URL in the workflow summary.

## Daily update schedule

The workflow uses:

```yaml
cron: "0 0 * * *"
```

GitHub Actions cron is UTC, so this runs at `08:00` in Malaysia.

## Editing content manually

Edit `data/news.json` if you want to revise a story, add class notes, or remove an item before presenting.

## Files

- `index.html` - website structure
- `styles.css` - tech-style presentation design
- `app.js` - renders the briefing and archive
- `data/news.json` - current and archived news data
- `scripts/update_site.py` - daily RSS/news updater
- `.github/workflows/update-ai-news-site.yml` - GitHub Pages deployment workflow
