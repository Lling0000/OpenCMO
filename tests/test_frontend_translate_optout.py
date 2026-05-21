"""Regression tests for issue #26: Chrome Translate blanks the SPA.

Chrome/Google Translate replaces text nodes inside the React-managed DOM,
which breaks reconciliation and surfaces as
`NotFoundError: Failed to execute 'insertBefore' on 'Node'` followed by
`#root` being emptied. We mitigate this by marking the body and `#root`
with `translate="no"` / `notranslate`, plus a `<meta name="google"
content="notranslate">` hint. The static SEO copy in
`<main id="static-site-copy">` opts back in via `translate="yes"` so
crawlers still see it.

These tests guard those markers so a future edit to `index.html` cannot
silently regress the fix.
"""

from __future__ import annotations

import re
from pathlib import Path

_INDEX_HTML = Path("frontend/index.html")


def _read_index_html() -> str:
    text = _INDEX_HTML.read_text(encoding="utf-8")
    assert text, "frontend/index.html should not be empty"
    return text


def _strip_html_comments(text: str) -> str:
    """Drop HTML comments so the example markup inside our own opt-out comment
    block doesn't accidentally satisfy / shadow the real tag regexes.
    """
    return re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)


def test_index_html_has_google_notranslate_meta() -> None:
    text = _read_index_html()
    assert re.search(
        r'<meta\s+name="google"\s+content="notranslate"\s*/?>',
        text,
    ), 'expected <meta name="google" content="notranslate"> opt-out hint'


def test_body_opts_out_of_translation() -> None:
    text = _strip_html_comments(_read_index_html())
    body_match = re.search(r"<body(\s[^>]*)?>", text)
    assert body_match, "frontend/index.html should declare a <body> tag"
    attrs = body_match.group(1) or ""
    assert 'translate="no"' in attrs, "<body> must carry translate=\"no\""
    assert "notranslate" in attrs, "<body> class list must include 'notranslate'"


def test_react_root_opts_out_of_translation() -> None:
    text = _strip_html_comments(_read_index_html())
    root_match = re.search(r'<div\s+id="root"(\s[^>]*)?>', text)
    assert root_match, "frontend/index.html should declare <div id=\"root\"> for React"
    attrs = root_match.group(1) or ""
    assert 'translate="no"' in attrs, "#root must carry translate=\"no\""
    assert "notranslate" in attrs, "#root must include the 'notranslate' class"


def test_static_seo_copy_remains_translatable() -> None:
    """SEO/no-JS fallback copy lives outside #root; it should stay translatable
    so crawlers and translated previews can still read it.
    """
    text = _strip_html_comments(_read_index_html())
    main_match = re.search(r'<main\s+id="static-site-copy"(\s[^>]*)?>', text)
    assert main_match, "static SEO copy <main> should be present"
    attrs = main_match.group(1) or ""
    assert 'translate="yes"' in attrs, (
        "static SEO copy must explicitly opt back into translation, "
        "otherwise the body-level translate=\"no\" would suppress it too"
    )
