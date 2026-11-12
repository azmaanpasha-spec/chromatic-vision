"""
End-to-end UI check + screenshot capture (development tool, not needed to run the app).

Requires:  pip install playwright   (uses the installed Microsoft Edge, no browser download)
Usage:     streamlit run app.py      (in another terminal)
           python scripts/capture_screenshots.py [--mobile]

The script clicks through every page like a user, runs the sample image and
video demos, uploads an invalid file, triggers downloads and saves
screenshots to report/screenshots/. It prints PASS/FAIL lines for each check.
"""

from __future__ import annotations

import os
import sys
import time

from playwright.sync_api import Page, sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOTS = os.path.join(ROOT, "report", "screenshots")
DL_DIR = os.path.join(ROOT, "outputs", "e2e_downloads")
URL = "http://localhost:8501"
results = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}")


def settle(page: Page, extra: float = 0.8) -> None:
    """Wait until Streamlit finished re-running the script."""
    time.sleep(0.4)
    for _ in range(600):
        if page.locator('[data-testid="stStatusWidget"]').count() == 0:
            break
        time.sleep(0.25)
    time.sleep(extra)


def shot(page: Page, name: str, full: bool = True) -> None:
    """Screenshot. Streamlit scrolls inside its own container, so for a full-page
    capture the viewport is temporarily enlarged to the content height."""
    if not full:
        page.screenshot(path=os.path.join(SHOTS, name))
        return
    vp = page.viewport_size
    height = page.evaluate(
        "Math.max(...Array.from(document.querySelectorAll('[data-testid=stMain], section.main, "
        "[data-testid=stAppViewContainer]')).map(e => e.scrollHeight), 900)")
    page.set_viewport_size({"width": vp["width"], "height": min(int(height) + 40, 7000)})
    time.sleep(1.2)
    page.screenshot(path=os.path.join(SHOTS, name))
    page.set_viewport_size(vp)
    time.sleep(0.5)


def nav(page: Page, label: str) -> None:
    page.locator('section[data-testid="stSidebar"] button', has_text=label).first.click()
    settle(page)


def choose(page: Page, option: str) -> None:
    """Pick an option in the first selectbox of the main area."""
    box = page.locator('[data-testid="stMain"] [data-testid="stSelectbox"] input').first
    box.click()
    box.fill(option)
    page.keyboard.press("Enter")
    settle(page)


def main_text(page: Page) -> str:
    return page.locator('[data-testid="stMain"]').inner_text()


def run(mobile: bool = False) -> int:
    os.makedirs(SHOTS, exist_ok=True)
    os.makedirs(DL_DIR, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        if mobile:
            ctx = browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2,
                                      is_mobile=True, has_touch=True)
        else:
            ctx = browser.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=1,
                                      accept_downloads=True)
        page = ctx.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(URL)
        page.wait_for_selector("text=Chromatic Vision", timeout=60000)
        settle(page, 1.5)

        if mobile:
            time.sleep(2)
            shot(page, "mobile_overview.png")
            page.goto(URL + "/?page=image")
            page.wait_for_selector("text=Image Analysis Studio", timeout=60000)
            settle(page, 2.5)
            shot(page, "mobile_image_studio.png")
            overflow = page.evaluate("document.documentElement.scrollWidth > window.innerWidth + 1")
            check("Mobile: no horizontal overflow", not overflow)
            browser.close()
            return 0

        # 1. Overview ------------------------------------------------------
        check("Overview renders", "Total Images Analysed" in main_text(page))
        shot(page, "01_overview.png")

        # 2. Navigation through every page ------------------------------------
        for label, marker in [("Image Analysis", "Image Analysis Studio"), ("Video Tracking", "Video Tracking Studio"),
                              ("Analytics & Insights", "No analytics yet"), ("About Project", "About the Project"),
                              ("Overview", "Session statistics")]:
            nav(page, label)
            try:
                page.wait_for_selector(f"text={marker}", timeout=10000)
            except Exception:
                pass
            check(f"Navigate to {label}", marker in main_text(page))
        nav(page, "Analytics & Insights")
        shot(page, "05_analytics_empty.png", full=False)
        nav(page, "Image Analysis")
        shot(page, "02_image_empty.png", full=False)

        # 3. Image demo (sample image, red) -------------------------------------
        nav(page, "Overview")
        page.get_by_role("button", name="Try Sample Image Demo").click()
        settle(page, 1.5)
        text = main_text(page)
        check("Sample image demo detects 3 red objects", "Detected: 3 red object(s)" in text)
        shot(page, "03_image_results.png")

        # Mask and morphology tabs
        page.get_by_role("tab", name="Mask & segmentation").click()
        settle(page, 0.6)
        page.locator('[data-testid="stTabs"]').first.screenshot(path=os.path.join(SHOTS, "03b_mask_tab.png"))
        page.get_by_role("tab", name="Morphology pipeline").click()
        settle(page, 0.6)
        page.locator('[data-testid="stTabs"]').first.screenshot(path=os.path.join(SHOTS, "03c_morphology_tab.png"))

        # Download processed image
        with page.expect_download() as dl_info:
            page.get_by_role("button", name="Processed image").click()
        dl = dl_info.value
        target = os.path.join(DL_DIR, dl.suggested_filename)
        dl.save_as(target)
        check("Download processed image", os.path.getsize(target) > 1000, dl.suggested_filename)

        # Blue on the same image
        page.locator('[data-testid="stButtonGroup"] button', has_text="Blue").first.click()
        settle(page)
        page.get_by_role("button", name="Analyze Image").click()
        settle(page, 1.2)
        check("Blue detection on sample (expect 3)", "Detected: 3 blue object(s)" in main_text(page))

        # Green on ball collection
        choose(page, "ball_collection.jpg")
        settle(page)
        page.locator('[data-testid="stButtonGroup"] button', has_text="Green").first.click()
        settle(page)
        page.get_by_role("button", name="Analyze Image").click()
        settle(page, 1.2)
        check("Green detection on ball_collection (expect 2)", "Detected: 2 green object(s)" in main_text(page))

        # No-match image
        choose(page, "neutral_scene.png")
        settle(page)
        page.get_by_role("button", name="Analyze Image").click()
        settle(page, 1.2)
        text = main_text(page)
        check("No matching colour shows info message", "No green objects were found" in text)
        shot(page, "04_image_no_match.png", full=False)

        # Invalid upload
        page.locator('[data-testid="stButtonGroup"] button', has_text="Upload image").first.click()
        settle(page)
        bad = os.path.join(DL_DIR, "not_an_image.png")
        with open(bad, "wb") as fh:
            fh.write(b"this is plain text, not a PNG")
        page.locator('input[type="file"]').set_input_files(bad)
        settle(page, 1.2)
        check("Invalid image upload shows error", "Invalid image" in main_text(page))
        shot(page, "04b_invalid_upload.png", full=False)

        # Real upload of a sample file through the uploader
        page.locator('input[type="file"]').set_input_files(
            os.path.join(ROOT, "assets", "sample_images", "ball_collection.jpg"))
        settle(page, 1.2)
        page.locator('[data-testid="stButtonGroup"] button', has_text="Red").first.click()
        settle(page)
        page.get_by_role("button", name="Analyze Image").click()
        settle(page, 1.2)
        check("Uploaded JPG: red detection (expect 4)", "Detected: 4 red object(s)" in main_text(page))

        # 4. Video demo ---------------------------------------------------------
        nav(page, "Overview")
        page.get_by_role("button", name="Try Sample Video Demo").click()
        page.wait_for_selector("text=Tracking results", timeout=180000)
        settle(page, 2.0)
        text = main_text(page)
        check("Video demo processed 200 frames", "200" in text and "Frames processed" in text)
        check("Video demo: 2 unique track IDs", "Unique track IDs\n2" in text or "Unique track IDs\n\n2" in text)
        shot(page, "06_video_results.png")

        with page.expect_download() as dl_info:
            page.get_by_role("button", name="Processed video (WebM)").click()
        dl = dl_info.value
        target = os.path.join(DL_DIR, dl.suggested_filename)
        dl.save_as(target)
        check("Download processed video (WebM)", os.path.getsize(target) > 10000, dl.suggested_filename)
        with page.expect_download() as dl_info:
            page.get_by_role("button", name="Processed video (MP4)").click()
        dl = dl_info.value
        target_mp4 = os.path.join(DL_DIR, dl.suggested_filename)
        dl.save_as(target_mp4)
        check("Download processed video (MP4)", os.path.getsize(target_mp4) > 10000, dl.suggested_filename)

        # 5. Analytics with data --------------------------------------------------
        nav(page, "Analytics & Insights")
        settle(page, 1.5)
        check("Analytics shows image metrics", "Detection percentage" in main_text(page))
        shot(page, "07_analytics_image.png")
        page.get_by_role("tab", name="Video analytics").click()
        settle(page, 1.5)
        check("Analytics shows video metrics", "Avg processing / frame" in main_text(page))
        shot(page, "08_analytics_video.png")
        page.get_by_role("tab", name="Session history").click()
        settle(page, 1.0)
        shot(page, "08b_session_history.png", full=False)

        # 6. Dashboard statistics -----------------------------------------------
        nav(page, "Overview")
        text = main_text(page)
        check("Dashboard statistics updated", "Total Images Analysed\n5" in text
              and "Total Videos Processed\n1" in text, "(5 image runs, 1 video run expected)")
        shot(page, "09_overview_after.png", full=False)

        # 7. About page -------------------------------------------------------
        nav(page, "About Project")
        shot(page, "10_about.png", full=False)
        page.get_by_role("tab", name="Architecture").click()
        settle(page, 0.8)
        shot(page, "11_about_architecture.png")
        page.get_by_role("tab", name="Techniques").click()
        settle(page, 0.8)
        shot(page, "12_about_techniques.png")

        # 8. Video studio upload of AVI ------------------------------------------
        nav(page, "Video Tracking")
        page.locator('[data-testid="stButtonGroup"] button', has_text="Upload video").first.click()
        settle(page)
        page.locator('input[type="file"]').set_input_files(
            os.path.join(ROOT, "assets", "sample_videos", "orbiting_ball.avi"))
        settle(page, 2.0)
        text = main_text(page)
        check("AVI upload shows video info (120 frames, 30 fps)", "120" in text and "30.00" in text)
        shot(page, "13_video_upload_info.png", full=False)

        check("No JavaScript page errors", not errors, "; ".join(errors[:3]))
        browser.close()

    failed = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(run(mobile="--mobile" in sys.argv))
