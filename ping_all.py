"""Wake Streamlit Community Cloud apps with a real browser.

An HTTP request is not enough for a sleeping Streamlit app: the sleeping page
requires a browser to press its wake button. This script deliberately treats a
redirect to Streamlit's login page as a failure, rather than claiming success.

For public apps, no secret is needed. Private apps require an already
authenticated Playwright storage state in the STREAMLIT_STORAGE_STATE secret.
Never put a password, Google credential, or storage-state JSON in this repo.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from playwright.async_api import (
    Browser,
    Error as PlaywrightError,
    Page,
    TimeoutError as PlaywrightTimeoutError,
    async_playwright,
)


# Edit this list to add or remove apps. Keep only app URLs here—never credentials.
TARGET_URLS = [
    "https://financedailynews-mobile.streamlit.app/",
    "https://financedailynews-web.streamlit.app/",
    "https://lyu-science-cloud.streamlit.app/",
    "https://ai-biology-lab.streamlit.app/",
    "https://ai-earthscience-lab.streamlit.app/",
    "https://finance-daily-news.streamlit.app/",
    "https://science-truth-portal.streamlit.app/",
    "https://science-ai-lab.streamlit.app/",
]

NAVIGATION_TIMEOUT_MS = 90_000
READY_TIMEOUT_MS = 120_000
MAX_ATTEMPTS = 2
RETRY_DELAY_SECONDS = 8


class AuthenticationRequired(RuntimeError):
    """The app is private and the runner has no valid Streamlit session."""


@dataclass
class WakeResult:
    url: str
    state: str
    detail: str
    elapsed_seconds: float


def safe_url(url: str) -> str:
    """Avoid emitting query strings that could contain a login payload."""
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def target_urls() -> list[str]:
    """Allow a manual workflow run to override targets without changing code."""
    supplied = os.environ.get("TARGET_URLS", "").strip()
    candidates = re.split(r"[\s,]+", supplied) if supplied else TARGET_URLS
    urls: list[str] = []
    for candidate in candidates:
        if not candidate:
            continue
        parts = urlsplit(candidate)
        if parts.scheme != "https" or not parts.netloc:
            raise ValueError(f"Only complete HTTPS URLs are allowed: {candidate!r}")
        urls.append(candidate)
    if not urls:
        raise ValueError("No target URLs were supplied.")
    return urls


def storage_state() -> dict[str, Any] | None:
    """Read an optional encrypted GitHub Secret without writing it to disk."""
    raw_state = os.environ.get("STREAMLIT_STORAGE_STATE", "").strip()
    if not raw_state:
        return None
    try:
        parsed = json.loads(raw_state)
    except json.JSONDecodeError as error:
        raise ValueError(
            "STREAMLIT_STORAGE_STATE is not valid Playwright storage-state JSON. "
            "Leave it unset for public apps."
        ) from error
    if not isinstance(parsed, dict):
        raise ValueError("STREAMLIT_STORAGE_STATE must be a JSON object.")
    return parsed


async def login_page_visible(page: Page) -> bool:
    """Detect Community Cloud's private-app login gate without logging its payload."""
    if "/-/login" in page.url:
        return True
    try:
        return await page.locator('a[href*="/-/login"]').count() > 0
    except PlaywrightError:
        return False


async def wait_for_running_app(page: Page) -> None:
    """Wait for Streamlit's application container and reject a sleeping/login page."""
    await page.wait_for_function(
        """
        () => {
          const text = document.body?.innerText || '';
          const sleeping = /gone to sleep due to inactivity/i.test(text);
          const app = document.querySelector(
            '[data-testid="stApp"], [data-testid="stAppViewContainer"]'
          );
          return Boolean(app) && !sleeping;
        }
        """,
        timeout=READY_TIMEOUT_MS,
    )


async def click_wake_button_if_needed(page: Page) -> bool:
    """Click the Community Cloud sleep-page button when it is present."""
    wake_button = page.get_by_role(
        "button", name=re.compile(r"yes,? get this app back up", re.IGNORECASE)
    )
    if await wake_button.count() == 0:
        return False
    await wake_button.first.click(timeout=15_000)
    return True


async def wake_once(browser: Browser, url: str, state: dict[str, Any] | None) -> WakeResult:
    started = perf_counter()
    context = await browser.new_context(storage_state=state)
    page = await context.new_page()
    try:
        try:
            response = await page.goto(url, wait_until="domcontentloaded", timeout=NAVIGATION_TIMEOUT_MS)
        except PlaywrightError as error:
            # Private Community Cloud apps can loop on /-/login before the page
            # reaches DOMContentLoaded. Surface that as an authentication issue.
            if await login_page_visible(page) or "ERR_TOO_MANY_REDIRECTS" in str(error):
                raise AuthenticationRequired(
                    "Streamlit login did not complete; the app is private and this runner has no valid session"
                ) from error
            raise
        if await login_page_visible(page):
            raise AuthenticationRequired(
                "redirected to Streamlit login; the app is private and this runner has no valid session"
            )

        clicked_wake = await click_wake_button_if_needed(page)
        if clicked_wake:
            await page.wait_for_timeout(1_000)
            if await login_page_visible(page):
                raise AuthenticationRequired(
                    "the wake button led to Streamlit login; a valid private-app session is required"
                )

        await wait_for_running_app(page)
        initial_status = response.status if response is not None else "no response"
        state_label = "woke sleeping app" if clicked_wake else "already running"
        return WakeResult(
            safe_url(url), state_label, f"initial HTTP status: {initial_status}", perf_counter() - started
        )
    finally:
        await context.close()


async def wake_target(browser: Browser, url: str, state: dict[str, Any] | None) -> WakeResult:
    last_error: Exception | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            result = await wake_once(browser, url, state)
            print(f"OK  {result.url} — {result.state} ({result.elapsed_seconds:.1f}s; {result.detail})")
            return result
        except AuthenticationRequired as error:
            # Retrying cannot create a login session and only hides the real problem.
            last_error = error
            break
        except (PlaywrightTimeoutError, PlaywrightError, RuntimeError) as error:
            last_error = error
            if attempt < MAX_ATTEMPTS:
                print(f"RETRY {safe_url(url)} — attempt {attempt}/{MAX_ATTEMPTS}: {error}")
                await asyncio.sleep(RETRY_DELAY_SECONDS)

    assert last_error is not None
    result = WakeResult(safe_url(url), "failed", str(last_error), 0)
    print(f"FAIL {result.url} — {result.detail}")
    return result


def write_summary(results: list[WakeResult]) -> None:
    """Publish a compact diagnostic table in the GitHub Actions job summary."""
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return
    lines = [
        "## Streamlit keep-alive result",
        "",
        "| App | Result | Detail |",
        "| --- | --- | --- |",
    ]
    for result in results:
        detail = result.detail.replace("|", "\\|")
        lines.append(f"| {result.url} | {result.state} | {detail} |")
    Path(summary_path).write_text("\n".join(lines) + "\n", encoding="utf-8")


async def main() -> int:
    try:
        urls = target_urls()
        state = storage_state()
    except ValueError as error:
        print(f"CONFIGURATION ERROR: {error}", file=sys.stderr)
        return 2

    print(f"Starting browser-based keep-alive for {len(urls)} app(s).")
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        try:
            # Wake targets concurrently so a cluster of sleeping apps cannot make
            # the scheduled job exceed its timeout while waiting one-by-one.
            results = await asyncio.gather(
                *(wake_target(browser, url, state) for url in urls)
            )
        finally:
            await browser.close()

    write_summary(results)
    failed = [result for result in results if result.state == "failed"]
    if failed:
        print(f"{len(failed)}/{len(results)} app(s) failed. The workflow is intentionally marked failed.")
        return 1
    print(f"All {len(results)} app(s) are running.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
