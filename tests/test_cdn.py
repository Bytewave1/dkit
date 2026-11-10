"""Tests for ``dkit cdn``."""

from __future__ import annotations

import json
import re

import pytest

from dkit.commands.cdn import build_url, endpoints
from dkit.core import data


def test_endpoint_table_matches_the_docs(cli) -> None:
    payload = cli("--json", "cdn", "--list").json
    assert payload["mode"] == "list"
    assert payload["count"] == len(endpoints()) == 21
    types = [entry["type"] for entry in payload["endpoints"]]
    assert "avatar" in types
    assert "default-avatar" in types
    assert "sticker" in types
    assert payload["source"]["last_verified"] == "2026-11-10"


def test_avatar_url_with_format_and_size(cli) -> None:
    result = cli(
        "--json",
        "cdn",
        "avatar",
        "80351110224678912",
        "a_1269e74af4df7417b13759eae50c83dc",
        "--format",
        "webp",
        "--size",
        "256",
    ).json
    assert result["mode"] == "url"
    assert result["url"] == (
        "https://cdn.discordapp.com/avatars/80351110224678912/"
        "a_1269e74af4df7417b13759eae50c83dc.webp?size=256"
    )


def test_png_is_the_default_format(cli) -> None:
    payload = build_url("guild-icon", ["123456789012345678", "abc123"])
    assert payload["url"] == "https://cdn.discordapp.com/icons/123456789012345678/abc123.png"


def test_jpeg_uses_the_jpg_extension(cli) -> None:
    payload = build_url("guild-splash", ["123456789012345678", "abc123"], format_name="jpeg")
    assert payload["url"].endswith("/abc123.jpg")


def test_animated_webp_adds_the_querystring() -> None:
    payload = build_url(
        "avatar",
        ["80351110224678912", "a_1269e74af4df7417b13759eae50c83dc"],
        format_name="webp",
        animated=True,
    )
    assert payload["url"].endswith("?animated=true")


def test_animated_requires_an_a_hash() -> None:
    with pytest.raises(Exception, match="starts with a_"):
        build_url("avatar", ["80351110224678912", "abc123"], format_name="webp", animated=True)


def test_gif_rejected_for_non_animated_endpoint() -> None:
    with pytest.raises(Exception, match="does not support"):
        build_url("guild-splash", ["123456789012345678", "abc123"], format_name="gif")


def test_gif_allowed_for_a_hash() -> None:
    payload = build_url("avatar", ["80351110224678912", "a_abc123"], format_name="gif")
    assert payload["url"].endswith("/a_abc123.gif")


def test_size_must_be_a_power_of_two() -> None:
    for bad in ("100", "8", "8192"):
        with pytest.raises(Exception, match="power of two"):
            build_url("avatar", ["80351110224678912", "abc123"], size=bad)
    payload = build_url("avatar", ["80351110224678912", "abc123"], size="4096")
    assert payload["url"].endswith("?size=4096")


def test_size_must_be_an_integer() -> None:
    with pytest.raises(Exception, match="not an integer"):
        build_url("avatar", ["80351110224678912", "abc123"], size="abc")


def test_empty_hash_is_rejected() -> None:
    with pytest.raises(Exception, match="hash is empty"):
        build_url("avatar", ["80351110224678912", ""])


def test_animated_rejected_for_stickers() -> None:
    with pytest.raises(Exception, match="does not apply to stickers"):
        build_url("sticker", ["813248342119698674"], format_name="gif", animated=True)


def test_animated_requires_the_webp_format() -> None:
    with pytest.raises(Exception, match="only applies to --format webp"):
        build_url("avatar", ["80351110224678912", "a_abc123"], format_name="png", animated=True)


def test_animated_rejected_for_never_animated_endpoints() -> None:
    with pytest.raises(Exception, match="never animated"):
        build_url("app-icon", ["123456789012345678", "abc123"], format_name="webp", animated=True)


def test_default_avatar_index_from_user_id(cli) -> None:
    payload = cli("--json", "cdn", "default-avatar", "80351110224678912").json
    assert payload["index"] == (80351110224678912 >> 22) % 6 == 5
    assert payload["url"] == "https://cdn.discordapp.com/embed/avatars/5.png"
    assert payload["size_ignored"] is True


def test_default_avatar_from_legacy_discriminator() -> None:
    payload = build_url("default-avatar", ["80351110224678912"], discriminator="1234")
    assert payload["index"] == 1234 % 5 == 4


def test_default_avatar_rejects_discriminator_zero() -> None:
    with pytest.raises(Exception, match="new username system"):
        build_url("default-avatar", ["80351110224678912"], discriminator="0")


def test_default_avatar_rejects_a_non_numeric_discriminator() -> None:
    with pytest.raises(Exception, match="not a number"):
        build_url("default-avatar", ["80351110224678912"], discriminator="abcd")


def test_default_avatar_takes_exactly_one_argument() -> None:
    with pytest.raises(Exception, match="takes 1 argument"):
        build_url("default-avatar", [])


def test_default_avatar_size_is_appended_but_marked_ignored() -> None:
    payload = build_url("default-avatar", ["80351110224678912"], size="256")
    assert payload["url"].endswith("?size=256")
    assert payload["size_ignored"] is True


def test_list_cannot_be_combined_with_a_type(cli) -> None:
    result = cli("cdn", "--list", "avatar")
    assert result.exit_code == 2


def test_no_type_given_is_a_usage_error(cli) -> None:
    result = cli("cdn")
    assert result.exit_code == 2


def test_sticker_gif_uses_media_base_url() -> None:
    payload = build_url("sticker", ["813248342119698674"], format_name="gif")
    assert payload["url"] == "https://media.discordapp.net/stickers/813248342119698674.gif"


def test_sticker_lottie_uses_the_json_extension() -> None:
    payload = build_url("sticker", ["813248342119698674"], format_name="lottie")
    assert payload["url"] == "https://cdn.discordapp.com/stickers/813248342119698674.json"


def test_sticker_png_keeps_the_documented_path() -> None:
    payload = build_url("sticker", ["813248342119698674"])
    assert payload["url"] == "https://cdn.discordapp.com/stickers/813248342119698674.png"


def test_store_asset_has_no_extension() -> None:
    payload = build_url("store-asset", ["123456789012345678", "abc123"])
    assert payload["url"] == "https://cdn.discordapp.com/app-assets/123456789012345678/store/abc123"


def test_member_avatar_takes_three_arguments() -> None:
    payload = build_url("member-avatar", ["111", "222", "abc123"])
    assert payload["url"] == "https://cdn.discordapp.com/guilds/111/users/222/avatars/abc123.png"
    with pytest.raises(Exception, match="takes 3 arguments"):
        build_url("member-avatar", ["111", "abc123"])


def test_ids_go_through_snowflake_parsing() -> None:
    with pytest.raises(Exception, match="snowflake"):
        build_url("avatar", ["not-a-number", "abc123"])


def test_unknown_type_suggests_the_closest_name(cli) -> None:
    result = cli("cdn", "avatr", "80351110224678912", "abc123")
    assert result.exit_code == 2
    assert "avatar" in result.stdout + result.stderr


def test_wrong_format_for_endpoint_is_a_usage_error(cli) -> None:
    result = cli("cdn", "app-icon", "123456789012345678", "abc123", "--format", "gif")
    assert result.exit_code == 2


def test_json_payload_carries_provenance(cli) -> None:
    payload = cli("--json", "cdn", "avatar", "80351110224678912", "abc123").json
    assert payload["source"]["last_verified"] == "2026-11-10"
    assert payload["source"]["source_rendered"] == (
        "https://discord.com/developers/docs/reference#image-formatting"
    )


def test_text_output_prints_the_url(cli) -> None:
    result = cli("cdn", "avatar", "80351110224678912", "a_1269e74af4df7417b13759eae50c83dc")
    assert result.exit_code == 0
    assert (
        "https://cdn.discordapp.com/avatars/80351110224678912/"
        "a_1269e74af4df7417b13759eae50c83dc.png" in result.stdout
    )


def test_cdn_json_is_wellformed() -> None:
    cdn = data.load("cdn")
    assert json.dumps(cdn)  # serialisable
    for entry in cdn["endpoints"]:
        assert entry["args"] and entry["path"] and entry["formats"]
        if not entry.get("no_extension"):
            assert entry["path"].endswith(".png"), entry["type"]
        placeholders = set(re.findall(r"\{([a-z_]+)\}", entry["path"])) - {"hash"}
        ids = {arg for arg in entry["args"] if arg.endswith("_id")}
        if "index" not in entry["path"]:
            assert placeholders == ids, entry["type"]
