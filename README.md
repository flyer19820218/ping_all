# Streamlit keep-alive

This repository keeps Streamlit Community Cloud apps awake with Chromium, not a
simple HTTP request. If an app is asleep, it clicks Streamlit's wake button and
waits for the actual Streamlit app container to appear.

## Why the previous workflow reported success when it had not worked

The old script used `requests.get()`. It could neither click the sleeping-page
button nor sign in to a private app. It also completed with exit code zero even
when every target failed, so GitHub Actions displayed a green check incorrectly.
Its hourly commits were unrelated to the target apps and have been removed.

## Schedule

The workflow runs every four hours at minute 17 UTC. Community Cloud sleeps apps
after 12 hours without traffic, so this leaves a sizeable margin and avoids the
top of the hour, when GitHub Actions scheduled runs can be delayed.

Use **Actions → Browser-based Streamlit keep-alive → Run workflow** to run it
immediately. The job summary names every target as `already running`, `woke
sleeping app`, or `failed`. Any failure makes the workflow fail visibly.

## Private apps

The targets currently redirect unauthenticated visitors to Streamlit's
`/-/login` route. This is correct for a private app, but it means an automated
GitHub runner cannot wake it without an authenticated session.

Do **not** add a Google password, Streamlit password, student data, Drive
credentials, or a session file to this repository. The workflow accepts the
optional `STREAMLIT_STORAGE_STATE` GitHub Secret for a Playwright storage-state
JSON only. If that secret is not configured, public apps work normally and
private targets intentionally fail with an explicit login-required message.

Before adding such a session secret, consider its impact carefully: it grants
the runner the same app-viewing access as that browser session and may expire.
For sensitive grade apps, it is safer to let them sleep than to give a cloud
automation runner an authenticated session.

## Managing targets

Edit `TARGET_URLS` near the top of `ping_all.py`. A manual workflow run can
temporarily replace the list by filling in **target_urls** with one or more
HTTPS URLs separated by spaces or commas.
