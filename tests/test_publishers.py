"""Tests for auto-publish tools — Reddit + Twitter with safety gates."""

from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Reddit
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_publish_reddit_dry_run():
    """Default (dry_run=True) returns preview, never posts — works without praw."""
    from opencmo.tools.publishers import publish_reddit_post_impl

    result = await publish_reddit_post_impl("SideProject", "Test Title", "Test body", dry_run=True)
    assert result["ok"]
    assert result["dry_run"]
    assert "preview" in result


@pytest.mark.asyncio
async def test_publish_reddit_no_consent():
    """publish_reddit_post_impl with dry_run always returns preview regardless of env."""
    from opencmo.tools.publishers import publish_reddit_post_impl

    result = await publish_reddit_post_impl("test", "title", "body", dry_run=True)
    assert result["ok"]
    assert result["dry_run"]
    assert result["preview"]["subreddit"] == "test"


@pytest.mark.asyncio
async def test_publish_reddit_success(monkeypatch):
    """Real publish with mocked praw."""
    from opencmo import llm

    token = llm.set_request_keys({
        "REDDIT_CLIENT_ID": "test_id",
        "REDDIT_CLIENT_SECRET": "test_secret",
        "REDDIT_USERNAME": "test_user",
        "REDDIT_PASSWORD": "test_pass",
    })
    try:
        import opencmo.tools.publishers as pub

        mock_submission = MagicMock()
        mock_submission.permalink = "/r/test/comments/abc123"
        mock_submission.id = "abc123"

        mock_sub = MagicMock()
        mock_sub.submit = MagicMock(return_value=mock_submission)

        mock_reddit = MagicMock()
        mock_reddit.subreddit = MagicMock(return_value=mock_sub)

        mock_praw = MagicMock()
        mock_praw.Reddit = MagicMock(return_value=mock_reddit)

        pub._HAS_PRAW = True
        monkeypatch.setattr(pub, "praw", mock_praw, raising=False)

        result = await pub.publish_reddit_post_impl("test", "Title", "Body", dry_run=False)

        assert result["ok"]
        assert not result["dry_run"]
        assert "reddit.com" in result["url"]
    finally:
        llm.reset_request_keys(token)


@pytest.mark.asyncio
async def test_publish_reddit_error(monkeypatch):
    """Reddit API error returns error dict, doesn't raise."""
    from opencmo import llm

    token = llm.set_request_keys({
        "REDDIT_CLIENT_ID": "id",
        "REDDIT_CLIENT_SECRET": "secret",
        "REDDIT_USERNAME": "user",
        "REDDIT_PASSWORD": "pass",
    })
    try:
        import opencmo.tools.publishers as pub

        mock_praw = MagicMock()
        mock_praw.Reddit = MagicMock(side_effect=Exception("Auth failed"))

        pub._HAS_PRAW = True
        monkeypatch.setattr(pub, "praw", mock_praw, raising=False)

        result = await pub.publish_reddit_post_impl("test", "T", "B", dry_run=False)

        assert not result["ok"]
        assert "Auth failed" in result["error"]
    finally:
        llm.reset_request_keys(token)


@pytest.mark.asyncio
async def test_praw_not_installed():
    """When praw is not installed, non-dry-run publish returns error."""
    import opencmo.tools.publishers as pub

    original = pub._HAS_PRAW
    pub._HAS_PRAW = False
    try:
        result = await pub.publish_reddit_post_impl("test", "T", "B", dry_run=False)
        assert not result["ok"]
        assert "praw" in result["error"]
    finally:
        pub._HAS_PRAW = original


# ---------------------------------------------------------------------------
# Twitter
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_publish_tweet_dry_run():
    """Default dry_run returns preview — works without tweepy."""
    from opencmo.tools.publishers import publish_tweet_impl

    result = await publish_tweet_impl("Hello world!", dry_run=True)
    assert result["ok"]
    assert result["dry_run"]
    assert result["preview"]["length"] == 12


@pytest.mark.asyncio
async def test_publish_tweet_too_long():
    """Tweet > 280 chars is rejected before any API call."""
    from opencmo.tools.publishers import publish_tweet_impl

    long_text = "x" * 281
    result = await publish_tweet_impl(long_text, dry_run=False)
    assert not result["ok"]
    assert "too long" in result["error"].lower()


@pytest.mark.asyncio
async def test_publish_tweet_success(monkeypatch):
    """Real publish with mocked tweepy."""
    from opencmo import llm

    token = llm.set_request_keys({
        "TWITTER_API_KEY": "key",
        "TWITTER_API_SECRET": "secret",
        "TWITTER_ACCESS_TOKEN": "token",
        "TWITTER_ACCESS_SECRET": "secret",
    })
    try:
        import opencmo.tools.publishers as pub

        mock_response = MagicMock()
        mock_response.data = {"id": "12345"}

        mock_client = MagicMock()
        mock_client.create_tweet = MagicMock(return_value=mock_response)

        mock_tweepy = MagicMock()
        mock_tweepy.Client = MagicMock(return_value=mock_client)

        pub._HAS_TWEEPY = True
        monkeypatch.setattr(pub, "tweepy", mock_tweepy, raising=False)

        result = await pub.publish_tweet_impl("Hello!", dry_run=False)

        assert result["ok"]
        assert result["tweet_id"] == "12345"
    finally:
        llm.reset_request_keys(token)


@pytest.mark.asyncio
async def test_tweepy_not_installed():
    """When tweepy is not installed, non-dry-run publish returns error."""
    import opencmo.tools.publishers as pub

    original = pub._HAS_TWEEPY
    pub._HAS_TWEEPY = False
    try:
        result = await pub.publish_tweet_impl("test", dry_run=False)
        assert not result["ok"]
        assert "tweepy" in result["error"]
    finally:
        pub._HAS_TWEEPY = original
