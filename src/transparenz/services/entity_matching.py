"""Automatische Zuordnung Wertpapier → Rechtsträger ohne Einzelfallfreigabe (rein funktional).

Drei Verfahren, jedes mit eigener, messbarer Regel (D-046):

* **isin_wikidata** – exakter ISIN-Abgleich in Wikidata, genau ein Eintrag mit genau einem
  LEI, LEI bei GLEIF vorhanden, Name widerspricht nicht (bestehender Weg, D-039).
* **register** – Wikidata nennt für das Unternehmen eine Registernummer (z. B. OpenCorporates
  «us_de/2207172», australische ACN/ABN, japanische Unternehmensnummer), und GLEIF führt genau
  einen aktiven Rechtsträger mit dieser Nummer in derselben Rechtsordnung. Kennung, kein Name.
* **gleif_name_country** – GLEIF-Namenssuche. Angenommen wird nur ein Kandidat, dessen Name
  nach Normalisierung **gleich** (nicht ähnlich) dem Positionsnamen ist, der im Sitzland laut
  ISIN oder Fondsmeldung registriert ist, aktiv ist und kein Fonds und keine Zweigniederlassung
  ist. Bleiben mehrere, entscheidet nur die GLEIF-Konzernbeziehung (die oberste Gesellschaft
  der Gleichnamigen), sonst bleibt der Fall offen. Dieses Verfahren arbeitet automatisch nur,
  wenn seine an unabhängigen Referenzfällen gemessene Präzision die Freigabeschwelle erreicht.

Der Name ist hier kein Schlüssel: Er erzeugt Kandidaten, die erst durch Land, Status,
Eindeutigkeit und die gemessene Fehlerquote des Verfahrens tragfähig werden.
"""
from __future__ import annotations

import math
import re
import unicodedata
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

# Version der Regeln. Fonds, an deren Fehlern die Regeln dieser Version angepasst wurden, sind
# Entwicklungsdaten: Ihre Fälle werden gezeigt, zählen aber nicht für die Freigabe, ebenso wenig
# dieselben ISINs in anderen Fonds. Bei jeder Regeländerung: Version erhöhen, Fonds ergänzen.
RULE_VERSION = "2026-11-14.3"
DEVELOPMENT_FUNDS = frozenset({"SEB Global Sustainable Companies Fund",
                               "Handelsbanken Global High Dividend Low Volatility Criteria"})
# Freigabe eines Verfahrens: mindestens so viele unabhängige Referenzfälle mit Ergebnis und eine
# untere 95-%-Vertrauensgrenze der Präzision (Clopper-Pearson, einseitig) von mindestens …
RELEASE_MIN_CASES = 100
RELEASE_MIN_PRECISION_LOWER_BOUND = 0.97
CONFIDENCE = 0.95
# Freigabe je Region (D-046, D-058). Massgebend ist das Sitzland, mit dem die Namenssuche
# arbeitet: das vom Fonds gemeldete Emittentenland, sonst das Länderkürzel der ISIN.
_REGION_EUROPE = frozenset({
    "AT", "BE", "BG", "CH", "CY", "CZ", "DE", "DK", "EE", "ES", "FI", "FO", "FR", "GB", "GG",
    "GI", "GR", "HR", "HU", "IE", "IM", "IS", "IT", "JE", "LI", "LT", "LU", "LV", "MC", "MT",
    "NL", "NO", "PL", "PT", "RO", "SE", "SI", "SK"})
_REGION_ASIA_PACIFIC = frozenset({"AU", "CN", "HK", "ID", "IN", "JP", "KR", "MO", "MY", "NZ",
                                  "PH", "SG", "TH", "TW", "VN"})
_REGION_NORTH_AMERICA = frozenset({"US", "CA"})
REGIONS = ("north_america", "europe", "asia_pacific", "other", "unknown")


def region_of(country: str | None) -> str:
    """Region eines Landes (ISO 3166 Alpha-2); unbekannt, wenn kein Land vorliegt."""
    country = (country or "").upper()
    if country in _REGION_NORTH_AMERICA:
        return "north_america"
    if country in _REGION_EUROPE:
        return "europe"
    if country in _REGION_ASIA_PACIFIC:
        return "asia_pacific"
    return "other" if len(country) == 2 and country.isalpha() else "unknown"


def position_region(issuer_country: str | None, isin: str | None) -> str:
    """Region einer Position: gemeldetes Emittentenland, sonst Länderkürzel der ISIN."""
    return region_of(issuer_country or (isin or "")[:2] or None)

_LEGAL_FORM_WORDS = {"ag", "sa", "nv", "bv", "ab", "as", "asa", "oyj", "oy", "plc", "inc", "ltd",
                     "limited", "llc", "gmbh", "spa", "sl", "srl", "corp", "corporation",
                     "company", "co", "the", "and", "lda", "unipessoal", "sp", "z", "o",
                     "se", "kabushiki", "kaisha", "kk", "aktiengesellschaft", "oo", "of", "de",
                     "incorporated", "tbk", "bhd", "berhad", "pte", "pty", "sab", "cv", "kgaa",
                     "publ", "a/s", "aps", "nyrt", "sca", "lp", "reit", "public",
                     "societa", "per", "azioni", "responsabilita", "limitata", "sociedad",
                     "anonima", "aktiebolag", "aksjeselskap", "naamloze", "vennootschap",
                     "osakeyhtio", "julkinen", "spolka", "akcyjna", "sarl", "sas", "ltda"}
# Allerweltswörter würden sonst zufällige «Übereinstimmungen» erzeugen.
_GENERIC_WORDS = {"group", "groupe", "grupo", "holding", "holdings", "international", "intl",
                  "industries", "industry", "technologies", "technology", "global", "systems",
                  "services", "energy", "electric", "financial", "reg", "registered", "shares",
                  "stamm", "class", "cl", "adr", "bank", "motor", "motors"}
# Zusätze in Positionsnamen, die die Aktiengattung beschreiben, nicht das Unternehmen.
_SHARE_CLASS_WORDS = {"a", "b", "c", "d", "h", "r", "ser", "series", "class", "cl", "reg",
                      "registered", "shs", "share", "shares", "ord", "ordinary", "com", "common",
                      "stock", "stamm", "pref", "npv", "adr", "ads", "sdr", "units", "unit",
                      "new", "gbp", "usd", "eur", "sek", "chf", "dkk", "nok", "jpy", "hkd",
                      "aud", "cad", "inh", "vz", "akt", "aktie", "br", "bearer", "sp", "spon"}
_TRANSLATE = str.maketrans({"ø": "o", "Ø": "o", "æ": "ae", "Æ": "ae", "ß": "ss", "œ": "oe",
                            "ł": "l", "đ": "d", "'": "", "’": "", "`": "", "&": " and "})
_PAREN_RE = re.compile(r"\([^)]*\)")
_ABBREVIATION_RE = re.compile(r"in forma abbreviata|abbreviated|abrev\w*", re.I)


def normalise(value: str | None) -> str:
    text = unicodedata.normalize("NFKD", (value or "").translate(_TRANSLATE))
    text = "".join(ch for ch in text if not unicodedata.combining(ch)).lower()
    return "".join(ch if ch.isalnum() else " " for ch in text)


def name_words(value: str | None) -> set[str]:
    return {word for word in normalise(value).split()
            if len(word) > 1 and word not in _LEGAL_FORM_WORDS and word not in _GENERIC_WORDS}


def compact(value: str | None) -> str:
    return "".join(w for w in normalise(value).split() if w not in _LEGAL_FORM_WORDS)


def names_agree(left: list[str | None], right: list[str | None]) -> bool | None:
    """Sichtprüfung zweier Namenslisten. ``None``: nichts zu vergleichen.

    Übereinstimmung heisst: ein gemeinsames, nicht allgemeines Wort oder dieselbe Zeichenfolge
    ohne Leerzeichen («UCB» = «U C B», «Cap Gemini» ⊂ «Capgemini»). Das bestätigt keine Identität,
    es deckt nur offensichtliche Widersprüche auf.
    """
    left_names = [n for n in left if n]
    right_names = [n for n in right if n]
    if not left_names or not right_names:
        return None
    for a in left_names:
        words_a, compact_a = name_words(a), compact(a)
        for b in right_names:
            if words_a & name_words(b):
                return True
            compact_b = compact(b)
            if compact_a and compact_b and (
                    compact_a == compact_b or (min(len(compact_a), len(compact_b)) >= 4
                                               and (compact_a in compact_b
                                                    or compact_b in compact_a))):
                return True
    return False


def security_query(name: str | None) -> str:
    """Suchtext aus einem Positionsnamen: ohne Klammern und ohne Gattungszusätze."""
    words = [w for w in normalise(_PAREN_RE.sub(" ", name or "")).split()
             if w not in _SHARE_CLASS_WORDS and w not in _LEGAL_FORM_WORDS]
    return " ".join(words)


_STRUCTURE_WORDS = {"group", "groupe", "grupo", "gruppe", "holding", "holdings"}


def name_key(name: str | None, *, security: bool = False) -> str:
    """Vergleichsschlüssel für Namensgleichheit: ohne Rechtsform, ohne «Group»/«Holding» und
    (bei Positionsnamen) ohne Gattungszusätze, ohne Leerzeichen. Branchenwörter («Energy»,
    «Bank») bleiben: «Siemens» und «Siemens Energy» sind verschiedene Schlüssel."""
    text = _PAREN_RE.sub(" ", name or "") if security else (name or "")
    # «S.p.A.» = «SpA», «A/S» = «AS», «Amazon.com» = «Amazoncom»
    text = text.replace(".", "").replace("/", "")
    drop = _LEGAL_FORM_WORDS | _STRUCTURE_WORDS | (_SHARE_CLASS_WORDS if security else set())
    return "".join(w for w in normalise(text).split() if w not in drop)


@dataclass(frozen=True)
class GleifCandidate:
    lei: str
    legal_name: str
    other_names: tuple[str, ...] = ()
    legal_country: str | None = None
    hq_country: str | None = None
    entity_status: str | None = None
    registration_status: str | None = None
    category: str | None = None
    registered_as: str | None = None
    jurisdiction: str | None = None

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> GleifCandidate:
        attributes = record.get("attributes") or {}
        entity = attributes.get("entity") or {}
        names = [*(entity.get("otherNames") or []), *(entity.get("transliteratedOtherNames")
                                                      or [])]
        return cls(
            lei=str(record.get("id") or attributes.get("lei") or "").upper(),
            legal_name=((entity.get("legalName") or {}).get("name") or ""),
            other_names=tuple(n["name"] for n in names if n.get("name")),
            legal_country=(entity.get("legalAddress") or {}).get("country"),
            hq_country=(entity.get("headquartersAddress") or {}).get("country"),
            entity_status=entity.get("status"),
            registration_status=(attributes.get("registration") or {}).get("status"),
            category=entity.get("category"),
            registered_as=entity.get("registeredAs"),
            jurisdiction=entity.get("jurisdiction"))

    def to_dict(self) -> dict[str, Any]:
        return {"lei": self.lei, "legal_name": self.legal_name,
                "other_names": list(self.other_names), "legal_country": self.legal_country,
                "hq_country": self.hq_country, "entity_status": self.entity_status,
                "registration_status": self.registration_status, "category": self.category,
                "registered_as": self.registered_as, "jurisdiction": self.jurisdiction}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> GleifCandidate:
        return cls(**{**data, "other_names": tuple(data.get("other_names") or ())})


@dataclass
class MatchResult:
    method: str
    lei: str | None
    status: str  # accepted, ambiguous, no_candidate, too_many, not_searched
    reason: str
    candidates: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"method": self.method, "lei": self.lei, "status": self.status,
                "reason": self.reason, "candidates": self.candidates}


def allowed_countries(isin: str | None, issuer_country: str | None) -> set[str]:
    """Sitzländer, die zur Position passen: Länderpräfix der ISIN und Emittentenland."""
    out = {c for c in (issuer_country,) if c and len(c) == 2}
    prefix = (isin or "")[:2].upper()
    if prefix.isalpha() and prefix not in {"XS", "XC", "EU", "QS", "ZZ"}:
        out.add(prefix)
    return out


def _eligible(c: GleifCandidate, countries: set[str]) -> bool:
    return (c.entity_status == "ACTIVE"
            and c.registration_status in ("ISSUED", "LAPSED", "PENDING_TRANSFER",
                                          "PENDING_ARCHIVAL")
            and (c.category or "GENERAL") not in ("FUND", "BRANCH", "SOLE_PROPRIETOR")
            and bool({c.legal_country, c.hq_country} & countries))


def match_by_name(names: Iterable[str | None], countries: set[str],
                  candidates: Iterable[GleifCandidate], *, truncated: bool = False,
                  parent_of: Mapping[str, set[str]] | None = None) -> MatchResult:
    """Regel «gleif_name_country» (siehe Modulkopf). ``parent_of``: LEI → LEIs ihrer Mütter."""
    method = "gleif_name_country"
    if truncated:
        return MatchResult(method, None, "too_many",
                           "Die Namenssuche liefert zu viele Treffer, um eindeutig zu sein.")
    keys = {name_key(n, security=True) for n in names if n}
    keys = {k for k in keys if len(k) >= 3}
    if not keys:
        return MatchResult(method, None, "no_candidate", "Kein verwertbarer Name.")
    if not countries:
        return MatchResult(method, None, "no_candidate", "Kein Sitzland für die Prüfung bekannt.")
    hits = []
    for candidate in candidates:
        variants = [candidate.legal_name, *candidate.other_names]
        # Kurzform in Klammern («… (in forma abbreviata "Terna S.p.A.")») ist ein eigener Name.
        variants += [inner for name in variants for inner in _PAREN_RE.findall(name or "")]
        variants += [_ABBREVIATION_RE.sub("", name) for name in variants]
        own = {name_key(n.strip("() ")) for n in variants if n}
        if keys & own and _eligible(candidate, countries):
            hits.append(candidate)
    leis = sorted({c.lei for c in hits})
    if not leis:
        return MatchResult(method, None, "no_candidate",
                           "Kein aktiver, gleichnamiger Rechtsträger im passenden Sitzland.")
    if len(leis) == 1:
        return MatchResult(method, leis[0], "accepted",
                           "Genau ein aktiver, gleichnamiger Rechtsträger im Sitzland.", leis)
    parents = parent_of or {}
    tops = [lei for lei in leis if not (parents.get(lei, set()) & set(leis))]
    if len(tops) == 1 and all(tops[0] in _ancestors(lei, parents) for lei in leis
                              if lei != tops[0]):
        return MatchResult(method, tops[0], "accepted",
                           f"{len(leis)} gleichnamige Rechtsträger; laut GLEIF-Konzernbeziehung "
                           "ist dieser die Mutter der übrigen.", leis)
    return MatchResult(method, None, "ambiguous",
                       f"{len(leis)} gleichnamige Rechtsträger, keiner eindeutig.", leis)


def _ancestors(lei: str, parents: Mapping[str, set[str]]) -> set[str]:
    seen: set[str] = set()
    stack = [lei]
    while stack:
        for parent in parents.get(stack.pop(), set()):
            if parent not in seen:
                seen.add(parent)
                stack.append(parent)
    return seen


# OpenCorporates-Rechtsordnung → GLEIF-Rechtsordnung («us_de» → «US-DE», «gb» → «GB»).
def opencorporates_jurisdiction(code: str) -> str:
    country, _, region = code.partition("_")
    return f"{country.upper()}-{region.upper()}" if region else country.upper()


REGISTER_PROPERTIES = {"P1320": "OpenCorporates", "P3549": "Australian Company Number",
                       "P3548": "Australian Business Number",
                       "P3225": "Corporate Number (Japan)",
                       "P5687": "New Zealand Business Number"}
_REGISTER_COUNTRY = {"P3549": "AU", "P3548": "AU", "P3225": "JP", "P5687": "NZ"}


def register_queries(claims: Mapping[str, Iterable[str]]) -> list[tuple[str, str, str]]:
    """(Eigenschaft, Registernummer, erwartete Rechtsordnung) aus Wikidata-Kennungen."""
    out = []
    for prop, values in claims.items():
        for value in values:
            value = (value or "").strip()
            if not value:
                continue
            if prop == "P1320":
                jurisdiction, _, number = value.partition("/")
                if number:
                    out.append((prop, number, opencorporates_jurisdiction(jurisdiction)))
                    out.extend(_register_spellings(number, opencorporates_jurisdiction(
                        jurisdiction)))
            elif prop in _REGISTER_COUNTRY:
                number = re.sub(r"\s", "", value)
                out.append((prop, number, _REGISTER_COUNTRY[prop]))
                if prop == "P3548" and len(number) == 11 and number.isdigit():
                    # Die ABN enthält die ACN als letzte neun Ziffern; GLEIF führt meist die ACN.
                    out.append(("P3549", number[2:], "AU"))
                    out.extend(_register_spellings(number[2:], "AU"))
                else:
                    out.extend(_register_spellings(number, _REGISTER_COUNTRY[prop]))
    return list(dict.fromkeys(out))


def _register_spellings(number: str, jurisdiction: str) -> list[tuple[str, str, str]]:
    """Schreibweisen derselben Nummer, wie GLEIF sie führt (die Suche dort ist exakt).

    Australien: ACN in Dreiergruppen («141 075 201»). Japan: Die 13-stellige
    Unternehmensnummer ist eine Prüfziffer plus die 12-stellige Handelsregisternummer, die
    GLEIF als «1200-01-059662» führt.
    """
    digits = re.sub(r"\D", "", number)
    if jurisdiction == "AU" and len(digits) == 9:
        return [("P3549", f"{digits[:3]} {digits[3:6]} {digits[6:]}", "AU")]
    if jurisdiction == "JP" and len(digits) == 13:
        core = digits[1:]
        return [("P3225", f"{core[:4]}-{core[4:6]}-{core[6:]}", "JP")]
    return []


def _digits(value: str | None) -> str:
    return re.sub(r"[^0-9A-Za-z]", "", value or "").lstrip("0").upper()


def match_by_register(queries: list[tuple[str, str, str]],
                      found: Mapping[str, Iterable[GleifCandidate]],
                      countries: set[str] | None = None) -> MatchResult:
    """Regel «register»: genau ein aktiver Rechtsträger mit dieser Nummer in dieser
    Rechtsordnung. Mit ``countries`` muss er zudem im Sitzland der Position registriert sein;
    das fängt falsche Nummern in der Quelle ab (z. B. die Nummer einer ausländischen Tochter)."""
    method = "register"
    leis: set[str] = set()
    for _prop, number, jurisdiction in queries:
        for c in found.get(number, []):
            same_place = (c.jurisdiction or "").upper() == jurisdiction or (
                len(jurisdiction) == 2 and (c.jurisdiction or "")[:2].upper() == jurisdiction)
            same_number = _digits(c.registered_as) == _digits(number)
            # Massgebend ist das Land der Registerbehörde, nicht der Hauptsitz.
            register_country = (c.jurisdiction or c.legal_country or "")[:2].upper()
            in_country = not countries or register_country in countries
            if same_place and same_number and in_country and c.entity_status == "ACTIVE":
                leis.add(c.lei)
    if not queries:
        return MatchResult(method, None, "not_searched", "Keine Registernummer in Wikidata.")
    if len(leis) == 1:
        lei = next(iter(leis))
        return MatchResult(method, lei, "accepted",
                           "Registernummer laut Wikidata = Registernummer laut GLEIF, gleiche "
                           "Rechtsordnung.", [lei])
    if not leis:
        return MatchResult(method, None, "no_candidate",
                           "GLEIF führt keinen aktiven Rechtsträger mit dieser Registernummer.")
    return MatchResult(method, None, "ambiguous", "Mehrere Rechtsträger mit dieser Nummer.",
                       sorted(leis))


# ------------------------------------------------------------------- Messung und Freigabe
def _binom_cdf(k: int, n: int, p: float) -> float:
    if p <= 0:
        return 1.0
    if p >= 1:
        return 0.0 if k < n else 1.0
    total = 0.0
    log_p, log_q = math.log(p), math.log1p(-p)
    for i in range(0, k + 1):
        total += math.exp(math.lgamma(n + 1) - math.lgamma(i + 1) - math.lgamma(n - i + 1)
                          + i * log_p + (n - i) * log_q)
    return min(total, 1.0)


def precision_lower_bound(correct: int, total: int, confidence: float = CONFIDENCE) -> float:
    """Einseitige untere Clopper-Pearson-Grenze für den Anteil richtiger Ergebnisse."""
    if total == 0:
        return 0.0
    if correct == 0:
        return 0.0
    alpha = 1 - confidence
    low, high = 0.0, correct / total
    for _ in range(80):  # Bisektion: P(X ≥ correct | p) = alpha
        mid = (low + high) / 2
        tail = 1 - _binom_cdf(correct - 1, total, mid)
        if tail < alpha:
            low = mid
        else:
            high = mid
    return round(low, 4)


def evaluate(cases: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Präzision und Abdeckung eines Verfahrens an Referenzfällen.

    Je Fall: ``reference_lei`` (die als richtig geltende Zuordnung) und ``predicted_lei``
    (Ergebnis des Verfahrens oder ``None``). Abdeckung = Anteil mit Ergebnis; Präzision =
    Anteil richtiger Ergebnisse unter denen mit Ergebnis. Beides wird getrennt ausgewiesen.
    """
    cases = list(cases)
    answered = [c for c in cases if c.get("predicted_lei")]
    correct = [c for c in answered if c["predicted_lei"] == c["reference_lei"]]
    lower = precision_lower_bound(len(correct), len(answered))
    return {
        "reference_cases": len(cases), "answered": len(answered), "correct": len(correct),
        "wrong": len(answered) - len(correct),
        "coverage": round(len(answered) / len(cases), 4) if cases else None,
        "precision": round(len(correct) / len(answered), 4) if answered else None,
        "precision_lower_bound_95": lower,
        "released": len(answered) >= RELEASE_MIN_CASES
        and lower >= RELEASE_MIN_PRECISION_LOWER_BOUND,
        "release_rule": f"mindestens {RELEASE_MIN_CASES} unabhängige Referenzfälle mit Ergebnis "
                        "und untere "
                        f"95-%-Grenze der Präzision ≥ {RELEASE_MIN_PRECISION_LOWER_BOUND:.0%}",
        "wrong_cases": [dict(c) for c in answered if c["predicted_lei"] != c["reference_lei"]],
    }
