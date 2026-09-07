import re
from pathlib import Path


def test_site_stats_is_frontend_public_byok_path() -> None:
    client_ts = Path("frontend/src/api/client.ts").read_text()
    public_paths_match = re.search(r"PUBLIC_BYOK_PATHS = new Set\(\[(.*?)\]\);", client_ts, re.S)

    assert public_paths_match is not None
    assert '"/site/stats"' in public_paths_match.group(1)


def test_frontend_user_keys_include_gsc_and_chinese_geo_providers() -> None:
    user_keys_ts = Path("frontend/src/api/userKeys.ts").read_text(encoding='utf-8')

    for key in (
        "GOOGLE_GSC_CREDENTIALS",
        "GOOGLE_GSC_SITE_URL",
        "MOONSHOT_API_KEY",
        "DASHSCOPE_API_KEY",
        "DEEPSEEK_API_KEY",
        "ZHIPU_API_KEY",
        "DOUBAO_API_KEY",
    ):
        assert f'"{key}"' in user_keys_ts
