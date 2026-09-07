"""Promotional blog generation pipeline — 6-phase service.

Phases:
  1. Deep product crawl (sitemap + homepage links → fetch subpages)
  2. Product profile synthesis (LLM → structured JSON)
  3. Competitive research (reuse blog_writer._research_topic_impl)
  4. Blog writing (promotional_blog agent)
  5. Quality scoring (4 dimensions, parallel LLM calls)
  6. Bilingual generation (optional EN↔ZH adaptation)
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any, Callable

from opencmo import llm, storage
from opencmo.marketing_skills import MARKETING_SKILLS_UPSTREAM_COMMIT, MarketingSkill, get_marketing_skill
from opencmo.services.approval_service import create_approval

logger = logging.getLogger(__name__)

_MAX_CONCURRENT_LLM_CALLS = 3
_SUBPAGE_PRIORITY_PATTERNS = [
    "feature", "pricing", "about", "product", "solution",
    "doc", "how-it-work", "why", "benefit", "use-case",
    "integrat", "api", "overview", "getting-started",
]
_SUPPORTED_CONTENT_LANGUAGES = ("en", "zh", "ja", "ko", "es")
_LANGUAGE_NAMES = {
    "en": "English",
    "zh": "Chinese (Simplified, zh-CN)",
    "ja": "Japanese",
    "ko": "Korean",
    "es": "Spanish",
}


def _normalize_content_language(language: str | None) -> str | None:
    if not language:
        return None
    value = language.strip().lower()
    for supported in _SUPPORTED_CONTENT_LANGUAGES:
        if value == supported or value.startswith(f"{supported}-") or value.startswith(f"{supported}_"):
            return supported
    if value.startswith("zh"):
        return "zh"
    return None


def _detect_primary_language(project: dict) -> str:
    brand_name = project.get("brand_name", "")
    return "zh" if any("\u4e00" <= c <= "\u9fff" for c in brand_name) else "en"


def _secondary_language(primary_language: str) -> str:
    return "zh" if primary_language == "en" else "en"


# ---------------------------------------------------------------------------
# Progress helper
# ---------------------------------------------------------------------------

def _emit(on_progress: Callable | None, phase: str, status: str, summary: str) -> None:
    if on_progress:
        on_progress({"phase": phase, "status": status, "summary": summary})


# ---------------------------------------------------------------------------
# Phase 1: Deep Product Crawl
# ---------------------------------------------------------------------------

def _score_url(url: str) -> int:
    """Higher score = higher priority subpage for product understanding."""
    lower = url.lower()
    score = 0
    for pattern in _SUBPAGE_PRIORITY_PATTERNS:
        if pattern in lower:
            score += 1
    # Penalize very deep paths
    path_depth = lower.rstrip("/").count("/") - 2  # subtract scheme://host
    if path_depth > 3:
        score -= 1
    return score


async def _phase_deep_crawl(
    project_url: str,
    on_progress: Callable | None = None,
) -> dict:
    """Crawl homepage + up to 4 high-value subpages."""
    from opencmo.tools.crawl import fetch_url_content
    from opencmo.tools.llmstxt import _discover_pages

    _emit(on_progress, "crawl", "running", "Discovering site pages...")

    # Discover pages via sitemap or homepage link extraction
    try:
        discovered = await _discover_pages(project_url, max_pages=30)
    except Exception as exc:
        logger.warning("Page discovery failed: %s", exc)
        discovered = []

    # Always include homepage
    pages_result: list[dict] = []

    _emit(on_progress, "crawl", "running", "Crawling homepage...")
    try:
        homepage_content, homepage_source = await fetch_url_content(
            project_url, max_chars=15000,
        )
        pages_result.append({
            "url": project_url,
            "content": homepage_content,
            "source": homepage_source,
            "is_homepage": True,
        })
    except Exception as exc:
        logger.warning("Homepage crawl failed: %s", exc)
        pages_result.append({
            "url": project_url,
            "content": "",
            "source": "failed",
            "is_homepage": True,
        })

    # Select top 4 subpages by relevance score
    subpage_urls = [
        p["url"] for p in discovered
        if p["url"].rstrip("/") != project_url.rstrip("/")
    ]
    scored = sorted(subpage_urls, key=_score_url, reverse=True)
    selected = scored[:4]

    if selected:
        _emit(on_progress, "crawl", "running",
              f"Crawling {len(selected)} subpages...")

        sem = asyncio.Semaphore(2)  # light concurrency for crawls

        async def _crawl_one(url: str) -> dict:
            async with sem:
                try:
                    content, source = await fetch_url_content(
                        url, max_chars=8000,
                    )
                    return {"url": url, "content": content, "source": source}
                except Exception as exc:
                    logger.debug("Subpage crawl failed %s: %s", url, exc)
                    return {"url": url, "content": "", "source": "failed"}

        results = await asyncio.gather(*[_crawl_one(u) for u in selected])
        pages_result.extend(r for r in results if r["content"])

    _emit(on_progress, "crawl", "completed",
          f"Crawled {len(pages_result)} pages ({len(discovered)} discovered)")

    return {
        "pages": pages_result,
        "total_discovered": len(discovered),
    }


# ---------------------------------------------------------------------------
# Phase 2: Product Profile Synthesis
# ---------------------------------------------------------------------------

_PROFILE_SYSTEM = """\
You are a product analyst. Given crawled website content, extract a structured product profile as JSON.

Return ONLY valid JSON with these fields:
{
  "product_name": "exact product name",
  "tagline": "one-line value proposition",
  "value_proposition": "2-3 sentence description of what the product does and why it matters",
  "key_features": ["feature 1", "feature 2", ...],
  "target_audience": "who this product is for",
  "use_cases": ["use case 1", "use case 2", ...],
  "differentiators": ["what makes it unique 1", ...],
  "pricing_model": "free / freemium / paid / enterprise / unknown",
  "tech_stack": ["technology 1", ...],
  "integrations": ["integration 1", ...]
}

Rules:
- Only include information explicitly found in the crawled content
- If a field is not clear from the content, use an empty string or empty array
- Keep each feature/use case description under 20 words
- product_name must be the actual product name, NOT the hosting platform
"""


async def _phase_synthesize_profile(
    crawl_data: dict,
    project: dict,
    on_progress: Callable | None = None,
) -> dict:
    """Synthesize crawled pages into a structured product profile."""
    _emit(on_progress, "profile", "running", "Synthesizing product profile...")

    # Build content blob from all pages
    content_parts: list[str] = []
    for page in crawl_data["pages"]:
        label = "HOMEPAGE" if page.get("is_homepage") else page["url"]
        content_parts.append(f"=== {label} ===\n{page['content'][:6000]}")

    user_prompt = "\n\n".join(content_parts)
    if len(user_prompt) > 30000:
        user_prompt = user_prompt[:30000] + "\n\n[Content truncated]"

    raw = await llm.chat_completion(
        system=_PROFILE_SYSTEM,
        user=user_prompt,
        temperature=0.3,
    )

    # Parse JSON from response (handle markdown fences)
    json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    if json_match:
        raw = json_match.group(1)
    else:
        # Try to find JSON object directly
        brace_start = raw.find("{")
        brace_end = raw.rfind("}")
        if brace_start != -1 and brace_end != -1:
            raw = raw[brace_start:brace_end + 1]

    try:
        profile = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Failed to parse product profile JSON, using fallback")
        profile = {
            "product_name": project.get("brand_name", "Unknown"),
            "tagline": "",
            "value_proposition": "",
            "key_features": [],
            "target_audience": "",
            "use_cases": [],
            "differentiators": [],
            "pricing_model": "unknown",
            "tech_stack": [],
            "integrations": [],
        }

    # Merge with project metadata
    profile["brand_name"] = project.get("brand_name", profile.get("product_name", ""))
    profile["category"] = project.get("category", "")
    profile["url"] = project.get("url", "")

    _emit(on_progress, "profile", "completed",
          f"Profile: {profile.get('product_name', 'Unknown')} — {len(profile.get('key_features', []))} features identified")

    return profile


# ---------------------------------------------------------------------------
# Phase 3: Competitive Research
# ---------------------------------------------------------------------------

async def _phase_competitive_research(
    profile: dict,
    project_id: int,
    on_progress: Callable | None = None,
) -> dict:
    """Gather competitive context from existing data + fresh research."""
    _emit(on_progress, "research", "running", "Researching competitive landscape...")

    # Pull existing project data
    keywords = await storage.list_tracked_keywords(project_id)
    competitors = await storage.list_competitors(project_id)

    keyword_list = [k["keyword"] for k in keywords][:10] if keywords else []
    competitor_names = [c["name"] for c in competitors][:5] if competitors else []

    # Use blog_writer research tool for fresh competitive content
    research_result: dict = {}
    try:
        from opencmo.tools.blog_writer import _research_topic_impl

        topic = profile.get("product_name", profile.get("brand_name", ""))
        kw_str = ", ".join(keyword_list[:5]) if keyword_list else profile.get("category", "")
        if topic and kw_str:
            raw = await _research_topic_impl(topic, kw_str)
            research_result = json.loads(raw)
    except Exception as exc:
        logger.warning("Competitive research failed: %s", exc)

    result = {
        "tracked_keywords": keyword_list,
        "competitors": competitor_names,
        "competing_articles": research_result.get("competing_articles", []),
        "data_points": research_result.get("data_points", []),
    }

    article_count = len(result["competing_articles"])
    _emit(on_progress, "research", "completed",
          f"Found {article_count} competing articles, {len(keyword_list)} tracked keywords")

    return result


# ---------------------------------------------------------------------------
# Phase 4: Blog Writing
# ---------------------------------------------------------------------------

async def _phase_write_blog(
    profile: dict,
    research: dict,
    style: str,
    project_id: int,
    marketing_skill: MarketingSkill,
    target_language: str,
    on_progress: Callable | None = None,
) -> tuple[str, str]:
    """Write the blog article using the promotional agent. Returns (title, content)."""
    from agents import Runner

    from opencmo.agents.promotional_blog import build_promotional_blog_agent
    from opencmo.storage.brand_kit import build_brand_kit_prompt

    _emit(on_progress, "writing", "running", "Writing blog article...")

    brand_overlay = await build_brand_kit_prompt(project_id)
    agent = build_promotional_blog_agent(
        style,
        brand_overlay,
        marketing_skill_overlay=marketing_skill.as_prompt_block(),
        target_language=_LANGUAGE_NAMES.get(target_language, "English"),
    )

    # Build the user prompt with all context
    prompt_parts = [
        (
            f"## Target Language\nWrite the entire markdown asset in "
            f"{_LANGUAGE_NAMES.get(target_language, 'English')} ({target_language}). "
            "Do not switch languages except for product names, code identifiers, URLs, and technical terms that are normally kept in English."
        ),
        f"## Product Profile\n```json\n{json.dumps(profile, ensure_ascii=False, indent=2)}\n```",
        f"## Selected Marketing Skill\n{marketing_skill.name} ({marketing_skill.id})",
    ]

    if research.get("competing_articles"):
        articles_summary = []
        for article in research["competing_articles"][:3]:
            articles_summary.append(
                f"- **{article.get('title', 'Untitled')}** ({article.get('url', '')})\n"
                f"  Key points: {', '.join(article.get('key_points', []))}"
            )
        prompt_parts.append("## Competitive Articles\n" + "\n".join(articles_summary))

    if research.get("data_points"):
        prompt_parts.append(
            "## Data Points\n" + "\n".join(f"- {dp}" for dp in research["data_points"][:10])
        )

    if research.get("tracked_keywords"):
        prompt_parts.append(
            "## Target Keywords\n" + ", ".join(research["tracked_keywords"][:10])
        )

    if research.get("competitors"):
        prompt_parts.append(
            "## Known Competitors\n" + ", ".join(research["competitors"])
        )

    prompt_parts.append(
        f"\n## Instruction\nUse the **{style.replace('_', ' ')}** style and the selected "
        f"**{marketing_skill.name}** framework to produce the requested markdown asset."
    )

    from opencmo.rag.integration import section_evidence
    evidence = await section_evidence(f"{profile.get('product_name', '')} {style} {research.get('tracked_keywords', [])}")
    if evidence:
        prompt_parts.append(evidence)
    user_message = "\n\n".join(prompt_parts)

    run_options = {}
    if evidence:
        from agents import RunConfig
        run_options['run_config'] = RunConfig(tracing_disabled=True, trace_include_sensitive_data=False)
    result = await Runner.run(agent, user_message, **run_options)
    content = result.final_output or ""

    # Extract title from first H1
    title = ""
    for line in content.split("\n"):
        line = line.strip()
        if line.startswith("# ") and not line.startswith("## "):
            title = line[2:].strip()
            break

    if not title:
        title = f"{profile.get('product_name', 'Product')} — {style.replace('_', ' ').title()}"

    _emit(on_progress, "writing", "completed",
          f"Article written: \"{title}\" ({len(content.split())} words)")

    return title, content


# ---------------------------------------------------------------------------
# Phase 5: Quality Scoring
# ---------------------------------------------------------------------------

_SCORING_RUBRIC = {
    "seo": """\
Score this blog article's SEO quality (0-100).

Criteria:
- Keyword presence: Are the target keywords used naturally in the title, headings, and body?
- Heading structure: Does it use H1 (title) + H2 (sections) properly?
- Meta-readiness: Does the title work as a page title (30-60 chars)? Is the opening paragraph meta-description-ready?
- Internal linking opportunities: Does it mention topics that could link to other content?

Score anchors: 90+ = excellent keyword integration + perfect structure, 70-89 = good with minor gaps, 50-69 = usable but needs SEO editing, <50 = poor SEO fundamentals.

Return ONLY a JSON object: {"score": <number>, "reasoning": "<brief explanation>"}
""",
    "readability": """\
Score this blog article's readability (0-100).

Criteria:
- Sentence variety: Mix of short and long sentences? Avoids monotonous patterns?
- Paragraph length: Paragraphs under 4-5 sentences? Scannable?
- Jargon level: Appropriate for a technical audience without being inaccessible?
- Flow: Smooth transitions between sections? Logical progression?

Score anchors: 90+ = effortless to read, 70-89 = clear with minor rough spots, 50-69 = readable but dense, <50 = hard to follow.

Return ONLY a JSON object: {"score": <number>, "reasoning": "<brief explanation>"}
""",
    "keyword_coverage": """\
Score how well this article covers the target keywords (0-100).

Criteria:
- How many target keywords appear naturally in the article?
- Are keywords used in headings, not just body text?
- Are long-tail variations present?
- Is keyword density natural (not stuffed)?

Score anchors: 90+ = all keywords covered naturally, 70-89 = most covered, 50-69 = some gaps, <50 = poor coverage.

Return ONLY a JSON object: {"score": <number>, "reasoning": "<brief explanation>"}
""",
    "structure": """\
Score this blog article's structural quality (0-100).

Criteria:
- Hook: Does the introduction grab attention within 2-3 sentences?
- Section flow: Do sections follow a logical order? Does each section earn its place?
- CTA: Is there a clear call to action near the end?
- Completeness: Does the article feel finished? No abrupt endings or missing sections?
- H2 count: Does it have 4-7 well-titled sections?

Score anchors: 90+ = compelling structure, 70-89 = solid with minor ordering issues, 50-69 = all pieces present but weakly connected, <50 = missing key structural elements.

Return ONLY a JSON object: {"score": <number>, "reasoning": "<brief explanation>"}
""",
}


def _build_scoring_rubric(marketing_skill: MarketingSkill | None = None) -> dict[str, str]:
    rubrics = dict(_SCORING_RUBRIC)
    if marketing_skill is not None:
        rubrics.update(marketing_skill.quality_rubrics)
    return rubrics


async def _phase_quality_score(
    content: str,
    keywords: list[str],
    marketing_skill: MarketingSkill | None = None,
    on_progress: Callable | None = None,
) -> dict[str, Any]:
    """Score the article across 4 dimensions. Returns scores dict."""
    _emit(on_progress, "scoring", "running", "Scoring content quality...")

    sem = asyncio.Semaphore(_MAX_CONCURRENT_LLM_CALLS)
    scoring_rubric = _build_scoring_rubric(marketing_skill)

    async def _score_dimension(dimension: str) -> tuple[str, int, str]:
        async with sem:
            system = scoring_rubric[dimension]
            user = f"## Article to score\n\n{content[:8000]}"
            if dimension == "keyword_coverage" and keywords:
                user += f"\n\n## Target Keywords\n{', '.join(keywords)}"
            if marketing_skill is not None and dimension in marketing_skill.quality_rubrics:
                user += f"\n\n## Marketing Skill\n{marketing_skill.name}: {marketing_skill.description}"

            raw = await llm.chat_completion(
                system=system,
                user=user,
                temperature=0.2,
            )

            # Parse score from JSON response
            json_match = re.search(r"\{[^}]*\"score\"\s*:\s*(\d+)[^}]*\}", raw)
            if json_match:
                score = int(json_match.group(1))
                score = max(0, min(100, score))
            else:
                score = 65  # neutral fallback
            reasoning_match = re.search(r"\"reasoning\"\s*:\s*\"([^\"]+)\"", raw)
            reasoning = reasoning_match.group(1) if reasoning_match else ""
            return dimension, score, reasoning

    results = await asyncio.gather(
        *[_score_dimension(dim) for dim in scoring_rubric],
        return_exceptions=True,
    )

    scores: dict[str, Any] = {}
    for r in results:
        if isinstance(r, Exception):
            logger.warning("Scoring failed: %s", r)
            continue
        dim, score, reasoning = r
        scores[dim] = score
        scores[f"{dim}_reasoning"] = reasoning

    # Compute weighted overall
    weights = {"seo": 0.3, "readability": 0.25, "keyword_coverage": 0.25, "structure": 0.2}
    base_overall = sum(scores.get(dim, 65) * w for dim, w in weights.items())
    skill_dimensions = [dim for dim in scoring_rubric if dim not in _SCORING_RUBRIC]
    if skill_dimensions:
        framework_score = round(sum(scores.get(dim, 65) for dim in skill_dimensions) / len(skill_dimensions))
        scores["framework"] = framework_score
        scores["overall"] = round(base_overall * 0.75 + framework_score * 0.25)
    else:
        scores["overall"] = round(base_overall)

    _emit(on_progress, "scoring", "completed",
          f"Quality score: {scores['overall']}/100 (SEO={scores.get('seo', '?')}, Read={scores.get('readability', '?')}, KW={scores.get('keyword_coverage', '?')}, Struct={scores.get('structure', '?')})")

    return scores


# ---------------------------------------------------------------------------
# Phase 6: Bilingual Generation
# ---------------------------------------------------------------------------

_BILINGUAL_SYSTEM = """\
You are a professional translator and content adapter. Translate the following blog article
into {target_language}.

Rules:
- This is a CULTURAL ADAPTATION, not a literal translation
- Preserve all factual claims, product names, and technical terms
- Adapt idioms, cultural references, and phrasing to feel native in {target_language}
- Keep the same markdown structure (headings, emphasis, code blocks)
- Keep the same section order and roughly the same word count per section
- Product name should remain in its original form (do not translate brand names)
- Technical terms that are commonly used in English in {target_language} contexts should stay in English

Return ONLY the translated article in markdown format. No commentary.
"""


async def _phase_bilingual(
    content: str,
    primary_language: str,
    on_progress: Callable | None = None,
) -> str:
    """Adapt the article to the paired language."""
    target = _LANGUAGE_NAMES[_secondary_language(primary_language)]

    _emit(on_progress, "translate", "running", f"Generating {target} version...")

    translated = await llm.chat_completion(
        system=_BILINGUAL_SYSTEM.replace("{target_language}", target),
        user=content,
        temperature=0.5,
    )

    _emit(on_progress, "translate", "completed", f"{target} version generated")
    return translated


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

from opencmo.rag.integration import finalize_generation, with_knowledge


@with_knowledge('content')
async def generate_promotional_blog(
    project_id: int,
    style: str,
    bilingual: bool,
    task_id: str,
    skill_id: str | None = None,
    language: str | None = None,
    on_progress: Callable | None = None,
) -> dict:
    """Run the full 6-phase promotional blog generation pipeline.

    Returns:
        dict with draft_ids, quality_scores, approval_ids, summary
    """
    # Load project
    project = await storage.get_project(project_id)
    if not project:
        raise ValueError(f"Project {project_id} not found")
    marketing_skill = get_marketing_skill(skill_id)
    skill_meta = marketing_skill.to_public_dict()
    _emit(on_progress, "framework", "completed", f"Using {marketing_skill.name} framework")

    # Prefer the UI/request language; fall back to the legacy project-name heuristic.
    primary_language = _normalize_content_language(language) or _detect_primary_language(project)

    # Phase 1: Deep product crawl
    crawl_data = await _phase_deep_crawl(project["url"], on_progress)

    # Phase 2: Product profile synthesis
    profile = await _phase_synthesize_profile(crawl_data, project, on_progress)

    # Phase 3: Competitive research
    research = await _phase_competitive_research(profile, project_id, on_progress)

    # Phase 4: Blog writing
    title, content = await _phase_write_blog(
        profile, research, style, project_id, marketing_skill, primary_language, on_progress,
    )

    # Create primary draft record
    content, rag_meta = await finalize_generation(content)
    draft = await storage.create_blog_draft(
        project_id=project_id,
        task_id=task_id,
        style=style,
        language=primary_language,
    )
    await storage.update_blog_draft(
        draft["id"],
        title=title,
        content=content,
        product_profile=profile,
        meta={
            **rag_meta,
            "marketing_skill": skill_meta,
            "source_commit": MARKETING_SKILLS_UPSTREAM_COMMIT,
        },
        status="scoring",
    )

    # Phase 5: Quality scoring
    tracked_keywords = research.get("tracked_keywords", [])
    scores = await _phase_quality_score(content, tracked_keywords, marketing_skill, on_progress)
    await storage.update_blog_draft(draft["id"], quality_scores=scores)

    draft_ids = [draft["id"]]
    all_scores = {primary_language: scores}

    # Phase 6: Bilingual generation (optional)
    if bilingual:
        secondary_language = _secondary_language(primary_language)
        translated_content = await _phase_bilingual(
            content, primary_language, on_progress,
        )

        # Extract title from translated content
        translated_title = title
        for line in translated_content.split("\n"):
            line = line.strip()
            if line.startswith("# ") and not line.startswith("## "):
                translated_title = line[2:].strip()
                break

        # Create paired draft
        translated_content, translated_rag_meta = await finalize_generation(translated_content)
        paired_draft = await storage.create_blog_draft(
            project_id=project_id,
            task_id=task_id,
            style=style,
            language=secondary_language,
        )
        await storage.update_blog_draft(
            paired_draft["id"],
            title=translated_title,
            content=translated_content,
            product_profile=profile,
            meta={
                **translated_rag_meta,
                "marketing_skill": skill_meta,
                "source_commit": MARKETING_SKILLS_UPSTREAM_COMMIT,
                "translated_from_draft_id": draft["id"],
            },
            paired_draft_id=draft["id"],
            status="scoring",
        )
        # Link back
        await storage.update_blog_draft(
            draft["id"], paired_draft_id=paired_draft["id"],
        )

        # Score the translated version
        secondary_scores = await _phase_quality_score(
            translated_content, tracked_keywords, marketing_skill, on_progress,
        )
        await storage.update_blog_draft(
            paired_draft["id"], quality_scores=secondary_scores,
        )

        draft_ids.append(paired_draft["id"])
        all_scores[secondary_language] = secondary_scores

    # Post-pipeline: create approval(s)
    approval_ids: list[int] = []
    for did in draft_ids:
        d = await storage.get_blog_draft(did)
        if not d:
            continue
        try:
            approval = await create_approval(
                project_id=project_id,
                approval_type="blog_post",
                payload={
                    "title": d["title"],
                    "body": d["content"],
                    "project_id": project_id,
                    "draft_id": d["id"],
                    "marketing_skill": skill_meta,
                },
                content=d["content"],
                title=d["title"],
                agent_name="promotional_blog",
            )
            approval_id = approval.get("id")
            if approval_id:
                await storage.update_blog_draft(did, approval_id=approval_id)
                approval_ids.append(approval_id)
        except Exception as exc:
            logger.warning("Failed to create approval for draft %d: %s", did, exc)

    # Mark all drafts completed
    for did in draft_ids:
        await storage.update_blog_draft(did, status="completed")

    primary_scores = all_scores.get(primary_language, {})
    return {
        "draft_ids": draft_ids,
        "language": primary_language,
        "marketing_skill": skill_meta,
        "skill_id": marketing_skill.id,
        "skill_name": marketing_skill.name,
        "quality_scores": primary_scores,
        "approval_ids": approval_ids,
        "summary": f"{marketing_skill.name} draft generated: \"{title}\" (score: {primary_scores.get('overall', '?')}/100)",
    }
