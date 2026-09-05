"""Keep private Streamlit apps awake from a Mac that is already signed in.

Run ``python mac_keep_alive.py --login`` once on the Mac mini to sign in through
the visible Chromium window. Later scheduled runs use the same local browser
profile in headless mode. The authenticated session stays on that Mac; it is
never copied to GitHub, a secret manager, or this repository.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path
from time import perf_counter
from typing import Any

from playwright.async_api import (
    BrowserContext,
    Error as PlaywrightError,
    Page,
    TimeoutError as PlaywrightTimeoutError,
    async_playwright,
)

from ping_all import (
    MAX_ATTEMPTS,
    NAVIGATION_TIMEOUT_MS,
    READY_TIMEOUT_MS,
    RETRY_DELAY_SECONDS,
    AuthenticationRequired,
    WakeResult,
    click_wake_button_if_needed,
    login_page_visible,
    safe_url,
    target_urls,
    wait_for_running_app,
)


DEFAULT_PROFILE_DIR = (
    Path.home() / "Library" / "Application Support" / "StreamlitKeepAlive"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--login",
        action="store_true",
        help="Open Chromium visibly so you can sign in to Streamlit once.",
    )
    return parser.parse_args()


def profile_dir() -> Path:
    configured = os.environ.get("STREAMLIT_KEEP_ALIVE_PROFILE", "").strip()
    return Path(configured).expanduser() if configured else DEFAULT_PROFILE_DIR


async def wake_once(context: BrowserContext, url: str) -> WakeResult:
    started = perf_counter()
    page = await context.new_page()
    try:
        try:
            response = await page.goto(
                url, wait_until="domcontentloaded", timeout=NAVIGATION_TIMEOUT_MS
            )
        except PlaywrightError as error:
            if await login_page_visible(page) or "ERR_TOO_MANY_REDIRECTS" in str(error):
                raise AuthenticationRequired(
                    "Streamlit login did not complete; run this Mac's --login setup again"
                ) from error
            raise

        if await login_page_visible(page):
            raise AuthenticationRequired(
                "redirected to Streamlit login; run this Mac's --login setup again"
            )

        clicked_wake = await click_wake_button_if_needed(page)
        if clicked_wake:
            await page.wait_for_timeout(1_000)
            if await login_page_visible(page):
                raise AuthenticationRequired(
                    "the wake button led to Streamlit login; run this Mac's --login setup again"
                )

        await wait_for_running_app(page)
        initial_status = response.status if response is not None else "no response"
        state = "woke sleeping app" if clicked_wake else "already running"
        return WakeResult(
            safe_url(url), state, f"initial HTTP status: {initial_status}", perf_counter() - started
        )
    finally:
        await page.close()


async def wake_target(context: BrowserContext, url: str) -> WakeResult:
    last_error: Exception | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            result = await wake_once(context, url)
            print(f"OK   {result.url} — {result.state} ({result.elapsed_seconds:.1f}s)")
            return result
        except AuthenticationRequired as error:
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


async def establish_login(context: BrowserContext, urls: list[str]) -> int:
    page = await context.new_page()
    try:
        print("A Chromium window is open. Complete Streamlit/Google login there.")
        print("When you reach the Streamlit workspace, return here and press Return.")
        await page.goto(
            "https://share.streamlit.io", wait_until="domcontentloaded", timeout=NAVIGATION_TIMEOUT_MS
        )
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None, input, "Press Return after you have finished signing in: "
        )
        await page.goto(urls[0], wait_until="domcontentloaded", timeout=NAVIGATION_TIMEOUT_MS)
        if await login_page_visible(page):
            print("Login is still required. Nothing was saved outside this Mac.", file=sys.stderr)
            return 1
        await wait_for_running_app(page)
        print("Login saved in this Mac's dedicated StreamlitKeepAlive browser profile.")
        return 0
    finally:
        await page.close()


async def main() -> int:
    args = parse_args()
    urls = target_urls()
    profile = profile_dir()
    profile.parent.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as playwright:
        context = await playwright.chromium.launch_persistent_context(
            user_data_dir=str(profile),
            headless=not args.login,
        )
        try:
            if args.login:
                return await establish_login(context, urls)

            print(f"Using local browser profile: {profile}")
            results = await asyncio.gather(*(wake_target(context, url) for url in urls))
        finally:
            await context.close()

    failures = [result for result in results if result.state == "failed"]
    if failures:
        print(f"{len(failures)}/{len(results)} app(s) failed.")
        return 1
    print(f"All {len(results)} app(s) are running.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
