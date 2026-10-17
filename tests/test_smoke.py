"""Smoke tests — verify agent/tool structure without API calls."""


def test_imports():
    """All modules can be imported without error."""
    from opencmo.agents import (
        cmo_agent,
    )
    from opencmo.tools import (
        check_keyword_ranking,
        crawl_website,
        deep_search,
        publish_to_reddit,
    )
    # Just verify they exist
    assert cmo_agent is not None
    assert crawl_website is not None
    assert deep_search is not None
    assert check_keyword_ranking is not None
    assert publish_to_reddit is not None


def test_cmo_has_tools_and_handoffs():
    from opencmo.agents import cmo_agent

    assert len(cmo_agent.tools) > 0, "CMO should have tools"
    assert len(cmo_agent.handoffs) > 0, "CMO should have handoffs"
    tool_names = [t.name for t in cmo_agent.tools if hasattr(t, "name")]
    assert "deep_search" in tool_names


def test_cmo_has_as_tool_wrappers():
    """CMO should have generate_* tools for multi-channel mode."""
    from opencmo.agents import cmo_agent

    tool_names = [t.name for t in cmo_agent.tools if hasattr(t, "name")]
    assert "generate_twitter_content" in tool_names
    assert "generate_reddit_content" in tool_names
    assert "generate_linkedin_content" in tool_names


def test_cmo_generate_tools_are_marked_multi_channel_only():
    from opencmo.agents.cmo import linkedin_tool, reddit_tool, twitter_tool

    for tool in [twitter_tool, reddit_tool, linkedin_tool]:
        assert "Use ONLY for coordinated multi-channel orchestration" in tool.description
        assert "Never use this for a single-platform request" in tool.description


def test_cmo_handoffs_have_descriptions():
    """Each handoff should have a tool_description_override."""
    from opencmo.agents import cmo_agent

    for h in cmo_agent.handoffs:
        # handoff objects have tool_name and tool_description
        assert hasattr(h, "tool_description") or hasattr(h, "tool_name")


def test_all_experts_have_instructions():
    from opencmo.agents import (
        blog_expert,
        community_agent,
        geo_agent,
        hackernews_expert,
        linkedin_expert,
        producthunt_expert,
        reddit_expert,
        seo_agent,
        twitter_expert,
    )

    for agent in [
        twitter_expert,
        reddit_expert,
        linkedin_expert,
        producthunt_expert,
        hackernews_expert,
        blog_expert,
        seo_agent,
        geo_agent,
        community_agent,
    ]:
        assert agent.instructions, f"{agent.name} missing instructions"
        assert len(agent.instructions) > 50, f"{agent.name} instructions too short"


def test_blog_expert_has_deep_search_tool():
    from opencmo.agents import blog_expert

    tool_names = [t.name for t in blog_expert.tools if hasattr(t, "name")]
    assert "deep_search" in tool_names


def test_platform_experts_keep_explicit_deliverable_labels():
    from opencmo.agents import (
        hackernews_expert,
        jike_expert,
        linkedin_expert,
        producthunt_expert,
        reddit_expert,
        twitter_expert,
    )

    assert "Tweet 1" in twitter_expert.instructions
    assert "Post 1" in linkedin_expert.instructions
    assert "Primary Post" in reddit_expert.instructions
    assert "Maker Comment" in producthunt_expert.instructions
    assert "Show HN Body" in hackernews_expert.instructions
    assert "动态文案" in jike_expert.instructions


def test_platform_prompt_examples_do_not_contain_hypey_fake_metrics():
    from opencmo.agents import ruanyifeng_expert, sspai_expert, wechat_expert, xiaohongshu_expert

    assert "10倍" not in xiaohongshu_expert.instructions
    assert "80%" not in sspai_expert.instructions
    assert "上万元推广费" not in wechat_expert.instructions
    assert "100K+" not in ruanyifeng_expert.instructions


def test_seo_agent_has_tools():
    from opencmo.agents import seo_agent

    assert len(seo_agent.tools) >= 4, "SEO agent needs audit_page_seo + web_search + serp tools"
    tool_names = [t.name for t in seo_agent.tools if hasattr(t, "name")]
    assert "check_keyword_ranking" in tool_names
    assert "get_serp_trends" in tool_names


def test_geo_agent_has_tools():
    from opencmo.agents import geo_agent

    assert len(geo_agent.tools) >= 2, "GEO agent needs scan_geo_visibility + web_search"


def test_community_agent_has_tools():
    from opencmo.agents import community_agent

    assert len(community_agent.tools) >= 3, "Community agent needs scan_community + fetch_discussion_detail + web_search"


def test_blog_expert_has_tools():
    from opencmo.agents import blog_expert

    assert len(blog_expert.tools) >= 3, "Blog expert needs web_search + crawl_website + research_blog_topic"
    tool_names = [t.name for t in blog_expert.tools if hasattr(t, "name")]
    assert "research_blog_topic" in tool_names


def test_reddit_expert_has_publish_tool():
    from opencmo.agents import reddit_expert

    assert len(reddit_expert.tools) >= 1
    tool_names = [t.name for t in reddit_expert.tools if hasattr(t, "name")]
    assert "publish_to_reddit" in tool_names


def test_twitter_expert_has_publish_tool():
    from opencmo.agents import twitter_expert

    assert len(twitter_expert.tools) >= 1
    tool_names = [t.name for t in twitter_expert.tools if hasattr(t, "name")]
    assert "publish_to_twitter" in tool_names


def test_markdown_extraction():
    """Test _extract_markdown handles str, None, and object types."""
    from opencmo.tools.crawl import _extract_markdown

    # str case
    mock_str = type("R", (), {"markdown": "hello"})()
    assert _extract_markdown(mock_str) == "hello"

    # None case
    mock_none = type("R", (), {"markdown": None})()
    assert _extract_markdown(mock_none) == ""

    # Object with raw_markdown
    inner = type("MD", (), {"raw_markdown": "from object"})()
    mock_obj = type("R", (), {"markdown": inner})()
    assert _extract_markdown(mock_obj) == "from object"

    # Object without raw_markdown — falls back to str()
    inner2 = type("MD", (), {})()
    mock_obj2 = type("R", (), {"markdown": inner2})()
    result = _extract_markdown(mock_obj2)
    assert isinstance(result, str)
