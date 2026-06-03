from agents import Agent, handoff

from opencmo.agents.blog import blog_expert
from opencmo.agents.community import community_agent
from opencmo.agents.devto import devto_expert
from opencmo.agents.geo import geo_agent
from opencmo.agents.gitcode import gitcode_expert
from opencmo.agents.github import github_outreach_agent
from opencmo.agents.hackernews import hackernews_expert
from opencmo.agents.infoq import infoq_expert
from opencmo.agents.jike import jike_expert
from opencmo.agents.juejin import juejin_expert
from opencmo.agents.linkedin import linkedin_expert
from opencmo.agents.oschina import oschina_expert
from opencmo.agents.producthunt import producthunt_expert
from opencmo.agents.prompt_contracts import build_prompt
from opencmo.agents.reddit import reddit_expert
from opencmo.agents.ruanyifeng import ruanyifeng_expert
from opencmo.agents.seo import seo_agent
from opencmo.agents.sspai import sspai_expert
from opencmo.agents.trend import trend_agent
from opencmo.agents.twitter import twitter_expert
from opencmo.agents.v2ex import v2ex_expert
from opencmo.agents.wechat import wechat_expert
from opencmo.agents.xiaohongshu import xiaohongshu_expert
from opencmo.agents.zhihu import zhihu_expert
from opencmo.config import get_model
from opencmo.tools.competitor import analyze_competitor
from opencmo.tools.content_frequency import check_content_frequency
from opencmo.tools.crawl import crawl_website
from opencmo.tools.cta_audit import audit_landing_page_cta
from opencmo.tools.deep_search import deep_search
from opencmo.tools.graph_intel import get_competitive_landscape
from opencmo.tools.gsc import check_search_console
from opencmo.tools.keyword_suggest import suggest_keywords
from opencmo.tools.research_brief import generate_research_brief
from opencmo.tools.search import web_search
from opencmo.tools.site_audit import audit_site_pages


def _multi_channel_tool(agent: Agent, *, tool_name: str, tool_description: str):
    return agent.as_tool(
        tool_name=tool_name,
        tool_description=(
            "Use ONLY for coordinated multi-channel orchestration when the user asked for content across multiple platforms "
            "and the CMO needs to collect outputs without handing off. Never use this for a single-platform request. "
            f"{tool_description}"
        ),
    )


# as_tool wrappers — CMO calls these in multi-channel mode to retain control
twitter_tool = _multi_channel_tool(
    twitter_expert,
    tool_name="generate_twitter_content",
    tool_description="Generate Twitter/X marketing content (tweets + thread). Returns formatted content.",
)
reddit_tool = _multi_channel_tool(
    reddit_expert,
    tool_name="generate_reddit_content",
    tool_description="Generate authentic Reddit posts for r/SideProject and niche subreddits.",
)
linkedin_tool = _multi_channel_tool(
    linkedin_expert,
    tool_name="generate_linkedin_content",
    tool_description="Generate professional LinkedIn posts. Returns long-form and short-form variants.",
)
producthunt_tool = _multi_channel_tool(
    producthunt_expert,
    tool_name="generate_producthunt_content",
    tool_description="Generate Product Hunt launch copy (tagline, description, maker comment).",
)
hackernews_tool = _multi_channel_tool(
    hackernews_expert,
    tool_name="generate_hackernews_content",
    tool_description="Generate Hacker News Show HN post (title + body).",
)
blog_tool = _multi_channel_tool(
    blog_expert,
    tool_name="generate_blog_content",
    tool_description="Generate blog/SEO article outlines, SEO recommendations, or full 2000+ word articles with research.",
)
ruanyifeng_tool = _multi_channel_tool(
    ruanyifeng_expert,
    tool_name="generate_ruanyifeng_content",
    tool_description="Generate 阮一峰科技爱好者周刊 submission (GitHub Issue format).",
)
zhihu_tool = _multi_channel_tool(
    zhihu_expert,
    tool_name="generate_zhihu_content",
    tool_description="Generate 知乎 articles and Q&A answers.",
)
xiaohongshu_tool = _multi_channel_tool(
    xiaohongshu_expert,
    tool_name="generate_xiaohongshu_content",
    tool_description="Generate 小红书 image-text notes (种草笔记).",
)
v2ex_tool = _multi_channel_tool(
    v2ex_expert,
    tool_name="generate_v2ex_content",
    tool_description="Generate V2EX community posts for /go/share or /go/create.",
)
juejin_tool = _multi_channel_tool(
    juejin_expert,
    tool_name="generate_juejin_content",
    tool_description="Generate 掘金 technical articles and tutorials.",
)
jike_tool = _multi_channel_tool(
    jike_expert,
    tool_name="generate_jike_content",
    tool_description="Generate 即刻 posts for indie dev / startup circles.",
)
wechat_tool = _multi_channel_tool(
    wechat_expert,
    tool_name="generate_wechat_content",
    tool_description="Generate 微信公众号 long-form articles.",
)
oschina_tool = _multi_channel_tool(
    oschina_expert,
    tool_name="generate_oschina_content",
    tool_description="Generate OSChina (开源中国) project listings and articles.",
)
gitcode_tool = _multi_channel_tool(
    gitcode_expert,
    tool_name="generate_gitcode_content",
    tool_description="Generate GitCode repository setup and CSDN companion articles.",
)
sspai_tool = _multi_channel_tool(
    sspai_expert,
    tool_name="generate_sspai_content",
    tool_description="Generate 少数派 tool review and productivity articles.",
)
infoq_tool = _multi_channel_tool(
    infoq_expert,
    tool_name="generate_infoq_content",
    tool_description="Generate InfoQ deep-dive architecture and technical articles.",
)
devto_tool = _multi_channel_tool(
    devto_expert,
    tool_name="generate_devto_content",
    tool_description="Generate Dev.to developer blog articles and tutorials.",
)
trend_tool = trend_agent.as_tool(
    tool_name="research_trends",
    tool_description="Research trending topics across community platforms (Reddit, HN, YouTube, Bluesky, Twitter/X, Dev.to). Supports comparative mode for 'X vs Y' queries.",
)
github_outreach_tool = github_outreach_agent.as_tool(
    tool_name="github_user_discovery",
    tool_description="Discover GitHub users from a seed profile's followers/following, enrich profiles, score leads, and generate personalized batch outreach messages.",
)

cmo_agent = Agent(
    name="CMO Agent",
    instructions=build_prompt(
        base_instructions="""You are an AI Chief Marketing Officer (CMO) helping indie developers and startup founders create marketing content for their products.

Your job is to think like a real marketing leader, not a generic assistant. Convert product facts into audience-aware positioning, channel strategy, differentiated messaging, and the next best growth move.

## Your Workflow

1. **When the user provides a website URL**: Use the `crawl_website` tool to fetch and analyze the product's website content. Then extract:
   - **One-liner**: A single sentence describing what the product does
   - **Three core selling points**: The key value propositions
   - **Target audience**: Who would benefit most from this product
   - **Pain + promise**: What tension the audience feels and what outcome the product promises

2. **Based on user request**, route to the appropriate expert:
   - Twitter/X content → Twitter/X Expert
   - Reddit posts → Reddit Expert
   - LinkedIn posts → LinkedIn Expert
   - Product Hunt launch → Product Hunt Expert
   - Hacker News Show HN → Hacker News Expert
   - Blog/SEO content → Blog/SEO Expert
   - SEO site audit → SEO Audit Expert
   - AI crawler access / robots.txt AI check → SEO Audit Expert
   - llms.txt validation or generation → SEO Audit Expert
   - AI visibility / GEO score → AI Visibility Expert
   - Citability analysis / AI citation scoring → AI Visibility Expert
   - Brand presence / digital footprint → AI Visibility Expert
   - Community monitoring (Reddit/HN discussions) → Community Monitor
   - Trend research / what's hot / topic exploration → Trend Research
   - GitHub user discovery / developer outreach / batch marketing / find GitHub users → GitHub Outreach Expert
   - Multi-page site audit / content depth / internal links / meta duplicates → use `audit_site_pages` tool
   - Keyword suggestions / keyword difficulty / what to target → use `suggest_keywords` tool
   - Content publishing frequency / blog activity → use `check_content_frequency` tool
   - Landing page CTA / conversion audit → use `audit_landing_page_cta` tool
   - Google Search Console / indexing / search performance → use `check_search_console` tool
   - Competitive landscape / keyword gaps / graph intelligence → use `get_competitive_landscape` tool
   - 阮一峰周刊投稿 → 阮一峰周刊专家
   - 知乎文章/回答 → 知乎专家
   - 小红书笔记 → 小红书专家
   - V2EX 帖子 → V2EX 专家
   - 掘金技术文 → 掘金专家
   - 即刻动态 → 即刻专家
   - 微信公众号文章 → 微信公众号专家
   - OSChina/开源中国 → OSChina 专家
   - GitCode/CSDN → GitCode 专家
   - 少数派文章 → 少数派专家
   - InfoQ 投稿 → InfoQ 专家
   - Dev.to article → Dev.to Expert

3. **Routing rules**:
   - **Single platform request** → use handoff to transfer to that expert for deep interaction. Do not call the generate_* tool wrappers for single-platform requests.
   - **Multi-channel / full-platform / comprehensive plan** → ALWAYS use `generate_research_brief` FIRST to create a shared context document, then pass that brief to each channel expert via the generate_* tools. This ensures all channel content is consistent.
   - This is critical: for multi-channel, do NOT handoff — use the tool versions so you can collect all outputs and present a cohesive summary
   - The research brief creates a Campaign Run that tracks all generated content as artifacts

4. **Deep Search / Web Search**: Use `deep_search` when research needs a transparent Search -> Read -> Search loop, especially for competitor/market research where traceability matters. Use `web_search` for quick real-time lookups.

5. **Competitor Analysis**: Use `analyze_competitor` to get structured data about a competitor's product, then use insights to differentiate content.

6. **Graph Intelligence**: When a `[Project Context]` block appears in the conversation, it contains a knowledge graph summary with competitors, keyword overlaps, SERP rankings, and gaps. Use it to ground your recommendations. For deeper analysis, call `get_competitive_landscape` with the project_id.

7. **For follow-up requests**: Maintain context from previous interactions. If the user asks for modifications (e.g., "make it more technical", "shorter"), apply the changes while keeping the same product context.

## Platform Priority Guide
When the user asks for "全平台" or "comprehensive" distribution, prioritize in this order:
- ⭐⭐⭐⭐⭐: 阮一峰周刊, 知乎, 小红书, Product Hunt
- ⭐⭐⭐⭐: Hacker News, V2EX, 掘金
- ⭐⭐⭐: Twitter/X, 即刻, 微信公众号, OSChina, 少数派, Dev.to, Reddit
- ⭐⭐: GitCode, InfoQ

## Important Rules
- Crawl the website first if a URL is provided (unless already crawled in the conversation). If the user gives enough product context without a URL, proceed directly.
- After crawling, briefly share your product analysis (one-liner, selling points, target audience) only when it materially helps the user understand the recommendation. For direct content requests, skip the visible analysis and go straight to the draft.
- For single-platform content requests, do not draft, summarize, or editorialize before the handoff. Hand off immediately once you have enough context.
- In that product analysis, always include:
  - Audience
  - Pain
  - Promise
  - Proof (if available)
- When using handoff, the product analysis context is passed automatically.
- When using generate_* tools, include your product analysis in the tool input.
- If the user doesn't specify a platform, ask which platform(s) they'd like content for.
- Communicate in the same language the user uses (Chinese, English, etc.).
""",
        task_contract="""## Task Contract
- Judgment first: start with the clearest business or messaging judgment before expanding into options
- When evidence is incomplete, say exactly what is known, what is inferred, and what still needs validation
- If the user asks for strategy, default to: diagnosis, reasoning, priority, next move
- If the user asks for content, ground the brief in audience, pain, promise, and proof internally before routing or drafting
- For direct platform content requests, do not narrate routing, handoffs, internal checklists, or internal briefing labels to the user; use them internally and then let the platform expert answer
- For single-platform requests, never wrap or rewrite the platform expert's content pack yourself
""",
    ),
    tools=[
        crawl_website,
        deep_search,
        web_search,
        analyze_competitor,
        generate_research_brief,
        # as_tool wrappers for multi-channel orchestration
        twitter_tool,
        reddit_tool,
        linkedin_tool,
        producthunt_tool,
        hackernews_tool,
        blog_tool,
        ruanyifeng_tool,
        zhihu_tool,
        xiaohongshu_tool,
        v2ex_tool,
        juejin_tool,
        jike_tool,
        wechat_tool,
        oschina_tool,
        gitcode_tool,
        sspai_tool,
        infoq_tool,
        devto_tool,
        trend_tool,
        github_outreach_tool,
        get_competitive_landscape,
        # Growth checklist tools (site-wide audit, keywords, content, CTA, GSC)
        audit_site_pages,
        suggest_keywords,
        check_content_frequency,
        audit_landing_page_cta,
        check_search_console,
    ],
    handoffs=[
        handoff(
            twitter_expert,
            tool_description_override="Transfer to Twitter/X expert for tweet and thread writing.",
        ),
        handoff(
            reddit_expert,
            tool_description_override="Transfer to Reddit expert for authentic community posts.",
        ),
        handoff(
            linkedin_expert,
            tool_description_override="Transfer to LinkedIn expert for professional posts.",
        ),
        handoff(
            producthunt_expert,
            tool_description_override="Transfer to Product Hunt expert for launch copy.",
        ),
        handoff(
            hackernews_expert,
            tool_description_override="Transfer to Hacker News expert for Show HN posts.",
        ),
        handoff(
            blog_expert,
            tool_description_override="Transfer to Blog/SEO expert for article content and SEO recommendations.",
        ),
        handoff(
            seo_agent,
            tool_description_override="Transfer to SEO audit expert for technical website SEO analysis.",
        ),
        handoff(
            geo_agent,
            tool_description_override="Transfer to AI visibility expert to check brand mentions in AI search engines and compute GEO score.",
        ),
        handoff(
            community_agent,
            tool_description_override="Transfer to community monitor to scan Reddit, Hacker News, Dev.to and other platforms for brand discussions, fetch post details, and draft context-aware replies.",
        ),
        handoff(
            trend_agent,
            tool_description_override="Transfer to trend research specialist to explore what communities are discussing and identify content opportunities across platforms.",
        ),
        handoff(
            ruanyifeng_expert,
            tool_description_override="Transfer to 阮一峰周刊 expert for GitHub Issue submission drafts.",
        ),
        handoff(
            zhihu_expert,
            tool_description_override="Transfer to 知乎 expert for articles and Q&A answers.",
        ),
        handoff(
            xiaohongshu_expert,
            tool_description_override="Transfer to 小红书 expert for image-text notes.",
        ),
        handoff(
            v2ex_expert,
            tool_description_override="Transfer to V2EX expert for developer community posts.",
        ),
        handoff(
            juejin_expert,
            tool_description_override="Transfer to 掘金 expert for technical blog articles.",
        ),
        handoff(
            jike_expert,
            tool_description_override="Transfer to 即刻 expert for indie dev community posts.",
        ),
        handoff(
            wechat_expert,
            tool_description_override="Transfer to 微信公众号 expert for WeChat long-form articles.",
        ),
        handoff(
            oschina_expert,
            tool_description_override="Transfer to OSChina expert for open-source project listings.",
        ),
        handoff(
            gitcode_expert,
            tool_description_override="Transfer to GitCode expert for CSDN/GitCode repository setup.",
        ),
        handoff(
            sspai_expert,
            tool_description_override="Transfer to 少数派 expert for tool review and productivity articles.",
        ),
        handoff(
            infoq_expert,
            tool_description_override="Transfer to InfoQ expert for enterprise-grade technical articles.",
        ),
        handoff(
            devto_expert,
            tool_description_override="Transfer to Dev.to expert for developer blog articles and tutorials.",
        ),
        handoff(
            github_outreach_agent,
            tool_description_override="Transfer to GitHub outreach expert for developer discovery and personalized batch outreach via GitHub social graphs.",
        ),
    ],
    model=get_model("cmo"),
)
