# Deploying Paid Off Clothes

Nothing here has been deployed. This is the prepared setup and the exact steps left, in order.

## Why this shape

The app is pure Python standard library and stores everything in **one SQLite file**. That single
fact drives every decision below:

- **A persistent volume is mandatory.** Vercel, Netlify, Cloudflare Workers and GitHub Pages have
  ephemeral filesystems — the database would vanish on every deploy. They are not options.
- **Exactly one machine.** Two instances would either fail to mount the volume or mount separate
  copies and silently diverge. `fly.toml` pins this; do not add machines.
- **No build step.** No `pip install`, no bundler. The image is Python plus ~5MB of site.

## What lives where

| | |
|---|---|
| **Image** (rebuilt each deploy) | `index.html`, `script.js`, `styles.css`, `admin.html`, `fonts/`, `db/*.py`, a seed copy of the catalogue and photos |
| **Volume** at `/data` (survives deploys) | `paidoff.db`, `admin_auth.json`, uploaded `images/`, `backups/`, the JSON projections |

`POC_DATA_DIR` selects between them. Unset locally, so running `python3 server.py` on your laptop
behaves exactly as it always has.

`bootstrap()` seeds an empty volume once on first boot and never overwrites it afterwards. That is
what makes a redeploy safe: verified by placing an order, editing stock, uploading a photo,
restarting, and confirming all three survived while the shipped catalogue did not clobber them.

## Environments

| | Production | Staging |
|---|---|---|
| Config | `fly.toml` | `fly.staging.toml` |
| App | `paid-off-clothes` | `paid-off-clothes-staging` |
| Volume | `poc_data` | `poc_data_staging` (separate — test orders can never reach the real shop) |
| Machines | 1 always on | 1 always on (min_machines_running=1, kept warm for reviewers) |
| Deploys | manual approval | automatic on push |

## Secrets

Never in `fly.toml`, never in the repo. Set them with:

    fly secrets set NAME=value -a paid-off-clothes

They are encrypted at rest and injected as environment variables. `.dockerignore` also keeps
`admin_auth.json`, the database and every data file out of the image.

**The admin password is not a deploy secret.** It is set through the dashboard on first visit and
stored on the volume as a PBKDF2 hash, per environment.

## Backups

A volume is **not** a backup — Fly volumes live on one physical host.

    python3 db/backup.py                 timestamped snapshot into backups/
    python3 db/backup.py --stdout        stream a snapshot (used by CI)
    python3 db/backup.py --verify FILE   confirm it opens and holds a catalogue
    python3 db/backup.py --prune 30      delete local snapshots older than 30 days

Uses SQLite's backup API, not a file copy: copying a live database can capture it mid-transaction
and yield a file that will not open. Verification rejects truncated files, corrupted pages,
non-databases, and — the case that would otherwise pass silently — a structurally valid database
with an empty catalogue.

Pull one off the machine any time:

    fly ssh console -a paid-off-clothes -C "python3 /app/db/backup.py --stdout" > backup.sqlite

The deploy workflow also takes one before every production deploy and keeps it as a build artifact
for 30 days.

## Restoring

    fly scale count 0 -a paid-off-clothes          # stop writes first
    fly ssh sftp shell -a paid-off-clothes         # put backup.sqlite /data/paidoff.db
    fly scale count 1 -a paid-off-clothes

Then check the admin Orders tab and the storefront product count.

## Steps left, in order

Each needs your account, your card, or your approval — which is why none of them have been done.

1. `fly auth login`
2. `fly apps create paid-off-clothes-staging`
3. `fly volumes create poc_data_staging --size 1 -a paid-off-clothes-staging`
4. `fly deploy --config fly.staging.toml` — **staging only**, nothing public
5. Check staging, set its admin password, place a test order
6. Repeat 2–4 for production when you are satisfied
7. Create a Fly deploy token and add it to GitHub as `FLY_API_TOKEN`
8. Add a `production` environment in GitHub with yourself as a required reviewer

## Not done on purpose

- No apps created, no volumes, no deploy, no domain, no DNS.
- **Card entry has been removed** from checkout. Orders reserve stock for 30 minutes and the buyer
  is told to DM to settle up. Collecting card numbers into fields that discard them is the one
  genuinely unsafe thing this site could do.
