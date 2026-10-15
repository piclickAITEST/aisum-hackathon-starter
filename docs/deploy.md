# Deploy to Cloud Run — checkpoints 5 and 6

Do this after [checkpoints 0–4](setup.md) work on localhost.

## Checkpoint 5 — deploy

The project must listen on the port Cloud Run gives it and bind to `0.0.0.0`. The
included `Procfile` does both through Uvicorn.

You need the Google Cloud CLI (`gcloud`) — [install it](https://cloud.google.com/sdk/docs/install),
or use Cloud Shell in the browser where it is already installed.

**Windows** — run the installer, then:

1. Leave the options that add `gcloud` to your `PATH` checked. If `gcloud` is still not
   found in a **new** PowerShell window, add it for that window —
   [troubleshooting](troubleshooting.md#gcloud-not-found) has the command.
2. The installer ends by opening `gcloud init`. Sign in with the Google account you gave
   the organizers, and when it asks you to pick a project, choose your **team's
   project** — not "Create a new project" and not a personal one.

Check with `gcloud --version`. Then sign in and select your team's project (same on every
OS; on Windows this repeats what `gcloud init` did, which is fine):

```bash
gcloud auth login
gcloud config set project <your-team-project-id>
gcloud config get-value project     # should print your team's project
```

If the deploy below fails with `IAM_PERMISSION_DENIED`, see
[troubleshooting](troubleshooting.md#iam_permission_denied-when-deploying).

Cloud Run does not read `.env`. Turn it into `env.yaml` (ignored by git, and not
uploaded with the source), then deploy with that file. This keeps the keys out of
your shell history.

**macOS / Linux** — the first line puts `gcloud` on `PATH` for this terminal. Change the
folder if you unpacked the SDK somewhere other than your home folder; skip the line if
you installed with Homebrew.

```bash
export PATH="$HOME/google-cloud-sdk/bin:$PATH"

grep -E '^[A-Z_]+=' .env | sed -E 's/^([A-Z_]+)=(.*)$/\1: "\2"/' > env.yaml

gcloud run deploy app \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --env-vars-file env.yaml
```

**Windows (PowerShell)** — the line break is a backtick (`` ` ``), not `\`. The first line
puts `gcloud` on `PATH` for this window; it does no harm if it is already there.

```powershell
$env:PATH += ";$env:LOCALAPPDATA\Google\Cloud SDK\google-cloud-sdk\bin"

Get-Content .env | Where-Object { $_ -match '^[A-Z_]+=' } | ForEach-Object {
  $k, $v = $_ -split '=', 2; "${k}: `"$($v.Trim())`"" } | Set-Content env.yaml

gcloud run deploy app `
  --source . `
  --region us-central1 `
  --allow-unauthenticated `
  --env-vars-file env.yaml
```

**It is working when:** `gcloud` prints a `Service URL: https://...run.app` line and
opening that URL shows the starter page with the sign-in button.

`--allow-unauthenticated` is required. Without it the URL answers `403 Forbidden` —
the deploy succeeded, but Cloud Run refuses anyone who is not signed in to your Google
Cloud project, which includes every user of your app. Your app still requires its own
Google sign-in for every `/api/*` call ([why](setup.md#why-sign-in-is-required)).

## Checkpoint 6 — the deployed copy

On the Cloud Run URL, repeat [checkpoints 1–4](setup.md).

**It is working when:** the deployed copy can sign in, call the four product tools, and
return one LLM response just like localhost.

If sign-in works on localhost but the deployed page shows `auth/unauthorized-domain`,
the new `run.app` address is not yet on the Firebase project's list of allowed sign-in
domains. AISUM owns the Firebase projects and adds deployed addresses for you; if the
error is still there some time after your first deploy, tell the organizers the URL.
