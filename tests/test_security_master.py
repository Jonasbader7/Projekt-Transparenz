"""Wertpapierstamm ISIN → LEI aus N-PORT (D-056). Alle Daten fiktiv: ISIN ZZ…, LEI FIKT00…"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import sqlite3
import zipfile
from pathlib import Path

import pytest

from transparenz.database.session import init_db, make_engine
from transparenz.entities.identifiers import make_isin, make_lei
from transparenz.ingestion.gleif_level1 import LeiRecord
from transparenz.ingestion.gleif_lookup import load_parent_map
from transparenz.ingestion.sec_ncen_advisers import (
    AdviserRef,
    FundAdvisers,
    load_fund_advisers,
    read_archive,
)
from transparenz.services.provenance import ProvenanceError
from transparenz.services.security_master import (
    Context,
    adviser_keys,
    build_security_master,
    classify,
    independent_groups,
    lookup,
)

A, B, D, T, SL, ANN, MISSING = (make_lei(f"FIKT00SECMASTER{x:03d}") for x in range(1, 8))
ADV1, ADV2, ADV_PARENT, ADV3 = (make_lei(f"FIKT00ADVISER{x:05d}") for x in range(1, 5))
ISIN = make_isin("ZZSECM00001")


def rec(lei: str, entity: str = "ACTIVE", registration: str = "ISSUED",
        successor: str | None = None) -> LeiRecord:
    return LeiRecord(lei=lei, entity_status=entity, registration_status=registration,
                     country="ZZ", successor_lei=successor)


def ctx(**over) -> Context:
    records = {x: rec(x) for x in (A, B, T, SL)}
    records[D] = rec(D, "", "DUPLICATE", successor=A)
    records[ANN] = rec(ANN, "", "ANNULLED")
    base = dict(
        records=records,
        # S1, S2: verschiedene CIK und Berater; S3: andere CIK, aber Berater von S1
        fund_keys={"S1": frozenset({"cik:1", "lei:" + ADV1}),
                   "S2": frozenset({"cik:2", "lei:" + ADV2}),
                   "S3": frozenset({"cik:3", "lei:" + ADV1}),
                   "S4": frozenset({"cik:1"})},
        fund_cik={"S1": "1", "S2": "2", "S3": "3", "S4": "1"},
        series_trusts={SL: frozenset({T})},
        parents={})
    base.update(over)
    return Context(**base)


def test_two_independent_reporters_confirm():
    entry = classify(ISIN, {A: {"S1", "S2"}, None: {"S4"}}, ctx())
    assert entry.status == "confirmed" and entry.lei == A
    assert (entry.funds, entry.ciks, entry.independent) == (2, 2, 2)
    # S4 meldet die ISIN ohne LEI: zählt, widerspricht aber nicht.
    assert entry.funds_without_lei == 1


def test_same_adviser_with_different_cik_is_not_independent():
    entry = classify(ISIN, {A: {"S1", "S3"}}, ctx())
    assert entry.status == "single_reporter" and entry.independent == 1
    # Mit der Regel «jede CIK unabhängig» wäre die ISIN bestätigt.
    assert entry.ciks == 2 and entry.ciks_rule_confirmed


def test_adviser_group_uses_gleif_parent_and_registration_numbers():
    parents = {ADV1: {"ultimate-parent": ADV_PARENT}, ADV2: {"direct-parent": ADV_PARENT}}
    k1 = adviser_keys([AdviserRef(ADV1, None, None)], parents)
    k2 = adviser_keys([AdviserRef(ADV2, None, None)], parents)
    k3 = adviser_keys([AdviserRef(None, "801-12345", None)], parents)
    k4 = adviser_keys([AdviserRef(ADV3, "801-12345", "42")], parents)
    assert k1 & k2  # gleicher Konzern laut GLEIF
    assert k3 & k4  # gleiche SEC-Nummer
    keys = {"F1": k1, "F2": k2, "F3": k3, "F4": k4, "F5": {"cik:9"}}
    assert independent_groups(["F1", "F2", "F3", "F4", "F5"], keys) == 3


def test_any_other_lei_is_a_conflict_even_against_majority():
    entry = classify(ISIN, {A: {"S1", "S2", "S3"}, B: {"S4"}}, ctx())
    assert entry.status == "conflict" and entry.lei is None
    assert entry.conflict_kind == "other"
    assert [c.lei_reported for c in entry.claims] == [A, B]  # stärkste Meldung zuerst


def test_gleif_duplicate_is_replaced_by_successor():
    entry = classify(ISIN, {D: {"S1"}, A: {"S2"}}, ctx())
    assert entry.status == "confirmed" and entry.lei == A
    claim = next(c for c in entry.claims if c.lei_reported == D)
    assert claim.lei == A and claim.normalization == "gleif_duplicate"


def test_trust_lei_counts_for_the_series_of_that_trust():
    entry = classify(ISIN, {T: {"S1"}, SL: {"S2"}}, ctx())
    assert entry.status == "confirmed" and entry.lei == SL
    assert {c.normalization for c in entry.claims} == {"fund_trust_to_series", None}
    # Nur der Trust gemeldet: bleibt der Trust, keine Vermutung über die Serie.
    alone = classify(ISIN, {T: {"S1", "S2"}}, ctx())
    assert alone.lei == T and alone.claims[0].normalization is None


def test_unusable_gleif_records_are_never_confirmed():
    assert classify(ISIN, {ANN: {"S1", "S2"}}, ctx()).status == "lei_annulled"
    assert classify(ISIN, {MISSING: {"S1", "S2"}}, ctx()).status == "lei_not_in_gleif"
    unresolved = ctx()
    unresolved.records[D] = rec(D, "", "DUPLICATE")
    assert classify(ISIN, {D: {"S1", "S2"}}, unresolved).status == "lei_duplicate_unresolved"
    inactive = ctx()
    inactive.records[A] = rec(A, "INACTIVE", "RETIRED")
    assert classify(ISIN, {A: {"S1", "S2"}}, inactive).status == "confirmed"
    assert classify(ISIN, {None: {"S1"}}, ctx()).status == "no_lei_reported"


def test_conflict_kinds_are_described():
    merged = ctx()
    merged.records[B] = rec(B, "INACTIVE", "RETIRED", successor=A)
    assert classify(ISIN, {A: {"S1"}, B: {"S2"}}, merged).conflict_kind == "successor"
    family = ctx(parents={B: {"direct-parent": A}})
    assert classify(ISIN, {A: {"S1"}, B: {"S2"}}, family).conflict_kind == "parent_child"


# ------------------------------------------------------------------------ Quelldateien


def tsv(rows: list[dict[str, str]]) -> str:
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=list(rows[0]), delimiter="\t", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue()


def ncen_zip(adviser_rows: list[dict[str, str]]) -> bytes:
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as archive:
        archive.writestr("SUBMISSION.tsv", tsv([
            {"ACCESSION_NUMBER": "9999999999-26-000001", "CIK": "1"},
            {"ACCESSION_NUMBER": "9999999999-26-000002", "CIK": "2"}]))
        archive.writestr("FUND_REPORTED_INFO.tsv", tsv([
            {"FUND_ID": "F1", "ACCESSION_NUMBER": "9999999999-26-000001",
             "SERIES_ID": "S000000001"},
            {"FUND_ID": "F2", "ACCESSION_NUMBER": "9999999999-26-000002", "SERIES_ID": ""}]))
        archive.writestr("ADVISER.tsv", tsv(adviser_rows))
    return out.getvalue()


def adviser(fund: str, kind: str = "Advisor", lei: str = "", file_num: str = "",
            crd: str = "") -> dict[str, str]:
    return {"FUND_ID": fund, "ADVISER_TYPE": kind, "ADVISER_LEI": lei, "FILE_NUM": file_num,
            "CRD_NUM": crd}


def place_ncen(data_dir: Path, content: bytes, quarter: str = "2026q3",
               recorded_sha: str | None = None, downloaded: str = "2026-11-08T00:00:00") -> Path:
    folder = data_dir / "raw/external/sec_ncen/objects"
    folder.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(content).hexdigest()
    path = folder / f"{digest}.zip"
    path.write_bytes(content)
    (folder / f"{digest}.zip.metadata.json").write_text(json.dumps({
        "sha256": recorded_sha or digest, "source_key": "sec_ncen", "downloaded_at": downloaded,
        "url": f"https://www.sec.gov/files/dera/data/form-n-cen-data-sets/{quarter}_ncen.zip"}),
        encoding="utf-8")
    return path


def test_ncen_reads_only_advisers_with_identifiers(tmp_path):
    content = ncen_zip([
        adviser("F1", lei=ADV1),
        adviser("F1", kind="Subadvisor", lei=ADV2),
        adviser("F1", kind="Terminated Advisor", lei=ADV3),
        adviser("F2", lei="N/A", file_num="801-77"),
        adviser("F2", lei="FALSCH", file_num="kein"),
        adviser("F9", lei=ADV3)])
    result = FundAdvisers()
    path = tmp_path / "n.zip"
    path.write_bytes(content)
    read_archive(path, result)
    assert result.by_fund["S000000001"] == {AdviserRef(ADV1, None, None)}
    # Ohne Serie: Registrant als Fonds, wie in N-PORT («CIK» + CIK)
    assert result.by_fund["CIK0000000002"] == {AdviserRef(None, "801-77", None)}
    assert result.stats["rows"] == {"other_type": 2, "used": 2, "no_identifier": 1,
                                    "fund_unknown": 1}


def test_ncen_takes_latest_archive_per_quarter_and_checks_provenance(tmp_path):
    place_ncen(tmp_path, ncen_zip([adviser("F1", lei=ADV1)]), downloaded="2026-11-01")
    place_ncen(tmp_path, ncen_zip([adviser("F1", lei=ADV2)]), downloaded="2026-11-08")
    result = load_fund_advisers(tmp_path)
    assert result.stats["quarters"] == ["2026q3"]
    assert result.by_fund["S000000001"] == {AdviserRef(ADV2, None, None)}
    place_ncen(tmp_path, ncen_zip([adviser("F1", lei=ADV3)]), quarter="2026q2",
               recorded_sha="0" * 64)
    with pytest.raises(ProvenanceError):
        load_fund_advisers(tmp_path)


RR_COLUMNS = ("Relationship.StartNode.NodeID", "Relationship.StartNode.NodeIDType",
              "Relationship.EndNode.NodeID", "Relationship.EndNode.NodeIDType",
              "Relationship.RelationshipType", "Relationship.RelationshipStatus")


def rr_zip(rows: list[tuple[str, str, str, str]]) -> bytes:
    out = io.StringIO()
    writer = csv.writer(out, quoting=csv.QUOTE_ALL)
    writer.writerow(RR_COLUMNS)
    for child, parent, kind, status in rows:
        writer.writerow((child, "LEI", parent, "LEI", kind, status))
    data = io.BytesIO()
    with zipfile.ZipFile(data, "w") as archive:
        archive.writestr("fiktiv-rr.csv", out.getvalue())
    return data.getvalue()


def test_parent_map_keeps_active_relationships_only(tmp_path):
    path = tmp_path / "rr.zip"
    path.write_bytes(rr_zip([
        (ADV1, ADV_PARENT, "IS_ULTIMATELY_CONSOLIDATED_BY", "ACTIVE"),
        (ADV1, ADV_PARENT, "IS_DIRECTLY_CONSOLIDATED_BY", "ACTIVE"),
        (ADV2, ADV_PARENT, "IS_ULTIMATELY_CONSOLIDATED_BY", "INACTIVE"),
        (ADV3, ADV_PARENT, "IS_FUND-MANAGED_BY", "ACTIVE")]))
    assert load_parent_map(path, {ADV1, ADV2, ADV3}) == {
        ADV1: {"ultimate-parent": ADV_PARENT, "direct-parent": ADV_PARENT}}


# ------------------------------------------------------------------------ Gesamtaufbau

GLEIF_COLUMNS = ("LEI", "Entity.LegalAddress.Country", "Entity.EntityStatus",
                 "Entity.SuccessorEntity.1.SuccessorLEI", "Registration.LastUpdateDate",
                 "Registration.RegistrationStatus", "Registration.NextRenewalDate")


def place_gleif_files(data_dir: Path, records: list[dict[str, str]],
                      rr_rows: list[tuple[str, str, str, str]]) -> None:
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=list(GLEIF_COLUMNS), quoting=csv.QUOTE_ALL)
    writer.writeheader()
    writer.writerows([{c: r.get(c, "") for c in GLEIF_COLUMNS} for r in records])
    level1 = io.BytesIO()
    with zipfile.ZipFile(level1, "w") as archive:
        archive.writestr("fiktiv-lei2.csv", out.getvalue())
    for folder, name, content in (
            ("gleif_lei2_golden_copy", "gleif-goldencopy-lei2.csv.zip", level1.getvalue()),
            ("gleif_rr_golden_copy", "gleif-goldencopy-rr.csv.zip", rr_zip(rr_rows))):
        target = data_dir / "raw/external" / folder / "2026-11-15"
        target.mkdir(parents=True, exist_ok=True)
        (target / name).write_bytes(content)
        (target / "source.metadata.json").write_text(json.dumps({
            "source_key": folder, "license": "fiktiv", "size_bytes": len(content),
            "sha256": hashlib.sha256(content).hexdigest()}), encoding="utf-8")


def nport_db(path: Path) -> None:
    engine = make_engine(f"sqlite:///{path.as_posix()}")
    init_db(engine)
    engine.dispose()
    conn = sqlite3.connect(path)
    conn.execute("INSERT INTO dataset_versions (id, source_key, status, content_hash, "
                 "fetched_at, record_count, warning_count) VALUES (7, 'sec_nport', 'active', "
                 "'fiktiv', '2026-11-15 00:00:00', 0, 0)")
    subs = [  # (accession, Fonds, CIK, Serien-LEI, Registrant-LEI, Auswahl)
        ("9999999999-26-000001", "S000000001", "0000000001", None, T, "current"),
        ("9999999999-26-000002", "S000000002", "0000000002", SL, T, "current"),
        ("9999999999-26-000003", "S000000003", "0000000003", None, None, "current"),
        ("9999999999-26-000004", "S000000004", "0000000004", None, None, "superseded")]
    for accession, fund, cik, series_lei, registrant_lei, selection in subs:
        conn.execute("INSERT INTO nport_submissions (dataset_version_id, quarter, accession, "
                     "filing_date, sub_type, report_date, cik, series_lei, registrant_lei, "
                     "fund_key, selection) VALUES (7, '2026q3', ?, '2026-08-01', 'NPORT-P', "
                     "'2026-06-30', ?, ?, ?, ?, ?)",
                     (accession, cik, series_lei, registrant_lei, fund, selection))
    x1, x2, x3, x4 = (make_isin(f"ZZSECM0000{i}") for i in range(1, 5))
    holdings = [  # (accession, ISIN, Emittenten-LEI, Anlageart)
        ("9999999999-26-000001", x1, A, "EC"), ("9999999999-26-000002", x1, A, "EC"),
        ("9999999999-26-000003", x1, None, "EC"),
        ("9999999999-26-000001", x2, A, "DBT"), ("9999999999-26-000002", x2, B, "DBT"),
        ("9999999999-26-000001", x3, T, "EC"), ("9999999999-26-000002", x3, SL, "EC"),
        ("9999999999-26-000001", x4, B, "DE"), ("9999999999-26-000002", x4, B, "DE"),
        # ersetzte Meldung: zählt nicht (sonst wäre x2 ohne Widerspruch nicht prüfbar)
        ("9999999999-26-000004", x1, B, "EC")]
    for i, (accession, isin, lei, cat) in enumerate(holdings):
        conn.execute("INSERT INTO nport_holdings (dataset_version_id, quarter, accession, "
                     "holding_id, issuer_lei, issuer_lei_status, asset_cat, isin, isin_status) "
                     "VALUES (7, '2026q3', ?, ?, ?, ?, ?, ?, 'valid')",
                     (accession, i, lei, "valid" if lei else "not_applicable", cat, isin))
    conn.commit()
    conn.close()


def test_build_end_to_end_with_provenance_and_lookup(tmp_path):
    data = tmp_path / "daten"
    db = data / "processed/nport.sqlite"
    db.parent.mkdir(parents=True)
    nport_db(db)
    place_gleif_files(data, [
        {"LEI": x, "Entity.EntityStatus": "ACTIVE", "Registration.RegistrationStatus": "ISSUED",
         "Entity.LegalAddress.Country": "ZZ"} for x in (A, B, T, SL, ADV1, ADV2)],
        [(ADV1, ADV_PARENT, "IS_ULTIMATELY_CONSOLIDATED_BY", "ACTIVE")])
    funds = (io.BytesIO())
    with zipfile.ZipFile(funds, "w") as archive:
        archive.writestr("SUBMISSION.tsv", tsv([
            {"ACCESSION_NUMBER": f"9999999999-26-00000{i}", "CIK": str(i)} for i in (1, 2)]))
        archive.writestr("FUND_REPORTED_INFO.tsv", tsv([
            {"FUND_ID": f"F{i}", "ACCESSION_NUMBER": f"9999999999-26-00000{i}",
             "SERIES_ID": f"S00000000{i}"} for i in (1, 2)]))
        archive.writestr("ADVISER.tsv", tsv([adviser("F1", lei=ADV1), adviser("F2", lei=ADV2)]))
    place_ncen(data, funds.getvalue())
    out = data / "processed/security_master.sqlite"
    report = build_security_master(db, data, out, data / "processed/security_master/q.json")

    x1, x2, x3, x4 = (make_isin(f"ZZSECM0000{i}") for i in range(1, 5))
    assert lookup(out, x1)["status"] == "confirmed"
    assert lookup(out, x1)["funds_without_lei"] == 1
    assert lookup(out, x2)["status"] == "conflict"
    third = lookup(out, x3)
    assert third["status"] == "confirmed" and third["lei"] == SL
    assert lookup(out, x4) is None  # Derivat: nicht im Wertpapierstamm
    assert report["isins"]["by_status"]["confirmed"]["count"] == 2
    assert report["holdings"]["derivatives_excluded"] == 2
    assert report["input_stats"]["funds_with_ncen_adviser"]["count"] == 2
    assert report["inputs"]["gleif_level1"]["status"] == "verified"
    assert report["inputs"]["sec_ncen"][0]["status"] == "verified"
    assert json.loads((data / "processed/security_master/q.json").read_bytes()) == report
    # Die N-PORT-Datenbank wird nur lesend geöffnet: unverändert.
    conn = sqlite3.connect(db)
    assert conn.execute("SELECT COUNT(*) FROM nport_holdings").fetchone()[0] == 10
    conn.close()


# ------------------------------------------------------------------------ Gegenprüfung


def test_pilot_methods_are_measured_against_confirmed_reference(tmp_path):
    from transparenz.services.entity_matching import DEVELOPMENT_FUNDS
    from transparenz.services.reference_check import compare_with_reference, pilot_proposals
    from transparenz.services.security_master import _SCHEMA_SQL

    i1, i2, i3, i4 = (make_isin(f"ZZPILOT000{i}") for i in range(1, 5))
    db = tmp_path / "sm.sqlite"
    conn = sqlite3.connect(db)
    conn.executescript(_SCHEMA_SQL)
    conn.executemany("INSERT INTO securities (isin, lei, status, funds, ciks, independent, "
                     "funds_without_lei, holdings, gleif_country) VALUES (?, ?, ?, 2, 2, 2, 0, "
                     "2, ?)", [(i1, A, "confirmed", "SE"), (i2, B, "confirmed", "US"),
                               (i3, None, "conflict", None), (i4, A, "confirmed", "JP")])
    conn.execute("INSERT INTO build_info VALUES ('rule_version', '\"fiktiv\"')")
    conn.commit()
    conn.close()

    def position(isin: str, name_lei: str | None, country: str = "SE") -> dict:
        return {"isin": isin, "isin_valid": True, "issuer_country": country, "auto_match": {
            "name": {"lei": name_lei, "status": "accepted" if name_lei else "no_match"}}}

    pilot = tmp_path / "pilot"
    pilot.mkdir()
    test_fund = {"fund": {"fund_name": "Fiktiv Testfonds"}, "positions": [
        position(i1, A), position(i2, A, "US"), position(i3, B), position(i4, None)]}
    dev_fund = {"fund": {"fund_name": sorted(DEVELOPMENT_FUNDS)[0]},
                "positions": [position(i4, A)]}
    (pilot / "test.json").write_text(json.dumps(test_fund), encoding="utf-8")
    (pilot / "test_wikidata_isin.json").write_text(json.dumps({"rows": [
        {"isin": i1, "lei": A}, {"isin": i2, "lei": A}, {"isin": i2, "lei": B}]}),
        encoding="utf-8")
    (pilot / "dev.json").write_text(json.dumps(dev_fund), encoding="utf-8")

    result = compare_with_reference(db, pilot_proposals(pilot))
    name = result["methods"]["name"]["cases"]
    # i1 richtig, i2 falsch; i3 ohne Referenz (Widerspruch); i4 im Entwicklungsfonds
    assert (name["all"]["reference_cases"], name["all"]["answered"],
            name["all"]["correct"]) == (2, 2, 1)
    assert name["europe"]["correct"] == 1 and name["north_america"]["wrong"] == 1
    wikidata = result["methods"]["wikidata"]["cases"]["all"]
    # Wikidata ist nie angepasst worden: i4 zählt; i2 mit zwei LEI bleibt unbeantwortet.
    assert (wikidata["reference_cases"], wikidata["answered"], wikidata["correct"]) == (3, 1, 1)
    assert result["reference"]["status_of_pilot_isins"] == {"confirmed": 3, "conflict": 1}
    assert "released" not in name["all"] and name["all"]["meets_release_rule"] is False


def test_confirmed_reference_returns_only_confirmed_isins(tmp_path):
    from transparenz.services.security_master import _SCHEMA_SQL, confirmed_reference

    i1, i2 = make_isin("ZZREF000001"), make_isin("ZZREF000002")
    db = tmp_path / "sm.sqlite"
    conn = sqlite3.connect(db)
    conn.executescript(_SCHEMA_SQL)
    conn.executemany("INSERT INTO securities (isin, lei, status, funds, ciks, independent, "
                     "funds_without_lei, holdings) VALUES (?, ?, ?, 1, 1, 1, 0, 1)",
                     [(i1, A, "confirmed"), (i2, B, "single_reporter")])
    conn.execute("INSERT INTO build_info VALUES ('rule_version', '\"fiktiv\"')")
    conn.commit()
    conn.close()
    found, info = confirmed_reference(db, [i1, i2, make_isin("ZZREF000003")])
    assert found == {i1: A} and info["rule_version"] == "fiktiv"


def test_confirmed_details_add_support_and_gleif_status(tmp_path):
    from transparenz.services.security_master import _SCHEMA_SQL, confirmed_details

    i1, i2 = make_isin("ZZREF000001"), make_isin("ZZREF000002")
    db = tmp_path / "sm.sqlite"
    conn = sqlite3.connect(db)
    conn.executescript(_SCHEMA_SQL)
    conn.executemany("INSERT INTO securities (isin, lei, status, funds, ciks, independent, "
                     "funds_without_lei, holdings, gleif_entity_status) "
                     "VALUES (?, ?, ?, 7, 4, 3, 0, 9, ?)",
                     [(i1, A, "confirmed", "INACTIVE"), (i2, B, "conflict", "ACTIVE")])
    conn.execute("INSERT INTO build_info VALUES ('rule_version', '\"fiktiv\"')")
    conn.commit()
    conn.close()
    found, info, details = confirmed_details(db, [i1.lower(), i2])
    assert found == {i1: A} and info["rule_version"] == "fiktiv"
    # Inaktiver Rechtsträger bleibt bestätigt; der Status steht daneben.
    assert details == {i1: {"independent": 3, "funds": 7, "gleif_entity_status": "INACTIVE",
                            "gleif_registration_status": None, "gleif_country": None}}
