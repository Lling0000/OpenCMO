"""Capture all screenshots and GIFs for README documentation.

Requires: playwright, sqlite3, ffmpeg (for GIFs)
Usage: Start opencmo-web first, then run this script.
"""

from playwright.sync_api import sync_playwright
import json
import os
import sqlite3
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path

SCREENSHOTS_DIR = "assets/screenshots"
DB_PATH = Path.home() / ".opencmo" / "data.db"
BASE_URL = "http://localhost:8080/app"
PROJECT_ID = 24  # Existing OpenCMO project

os.makedirs(SCREENSHOTS_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# Phase 1: Seed realistic demo data into the DB
# ---------------------------------------------------------------------------


def seed_demo_data():
    """Insert rich demo data so all pages render with charts and content."""
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()

    pid = PROJECT_ID
    now = datetime.utcnow()

    # --- SEO scans (7 data points showing improvement, scores are 0-1 fractions) ---
    c.execute("DELETE FROM seo_scans WHERE project_id = ?", (pid,))
    seo_data = [
        (0.72, 3.2, 0.18, 450),
        (0.76, 2.8, 0.15, 380),
        (0.80, 2.4, 0.12, 320),
        (0.84, 2.1, 0.09, 270),
        (0.87, 1.8, 0.06, 220),
        (0.90, 1.5, 0.04, 180),
        (0.93, 1.2, 0.02, 150),
    ]
    for i, (perf, lcp, cls, tbt) in enumerate(seo_data):
        ts = (now - timedelta(days=len(seo_data) - 1 - i)).strftime("%Y-%m-%d %H:%M:%S")
        report = json.dumps({
            "lighthouseResult": {
                "categories": {"performance": {"score": perf}},
                "audits": {
                    "largest-contentful-paint": {"numericValue": lcp * 1000},
                    "cumulative-layout-shift": {"numericValue": cls},
                    "total-blocking-time": {"numericValue": tbt},
                },
            },
            "has_robots_txt": True,
            "has_sitemap": True,
            "has_schema_org": True,
        })
        c.execute(
            "INSERT INTO seo_scans (project_id, url, scanned_at, report_json, score_performance, score_lcp, score_cls, score_tbt, has_robots_txt, has_sitemap, has_schema_org) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, 1, 1)",
            (pid, "https://github.com/Lling0000/OpenCMO", ts, report, perf, lcp, cls, tbt),
        )

    # --- GEO scans (7 data points) ---
    c.execute("DELETE FROM geo_scans WHERE project_id = ?", (pid,))
    geo_data = [
        (28, 30, 25, 40),
        (35, 38, 32, 45),
        (42, 45, 40, 52),
        (50, 55, 48, 58),
        (58, 62, 55, 65),
        (65, 70, 60, 72),
        (72, 78, 68, 80),
    ]
    for i, (geo, vis, pos, sent) in enumerate(geo_data):
        ts = (now - timedelta(days=len(geo_data) - 1 - i)).strftime("%Y-%m-%d %H:%M:%S")
        platforms = json.dumps({
            "perplexity": {"mentioned": i > 1, "position": max(1, 8 - i), "sentiment": "positive" if i > 3 else "neutral"},
            "you.com": {"mentioned": i > 0, "position": max(1, 10 - i), "sentiment": "positive" if i > 2 else "neutral"},
            "chatgpt": {"mentioned": i > 2, "position": max(1, 7 - i), "sentiment": "positive"},
            "claude": {"mentioned": i > 3, "position": max(1, 6 - i), "sentiment": "positive"},
            "gemini": {"mentioned": i > 4, "position": max(1, 9 - i), "sentiment": "neutral"},
        })
        c.execute(
            "INSERT INTO geo_scans (project_id, scanned_at, geo_score, visibility_score, position_score, sentiment_score, platform_results_json) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (pid, ts, geo, vis, pos, sent, platforms),
        )

    # --- Community scans (7 data points) ---
    c.execute("DELETE FROM community_scans WHERE project_id = ?", (pid,))
    community_hits = [8, 12, 18, 22, 28, 35, 42]
    for i, hits in enumerate(community_hits):
        ts = (now - timedelta(days=len(community_hits) - 1 - i)).strftime("%Y-%m-%d %H:%M:%S")
        results = json.dumps([
            {"platform": "reddit", "title": f"Sample discussion {j}", "url": f"https://reddit.com/r/test/{j}"}
            for j in range(hits)
        ])
        c.execute(
            "INSERT INTO community_scans (project_id, scanned_at, total_hits, results_json) VALUES (?, ?, ?, ?)",
            (pid, ts, hits, results),
        )

    # --- SERP snapshots with positions ---
    c.execute("DELETE FROM serp_snapshots WHERE project_id = ?", (pid,))
    keywords = [
        ("OpenCMO", [3, 3, 2, 2, 1, 1, 1]),
        ("multi-agent marketing automation", [None, 45, 32, 22, 15, 10, 8]),
        ("open source Brand24 alternative", [None, None, 38, 28, 18, 12, 9]),
        ("AI visibility monitoring", [50, 40, 30, 22, 16, 11, 7]),
        ("GEO optimization", [None, 48, 35, 25, 18, 13, 10]),
        ("self-hosted brand monitoring", [42, 35, 28, 20, 14, 9, 6]),
        ("indie developer marketing automation", [None, None, 40, 30, 22, 15, 11]),
    ]
    for kw, positions in keywords:
        for i, pos in enumerate(positions):
            ts = (now - timedelta(days=len(positions) - 1 - i)).strftime("%Y-%m-%d %H:%M:%S")
            url_found = "https://github.com/Lling0000/OpenCMO" if pos and pos <= 20 else None
            c.execute(
                "INSERT INTO serp_snapshots (project_id, keyword, position, url_found, provider, error, checked_at) "
                "VALUES (?, ?, ?, ?, 'crawl', NULL, ?)",
                (pid, kw, pos, url_found, ts),
            )

    # --- Ensure we have discussion snapshots for engagement data ---
    c.execute("SELECT id FROM tracked_discussions WHERE project_id = ?", (pid,))
    disc_ids = [r[0] for r in c.fetchall()]
    for disc_id in disc_ids[:10]:
        c.execute("DELETE FROM discussion_snapshots WHERE discussion_id = ?", (disc_id,))
        for i in range(5):
            ts = (now - timedelta(days=4 - i)).strftime("%Y-%m-%d %H:%M:%S")
            c.execute(
                "INSERT INTO discussion_snapshots (discussion_id, checked_at, raw_score, comments_count, engagement_score) "
                "VALUES (?, ?, ?, ?, ?)",
                (disc_id, ts, 10 + i * 5, 3 + i * 2, 15 + i * 8),
            )

    # --- Ensure competitor keywords exist ---
    c.execute("SELECT id FROM competitors WHERE project_id = ? LIMIT 5", (pid,))
    comp_ids = [r[0] for r in c.fetchall()]
    overlap_keywords = [
        "AI marketing tool", "brand monitoring", "social media automation",
        "SEO audit tool", "content generation AI",
    ]
    for comp_id in comp_ids[:3]:
        for kw in overlap_keywords[:3]:
            c.execute(
                "INSERT OR IGNORE INTO competitor_keywords (competitor_id, keyword) VALUES (?, ?)",
                (comp_id, kw),
            )

    conn.commit()
    conn.close()
    print(f"Seeded demo data for project {pid}")


# ---------------------------------------------------------------------------
# Phase 2: Capture screenshots
# ---------------------------------------------------------------------------


def capture_page(page, url, path, label, wait_sec=3):
    """Navigate to a URL and capture a screenshot."""
    print(f"Capturing {label}...")
    try:
        page.goto(url, wait_until="networkidle", timeout=15000)
        time.sleep(wait_sec)
        page.screenshot(path=path)
        print(f"  Saved {path}")
    except Exception as e:
        print(f"  Error capturing {label}: {e}")


def capture_all(playwright):
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context(
        viewport={"width": 1440, "height": 900},
        color_scheme="light",
        device_scale_factor=2,
    )
    page = context.new_page()

    pid = PROJECT_ID

    # --- Static page captures ---
    captures = [
        (f"{BASE_URL}", f"{SCREENSHOTS_DIR}/dashboard-full.png", "Dashboard"),
        (f"{BASE_URL}/projects/{pid}/seo", f"{SCREENSHOTS_DIR}/seo-page.png", "SEO Page"),
        (f"{BASE_URL}/projects/{pid}/geo", f"{SCREENSHOTS_DIR}/geo-page.png", "GEO Page"),
        (f"{BASE_URL}/projects/{pid}/serp", f"{SCREENSHOTS_DIR}/serp-page.png", "SERP Page"),
        (f"{BASE_URL}/projects/{pid}/community", f"{SCREENSHOTS_DIR}/community-page.png", "Community Page"),
        (f"{BASE_URL}/projects/{pid}/graph", f"{SCREENSHOTS_DIR}/graph-page.png", "Knowledge Graph"),
        (f"{BASE_URL}/chat", f"{SCREENSHOTS_DIR}/chat-interface.png", "Chat Interface"),
        (f"{BASE_URL}/monitors", f"{SCREENSHOTS_DIR}/monitors-panel.png", "Monitors Panel"),
    ]

    for url, path, label in captures:
        capture_page(page, url, path, label)

    # --- Settings dialog (open from sidebar) ---
    print("Capturing Settings Dialog...")
    try:
        page.goto(BASE_URL, wait_until="networkidle", timeout=15000)
        time.sleep(2)
        # Click the Settings button in the sidebar
        settings_btn = page.locator("button", has_text="Settings").or_(
            page.locator("button", has_text="设置")
        )
        settings_btn.first.click()
        time.sleep(1.5)
        page.screenshot(path=f"{SCREENSHOTS_DIR}/settings-panel.png")
        print(f"  Saved {SCREENSHOTS_DIR}/settings-panel.png")
    except Exception as e:
        print(f"  Error capturing settings: {e}")

    # --- Knowledge Graph with longer wait for 3D render ---
    print("Re-capturing Knowledge Graph with full 3D render...")
    try:
        page.goto(f"{BASE_URL}/projects/{pid}/graph", wait_until="networkidle", timeout=15000)
        time.sleep(6)  # Extra time for Three.js to render
        page.screenshot(path=f"{SCREENSHOTS_DIR}/graph-page.png")
        print(f"  Saved {SCREENSHOTS_DIR}/graph-page.png")
    except Exception as e:
        print(f"  Error: {e}")

    browser.close()


# ---------------------------------------------------------------------------
# Phase 3: Record GIFs via Playwright video + ffmpeg
# ---------------------------------------------------------------------------


def record_gif(playwright, name, url, actions_fn, duration_sec=5):
    """Record a browser interaction as GIF using Playwright video + ffmpeg."""
    if not _has_ffmpeg():
        print(f"  Skipping GIF {name}: ffmpeg not found")
        return

    video_dir = "/tmp/opencmo_videos"
    os.makedirs(video_dir, exist_ok=True)

    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context(
        viewport={"width": 1280, "height": 720},
        color_scheme="light",
        device_scale_factor=2,
        record_video_dir=video_dir,
        record_video_size={"width": 1280, "height": 720},
    )
    page = context.new_page()

    try:
        page.goto(url, wait_until="networkidle", timeout=15000)
        time.sleep(3)  # Let page fully render

        actions_fn(page)
        time.sleep(duration_sec)

    except Exception as e:
        print(f"  Error recording {name}: {e}")
    finally:
        page.close()
        context.close()
        browser.close()

    # Find the recorded video
    video_files = sorted(Path(video_dir).glob("*.webm"), key=os.path.getmtime, reverse=True)
    if not video_files:
        print(f"  No video recorded for {name}")
        return

    video_path = str(video_files[0])
    gif_path = f"{SCREENSHOTS_DIR}/{name}.gif"

    # Convert webm → optimized GIF
    print(f"  Converting {video_path} → {gif_path}")
    try:
        # Generate palette for better quality
        palette = f"/tmp/{name}_palette.png"
        subprocess.run([
            "ffmpeg", "-y", "-i", video_path,
            "-vf", "fps=10,scale=800:-1:flags=lanczos,palettegen",
            palette,
        ], capture_output=True, check=True)

        subprocess.run([
            "ffmpeg", "-y", "-i", video_path, "-i", palette,
            "-lavfi", "fps=10,scale=800:-1:flags=lanczos [x]; [x][1:v] paletteuse",
            gif_path,
        ], capture_output=True, check=True)

        os.unlink(palette)
        os.unlink(video_path)
        size_mb = os.path.getsize(gif_path) / 1024 / 1024
        print(f"  Saved {gif_path} ({size_mb:.1f} MB)")
    except subprocess.CalledProcessError as e:
        print(f"  ffmpeg conversion failed: {e}")


def _has_ffmpeg():
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


def record_gifs(playwright):
    pid = PROJECT_ID

    # GIF 1: Knowledge Graph interaction (rotate/zoom)
    print("Recording Knowledge Graph GIF...")

    def graph_actions(page):
        canvas = page.locator("canvas").first
        box = canvas.bounding_box()
        if box:
            cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
            # Simulate drag to rotate
            page.mouse.move(cx, cy)
            page.mouse.down()
            for i in range(30):
                page.mouse.move(cx + i * 5, cy + i * 2)
                time.sleep(0.05)
            page.mouse.up()
            time.sleep(1)
            # Zoom in slightly
            for _ in range(3):
                page.mouse.wheel(0, -100)
                time.sleep(0.3)

    record_gif(playwright, "knowledge-graph-demo", f"{BASE_URL}/projects/{pid}/graph", graph_actions, duration_sec=3)

    # GIF 2: Chat interaction
    print("Recording Chat GIF...")

    def chat_actions(page):
        textarea = page.locator("textarea").first
        textarea.click()
        time.sleep(0.5)
        # Type a message character by character for visual effect
        msg = "What SEO improvements should I prioritize?"
        for ch in msg:
            textarea.type(ch, delay=50)
        time.sleep(0.5)
        # Press Enter or click send
        page.keyboard.press("Enter")
        time.sleep(5)  # Wait for streaming response

    record_gif(playwright, "chat-demo", f"{BASE_URL}/chat", chat_actions, duration_sec=3)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    print("=" * 60)
    print("OpenCMO Screenshot & GIF Capture")
    print("=" * 60)

    print("\n--- Seeding demo data ---")
    seed_demo_data()

    print("\n--- Capturing screenshots ---")
    with sync_playwright() as pw:
        capture_all(pw)

    print("\n--- Recording GIFs ---")
    with sync_playwright() as pw:
        record_gifs(pw)

    print("\n--- Done! ---")
    print(f"Files in {SCREENSHOTS_DIR}/:")
    for f in sorted(Path(SCREENSHOTS_DIR).iterdir()):
        if f.is_file():
            size = f.stat().st_size / 1024
            print(f"  {f.name:40s} {size:8.1f} KB")
