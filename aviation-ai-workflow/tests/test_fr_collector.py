"""Offline tests: no Federal Register connection or credentials needed."""

import argparse
import sqlite3
from pathlib import Path

import pytest

from src.aerocie.fr_collector import (
    canonical_record, fetch_json, fingerprint, ingest, initialize,
    published_query, run, search_published,
)


SAMPLE = {
    "document_number": "2024-06419",
    "title": "Airworthiness Directives; Certain Turbofan Engines",
    "type": "RULE",
    "publication_date": "2024-03-27",
    "effective_on": "2024-04-11",
    "html_url": "https://www.federalregister.gov/documents/2024/03/27/2024-06419/",
    "pdf_url": "https://www.govinfo.gov/content/pkg/FR-2024-03-27/pdf/2024-06419.pdf",
}


def test_query_filters_and_dates_remain_separate():
    q = dict(published_query(since="2024-03-01", cfr_part=450, term="launch"))
    assert q["conditions[publication_date][gte]"] == "2024-03-01"
    assert q["conditions[cfr][title]"] == "14"
    assert q["conditions[cfr][part]"] == "450"
    assert q["conditions[term]"] == "launch"
    assert "effective_on" not in q


def test_reject_invalid_search_date_and_unsafe_paths():
    with pytest.raises(ValueError):
        published_query(since="2024-13-01")
    with pytest.raises(ValueError):
        fetch_json("https://evil.example/exfiltrate")
    with pytest.raises(ValueError):
        fetch_json("../secret")


def test_status_does_not_assume_aircraft_is_affected():
    item = canonical_record(SAMPLE, source="published")
    assert item["verified_asset_applicability"] is False
    assert item["publication_date"] != item["effective_on"]
    inspection = canonical_record(SAMPLE, source="public_inspection")
    assert inspection["status"] == "public_inspection_unpublished"
    assert fingerprint(item) != fingerprint(inspection)


def test_new_unchanged_and_metadata_changed_recorded_without_overwrite():
    with sqlite3.connect(":memory:") as conn:
        initialize(conn)
        a = ingest(conn, SAMPLE, source="published", observed_at="2026-10-20T00:00:00+00:00")
        b = ingest(conn, SAMPLE, source="published", observed_at="2026-10-20T00:01:00+00:00")
        amended_metadata = {**SAMPLE, "title": SAMPLE["title"] + " (corrected metadata)"}
        c = ingest(conn, amended_metadata, source="published", observed_at="2026-10-20T00:02:00+00:00")
        assert [a["event"], b["event"], c["event"]] == ["new", "unchanged", "metadata_changed"]
        assert conn.execute("SELECT COUNT(*) FROM document_snapshots").fetchone()[0] == 2
        assert conn.execute("SELECT COUNT(*) FROM change_events").fetchone()[0] == 2
        assert "corrected metadata" in conn.execute("SELECT diff_excerpt FROM change_events ORDER BY id DESC LIMIT 1").fetchone()[0]


def test_inspection_and_published_are_separate_records():
    with sqlite3.connect(":memory:") as conn:
        initialize(conn)
        ingest(conn, SAMPLE, source="public_inspection")
        ingest(conn, SAMPLE, source="published")
        assert conn.execute("SELECT COUNT(*) FROM document_snapshots").fetchone()[0] == 2


def test_pagination_and_limit():
    calls = []
    def fake_get(path, params=None):
        calls.append((path, dict(params)))
        q = dict(params)
        page = int(q["page"])
        count = int(q["per_page"])
        start = (page - 1) * 100 + 1
        available = max(0, min(count, 101 - start + 1))
        return {"results": [{**SAMPLE, "document_number": f"2024-{i:05d}"}
                            for i in range(start, start + available)]}
    out = search_published(since="2024-03-01", limit=101, get_json=fake_get)
    assert len(out) == 101
    assert len(calls) == 2


def test_run_offline_persists_source_and_status(tmp_path: Path):
    def fake_get(path, params=None):
        if path == "documents.json":
            return {"results": [SAMPLE]}
        raise AssertionError("Unexpected endpoint " + path)
    args = argparse.Namespace(mode="published", since="2024-03-01", limit=3,
                              agency="federal-aviation-administration", cfr_part=None,
                              term=None, document_number=None, db=tmp_path / "fr.sqlite3")
    result = run(args, get_json=fake_get)
    assert result["new"] == 1
    assert result["records_checked"] == 1
    with sqlite3.connect(args.db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM document_snapshots").fetchone()[0] == 1
    again = run(args, get_json=fake_get)
    assert again["unchanged"] == 1


def test_reversion_to_prior_metadata_creates_new_historical_snapshot():
    with sqlite3.connect(":memory:") as conn:
        initialize(conn)
        other = {**SAMPLE, "title": "Temporary metadata change"}
        assert ingest(conn, SAMPLE, source="published")["event"] == "new"
        assert ingest(conn, other, source="published")["event"] == "metadata_changed"
        assert ingest(conn, SAMPLE, source="published")["event"] == "metadata_changed"
        assert conn.execute("SELECT COUNT(*) FROM document_snapshots").fetchone()[0] == 3
