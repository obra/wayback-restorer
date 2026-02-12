from __future__ import annotations

from pathlib import Path

from sp_recovery.rewrite import (
    RewriteResult,
    extract_internal_asset_urls,
    rewrite_html,
    write_unresolved_links_csv,
)


def test_rewrite_html_converts_internal_links_to_local_paths() -> None:
    html = (
        '<a href="sp02022024.html">next</a>'
        '<img src="arch/sp02012024.gif" />'
        '<a href="https://example.org/post">external</a>'
    )

    result = rewrite_html(
        html,
        page_original_url="http://www.somethingpositive.net:80/sp02012024.html",
        known_local_paths={
            "somethingpositive.net/sp02022024.html",
            "somethingpositive.net/arch/sp02012024.gif",
        },
    )

    assert isinstance(result, RewriteResult)
    assert 'href="/somethingpositive.net/sp02022024.html"' in result.html
    assert 'src="/somethingpositive.net/arch/sp02012024.gif"' in result.html
    assert 'href="https://example.org/post"' in result.html
    assert result.unresolved_targets == []


def test_unresolved_internal_targets_are_written_to_csv(tmp_path: Path) -> None:
    result = rewrite_html(
        '<a href="sp99999999.html">missing</a>',
        page_original_url="http://www.somethingpositive.net/sp02012024.html",
        known_local_paths=set(),
    )

    out_file = tmp_path / "state" / "unresolved_links.csv"
    write_unresolved_links_csv(out_file, result.unresolved_targets)

    lines = out_file.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "source_url,target_local_path"
    assert (
        lines[1]
        == "http://www.somethingpositive.net/sp02012024.html,somethingpositive.net/sp99999999.html"
    )


def test_rewrite_html_handles_root_relative_internal_urls() -> None:
    html = '<a href="/sp02022024.html">next</a><img src="/arch/sp02012024.gif" />'

    result = rewrite_html(
        html,
        page_original_url="http://www.somethingpositive.net:80/sp02012024.html",
        known_local_paths={
            "somethingpositive.net/sp02022024.html",
            "somethingpositive.net/arch/sp02012024.gif",
        },
    )

    assert 'href="/somethingpositive.net/sp02022024.html"' in result.html
    assert 'src="/somethingpositive.net/arch/sp02012024.gif"' in result.html
    assert result.unresolved_targets == []


def test_extract_internal_asset_urls_handles_root_relative_urls() -> None:
    html = (
        '<img src="/arch/sp02012024.gif" />'
        '<img src="images/title.gif" />'
        '<img src="https://example.org/outside.gif" />'
    )

    extracted = extract_internal_asset_urls(
        html,
        page_original_url="http://www.somethingpositive.net:80/sp02012024.html",
    )

    assert extracted == [
        "http://somethingpositive.net/arch/sp02012024.gif",
        "http://somethingpositive.net/images/title.gif",
    ]
