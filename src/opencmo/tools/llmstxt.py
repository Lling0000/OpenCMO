"""llms.txt validator and generator.

Inspired by geo-seo-claude (https://github.com/zubair-trabzada/geo-seo-claude).
The llms.txt standard (proposed Sept 2024, <5% adoption) helps AI crawlers
understand a site's structure via a simple Markdown file at /llms.txt.
"""

from __future__ import annotations

import logging
import re
import time
from urllib.parse import urljoin, urlparse

from agents import function_tool

from opencmo.tools.public_fetch import FETCH_TIMEOUT, fetch_public_text

logger = logging.getLogger(__name__)

_SECTION_KEYWORDS = {
    "Products & Services": (
        "/pricing", "/feature", "/product", "/solution", "/demo",
        "/plan", "/subscribe", "/enterprise",
    ),
    "Resources & Blog": (
        "/blog", "/article", "/resource", "/guide", "/learn",
        "/docs", "/documentation", "/tutorial", "/wiki", "/knowledge",
    ),
    "Company": (
        "/about", "/team", "/career", "/contact", "/press",
        "/partner", "/investor", "/mission",
    ),
    "Support": (
        "/help", "/support", "/faq", "/status", "/community",
        "/forum", "/ticket",
    ),
}

_SKIP_EXTENSIONS = (
    ".pdf", ".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp",
    ".css", ".js", ".ico", ".xml", ".json", ".zip", ".tar",
    ".mp3", ".mp4", ".wav", ".avi", ".mov",
)


def _validate_content(content: str) -> dict:
    """Validate llms.txt content against the standard."""
    lines = content.strip().splitlines()
    issues: list[str] = []
    suggestions: list[str] = []

    has_title = False
    has_description = False
    has_sections = False
    has_links = False
    section_count = 0
    link_count = 0

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("# ") and not stripped.startswith("## "):
            has_title = True
        elif stripped.startswith("> "):
            has_description = True
        elif stripped.startswith("## "):
            has_sections = True
            section_count += 1
        elif re.match(r'^- \[.+\]\(.+\)', stripped):
            has_links = True
            link_count += 1

    if not has_title:
        issues.append("Missing title line (should start with `# Site Name`)")
    if not has_description:
        issues.append("Missing description (should have a `> Description` blockquote)")
    if not has_sections:
        issues.append("Missing sections (should have at least one `## Section` heading)")
    if not has_links:
        issues.append("Missing links (should have `- [Title](url)` entries)")
    elif link_count < 5:
        suggestions.append(f"Only {link_count} links — consider adding more key pages")
    if section_count < 2:
        suggestions.append("Consider adding more sections for better organization")

    # Check for HTML tags (should be pure markdown)
    if re.search(r'<[a-zA-Z][^>]*>', content):
        issues.append("Contains HTML tags — llms.txt should be pure Markdown")

    return {
        "format_valid": len(issues) == 0,
        "has_title": has_title,
        "has_description": has_description,
        "has_sections": has_sections,
        "has_links": has_links,
        "section_count": section_count,
        "link_count": link_count,
        "issues": issues,
        "suggestions": suggestions,
    }


async def _discover_pages(url: str, max_pages: int = 30, *, deadline: float | None = None) -> list[dict]:
    """Discover site pages via sitemap or homepage links."""
    origin = f"{urlparse(url).scheme or 'https'}://{urlparse(url).netloc}"
    pages: list[dict] = []
    seen: set[str] = set()

    deadline = deadline if deadline is not None else time.monotonic() + FETCH_TIMEOUT
    # Try sitemap.xml first
    try:
        resp = await fetch_public_text(f"{origin}/sitemap.xml", deadline=deadline)
        if resp.status_code == 200 and "<loc>" in resp.text:
            locs = re.findall(r'<loc>(.*?)</loc>', resp.text)
            for loc in locs[:max_pages]:
                parsed = urlparse(loc)
                if parsed.netloc == urlparse(origin).netloc and loc not in seen:
                    seen.add(loc)
                    pages.append({"url": loc, "title": None, "description": None})
            if pages:
                return pages
    except Exception:
        pass

    # Fallback: crawl homepage for internal links
    try:
        resp = await fetch_public_text(origin, deadline=deadline)
        if resp.status_code == 200:
            # Extract title
            title_match = re.search(r'<title[^>]*>(.*?)</title>', resp.text, re.I | re.S)
            _site_title = title_match.group(1).strip() if title_match else ""

            # Extract internal links
            links = re.findall(r'href=["\']([^"\']+)["\']', resp.text)
            for link in links:
                full_url = urljoin(origin, link)
                parsed = urlparse(full_url)

                # Filter: same domain, no anchors, no skip extensions
                if parsed.netloc != urlparse(origin).netloc:
                    continue
                if parsed.fragment:
                    full_url = full_url.split("#")[0]
                if any(full_url.lower().endswith(ext) for ext in _SKIP_EXTENSIONS):
                    continue
                if full_url not in seen:
                    seen.add(full_url)
                    pages.append({"url": full_url, "title": None, "description": None})

                if len(pages) >= max_pages:
                    break
    except Exception as exc:
        logger.debug("Homepage crawl failed: %s", exc)

    return pages


def _categorize_pages(pages: list[dict]) -> dict[str, list[dict]]:
    """Sort discovered pages into sections by URL path keywords."""
    sections: dict[str, list[dict]] = {
        "Main Pages": [],
    }
    for section_name in _SECTION_KEYWORDS:
        sections[section_name] = []

    for page in pages:
        path = urlparse(page["url"]).path.lower()
        categorized = False

        for section_name, keywords in _SECTION_KEYWORDS.items():
            if any(kw in path for kw in keywords):
                sections[section_name].append(page)
                categorized = True
                break

        if not categorized:
            sections["Main Pages"].append(page)

    # Remove empty sections
    return {k: v for k, v in sections.items() if v}


def _generate_content(site_name: str, description: str, sections: dict[str, list[dict]], max_per_section: int = 10) -> str:
    """Generate llms.txt content from discovered pages."""
    lines = [f"# {site_name}", ""]
    if description:
        lines.append(f"> {description}")
        lines.append("")

    for section_name, pages in sections.items():
        lines.append(f"## {section_name}")
        lines.append("")
        for page in pages[:max_per_section]:
            path = urlparse(page["url"]).path
            title = page.get("title") or path.strip("/").split("/")[-1].replace("-", " ").title() or "Home"
            desc = page.get("description")
            if desc:
                lines.append(f"- [{title}]({page['url']}): {desc}")
            else:
                lines.append(f"- [{title}]({page['url']})")
        lines.append("")

    return "\n".join(lines)


@function_tool
async def validate_llmstxt(url: str) -> str:
    """Validate a website's /llms.txt file against the llms.txt standard. Checks for title, description, sections, and link format."""
    origin = f"{urlparse(url).scheme or 'https'}://{urlparse(url).netloc}"

    deadline = time.monotonic() + FETCH_TIMEOUT
    try:
        resp = await fetch_public_text(f"{origin}/llms.txt", deadline=deadline)
    except Exception as exc:
        return f"Error fetching llms.txt: {exc}"

    if resp.status_code != 200 or len(resp.text.strip()) < 10:
        return (
            f"## llms.txt Validation — {origin}\n\n"
            f"**No llms.txt found** at `{origin}/llms.txt`.\n\n"
            "The llms.txt standard is an emerging format (<5% adoption) that helps AI "
            "crawlers understand your site. Use `generate_llmstxt` to create one."
        )

    validation = _validate_content(resp.text)
    lines = [f"## llms.txt Validation — {origin}\n"]

    if validation["format_valid"]:
        lines.append("**Status: ✅ Valid**\n")
    else:
        lines.append("**Status: ❌ Issues Found**\n")

    lines.append(f"- Sections: {validation['section_count']}")
    lines.append(f"- Links: {validation['link_count']}")
    lines.append(f"- Title: {'✅' if validation['has_title'] else '❌'}")
    lines.append(f"- Description: {'✅' if validation['has_description'] else '❌'}")

    if validation["issues"]:
        lines.append("\n### Issues\n")
        for issue in validation["issues"]:
            lines.append(f"- ❌ {issue}")

    if validation["suggestions"]:
        lines.append("\n### Suggestions\n")
        for sug in validation["suggestions"]:
            lines.append(f"- 💡 {sug}")

    lines.append(f"\n### Current Content\n\n```\n{resp.text[:2000]}\n```")

    return "\n".join(lines)


@function_tool
async def generate_llmstxt(url: str) -> str:
    """Generate a compliant llms.txt file for a website by discovering its page structure via sitemap or homepage links."""
    origin = f"{urlparse(url).scheme or 'https'}://{urlparse(url).netloc}"

    # Get site metadata
    site_name = urlparse(url).netloc.split(".")[0].title()
    description = ""

    deadline = time.monotonic() + FETCH_TIMEOUT
    try:
        resp = await fetch_public_text(origin, deadline=deadline)
        if resp.status_code == 200:
            title_match = re.search(r'<title[^>]*>(.*?)</title>', resp.text, re.I | re.S)
            if title_match:
                raw_title = title_match.group(1).strip()
                site_name = re.split(r'\s*[|\-–—]\s*', raw_title)[0].strip()

            desc_match = re.search(
                r'<meta\s+(?:name=["\']description["\']\s+content=["\']([^"\']*)["\']|'
                r'content=["\']([^"\']*)["\'].*?name=["\']description["\'])',
                resp.text, re.I,
            )
            if desc_match:
                description = (desc_match.group(1) or desc_match.group(2) or "").strip()
    except Exception:
        pass

    # Discover pages
    pages = await _discover_pages(url, max_pages=30, deadline=deadline)

    if not pages:
        return (
            f"## Could not generate llms.txt for {origin}\n\n"
            "No pages discovered via sitemap or homepage links."
        )

    # Categorize and generate
    sections = _categorize_pages(pages)
    content = _generate_content(site_name, description, sections)

    # Validate the generated content
    validation = _validate_content(content)

    lines = [f"## Generated llms.txt for {origin}\n"]
    lines.append(f"Pages analyzed: {len(pages)}")
    lines.append(f"Sections: {validation['section_count']}")
    lines.append(f"Links: {validation['link_count']}")
    lines.append("\nSave this content as `/llms.txt` on your web server:\n")
    lines.append(f"```markdown\n{content}\n```")

    return "\n".join(lines)
