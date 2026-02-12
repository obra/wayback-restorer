from __future__ import annotations

from pathlib import Path

from sp_recovery.rewrite import RewriteResult, rewrite_html, write_unresolved_links_csv


def test_rewrite_html_converts_internal_links_to_local_paths() -> None:
    html = (
        '<a href="sp02022024.html">next</a>'
        '<img src="arch/sp02012024.gif" />'
        '<a href="https://example.org/post">external</a>'
    )

    result = rewrite_html(
        html,
        page_original_url="http://www.somethingpositive.net/sp02012024.html",
        known_local_paths={
            "www.somethingpositive.net/sp02022024.html",
            "www.somethingpositive.net/arch/sp02012024.gif",
        },
    )

    assert isinstance(result, RewriteResult)
    assert 'href="/www.somethingpositive.net/sp02022024.html"' in result.html
    assert 'src="/www.somethingpositive.net/arch/sp02012024.gif"' in result.html
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
        == "http://www.somethingpositive.net/sp02012024.html,www.somethingpositive.net/sp99999999.html"
    )
