# Streamlit keep-alive

This repository keeps Streamlit Community Cloud apps awake with Chromium, not a
simple HTTP request. If an app is asleep, it clicks Streamlit's wake button and
waits for the actual Streamlit app container to appear.

For private apps, the recommended option is the **Mac mini Chrome runner** below.
It uses your normal Chrome session on that Mac and never asks Google to sign in
through an automation browser.

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

## Recommended: use normal Google Chrome on your Mac mini

This needs no Python, Chromium, GitHub Secret, or automated Google login.
First, open Google Chrome normally on the Mac mini and sign in to Streamlit as
you usually do, completing two-step verification if requested. Leave Chrome
signed in. That Mac must be configured not to sleep
while it is plugged in.

1. Open the apps you want to maintain in Chrome manually, completing two-step
   verification where required. Then test the Chrome visit script. It refreshes
   existing app tabs only; it deliberately never creates a new tab or changes
   your active app:

   ```sh
   osascript chrome_keep_alive.applescript
   ```

   If an app is already sleeping, Chrome will show Streamlit's sleeping page.
   Click its wake button manually once. Subsequent six-hour Chrome refreshes
   keep the app active without an automated login.

2. Enable the six-hour macOS schedule. Copy
   `launchd/com.user.streamlit-keep-alive.plist` to
   `~/Library/LaunchAgents/com.user.streamlit-keep-alive.plist`, then replace
   every `__REPOSITORY__` with the complete repository path and every `__HOME__`
   with your macOS home-folder path. Load and test it:

   ```sh
   launchctl bootout gui/$(id -u) "$HOME/Library/LaunchAgents/com.user.streamlit-keep-alive.plist" 2>/dev/null || true
   launchctl bootstrap gui/$(id -u) "$HOME/Library/LaunchAgents/com.user.streamlit-keep-alive.plist"
   launchctl kickstart -k gui/$(id -u)/com.user.streamlit-keep-alive
   ```

   Logs are kept only on the Mac mini in `~/Library/Logs/streamlit-keep-alive.log`
   and `~/Library/Logs/streamlit-keep-alive-error.log`. If the Chrome session
   expires, sign in normally in Chrome again.

## Managing targets

Edit `TARGET_URLS` near the top of `ping_all.py`. A manual workflow run can
temporarily replace the list by filling in **target_urls** with one or more
HTTPS URLs separated by spaces or commas.
