# Job Digest Monitor

Daily GitHub Actions cron that watches SimplifyJobs listing repos and files a filtered
digest of newly opened US/remote SWE-adjacent roles as a GitHub Issue in this repo.
Zero server, zero secrets — uses the built-in `GITHUB_TOKEN`.

## Data source

Both repos generate their READMEs from a machine-written `listings.json` on the `dev`
branch (updated hourly). This tool reads that JSON directly — verified paths:

- `https://raw.githubusercontent.com/SimplifyJobs/Summer2026-Internships/dev/.github/scripts/listings.json`
- `https://raw.githubusercontent.com/SimplifyJobs/New-Grad-Positions/dev/.github/scripts/listings.json`

## How it works

- `state/seen.json` holds every listing `id` (UUID) already processed. Dedup is on `id` only.
- New = `active && is_visible && id not in seen`. All new ids are persisted (matched or
  not) and committed back by the workflow, so nothing is ever re-reported.
- **First run seeds** all current active ids and posts a one-line "seeded" issue instead
  of dumping hundreds of roles. Real digests start the next day.
- Filters (config block at top of [monitor.py](monitor.py)):
  - **Title** allow-list (SWE/ML/AI/data/quant/infra/backend/full-stack) with a small
    deny-list (hardware/PM/design).
  - **Location**: US or remote only. A role passes if any of its locations is US-based.
  - **Sponsorship**: never filtered, only tagged — `⛔ no sponsorship`,
    `⛔ citizenship required`, `✅ sponsors` (the common value `Other` gets no tag).

## Deploy

```sh
git remote add origin https://github.com/<you>/job-digest.git
git push -u origin main
```

Then make sure you receive email for your own repo activity:
GitHub → Settings → Notifications → "Participating" email on (issues you're subscribed
to in your own repo email you by default). Run it once manually via
Actions → Daily job digest → Run workflow to trigger the seed.

## Notes

- Digest is also written to the Actions run summary page.
- GitHub disables cron workflows after 60 days without repo activity; the daily state
  commit keeps it alive.
- Run locally with `python monitor.py` — without `GITHUB_TOKEN` it prints the digest
  to stdout instead of filing an issue.
