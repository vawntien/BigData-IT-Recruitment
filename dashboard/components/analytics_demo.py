"""Small in-memory SYNTHETIC fixtures. No file readers or real-query permission.

Counts deliberately differ from received snapshots. Nulls remain actual None;
denominators belong to each complete scope, never the displayed Top N.
"""
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
import math


@dataclass(frozen=True)
class Bucket:
    key: str | bool | None
    count: int
    share_all: float | None
    share_known: float | None


@dataclass(frozen=True)
class Partition:
    name: str
    population: int
    known: int
    missing: int
    rows: tuple[Bucket, ...]
    kind: str = "category"


@dataclass(frozen=True)
class Skill:
    code: str
    name: str
    count: int
    share: float | None


@dataclass(frozen=True)
class SkillScope:
    dimension: str
    bucket: str | None
    population: int
    zero_hit: int
    rows: tuple[Skill, ...]


@dataclass(frozen=True)
class Demo:
    query: str
    partitions: tuple[Partition, ...] = ()
    skills: tuple[SkillScope, ...] = ()
    origin: str = "SYNTHETIC_SAMPLE"


def ratio(n, d):
    return n / d if d else None


def _partition(name, values, *, population=100, kind="category"):
    missing = population - sum(n for _, n in values) if kind in ("month", "week") else sum(n for k, n in values if k is None)
    known = population - missing
    return Partition(name, population, known, missing, tuple(
        Bucket(k, n, ratio(n, population), ratio(n, known) if k is not None else None)
        for k, n in values), kind)


def build_demo(query):
    """Return a fresh immutable fixture only when explicitly called by demo UI."""
    if query == "Q02":
        return Demo(query, (_partition("experience", (("Entry", 35), ("Mid-Senior", 30),
                    ("Associate", 15), ("Unknown", 5), (None, 15))),))
    if query == "Q03":
        return Demo(query, (_partition("location", (("Hanoi", 35), ("Ha Noi", 25),
                    ("Remote", 20), ("Unknown", 10), (None, 10))),))
    if query == "Q04":
        return Demo(query, (
            _partition("work_type", (("Full-time", 60), ("Contract", 20), ("Part-time", 10), (None, 10))),
            _partition("remote", ((True, 30), (False, 10), (None, 60)), kind="remote")))
    if query == "Q08":
        parts = []
        for basis, counts in (("original_listed_time", (20, 20, 50)), ("listed_time", (25, 15, 40))):
            for kind, periods in (("month", ("2026-01", "2026-02", "2026-04")),
                                  ("week", ("2026-01-05", "2026-02-02", "2026-04-06"))):
                parts.append(_partition(basis + ":" + kind, tuple(zip(periods, counts)), kind=kind))
        return Demo(query, tuple(parts))
    if query == "Q06":
        # Twelve invented jobs, four zero-hit; no real source rows or text.
        job_skills = (("PYTHON", "SQL"), ("PYTHON", "DOCKER"), (), ("PYTHON",),
                      ("SQL", "DOCKER"), (), ("PYTHON", "SQL"), (),
                      ("PYTHON", "SQL"), ("PYTHON", "DOCKER"), ("SQL",), ())
        groups = ("Software",) * 7 + ("Data",) * 5
        experience = (None,) * 3 + ("Entry",) * 3 + ("Senior", "Entry") + ("Senior",) * 4
        jobs = tuple(zip(groups, experience, job_skills))
        scopes = []
        labels = {"PYTHON": "Python", "SQL": "SQL", "DOCKER": "Docker"}
        for dimension, keys in (("global", (None,)), ("group", ("Software", "Data")),
                                ("experience", (None, "Entry", "Senior"))):
            for key in keys:
                selected = [j for j in jobs if dimension == "global" or j[0 if dimension == "group" else 1] == key]
                counts = Counter(skill for _, _, skills in selected for skill in set(skills))
                scopes.append(SkillScope(dimension, key, len(selected), sum(not j[2] for j in selected),
                    tuple(Skill("DEMO_" + code, labels[code], n, ratio(n, len(selected))) for code, n in sorted(counts.items()))))
        return Demo(query, skills=tuple(scopes))
    raise ValueError("UNSUPPORTED_DEMO")


def _require(condition):
    if not condition:
        raise ValueError("INVALID_SYNTHETIC_DATA")


def _count(value):
    _require(type(value) is int and value >= 0)


def _rate(value, n, d):
    _require(value is None if not d else type(value) is float and math.isfinite(value)
             and 0 <= value <= 1 and math.isclose(value, n / d, rel_tol=1e-12, abs_tol=1e-12))


def validate_demo(demo, query):
    """Guard the complete fixture before any KPI/table/chart crosses into UI."""
    _require(type(demo) is Demo and demo.origin == "SYNTHETIC_SAMPLE" and demo.query == query)
    expected = {"Q02": {"experience"}, "Q03": {"location"}, "Q04": {"work_type", "remote"},
                "Q08": {b + ":" + g for b in ("original_listed_time", "listed_time") for g in ("month", "week")}, "Q06": set()}
    _require(query in expected and type(demo.partitions) is tuple and type(demo.skills) is tuple)
    _require(len(demo.partitions) == len(expected[query]) and {p.name for p in demo.partitions} == expected[query])
    _require(bool(demo.skills) if query == "Q06" else not demo.skills)
    _require(len({p.population for p in demo.partitions}) <= 1)
    for p in demo.partitions:
        _require(type(p) is Partition and p.kind in ("category", "remote", "month", "week"))
        _require(p.kind == ("remote" if p.name == "remote" else p.name.split(":")[-1] if query == "Q08" else "category"))
        for n in (p.population, p.known, p.missing):
            _count(n)
        _require(p.known + p.missing == p.population and type(p.rows) is tuple and bool(p.rows))
        _require(len({(type(r.key), r.key) for r in p.rows}) == len(p.rows))
        for r in p.rows:
            _require(type(r) is Bucket)
            _require(r.key is None or type(r.key) is (bool if p.kind == "remote" else str))
            _count(r.count)
            _require(r.count <= (p.known if r.key is not None else p.missing))
            _rate(r.share_all, r.count, p.population)
            _require(r.share_known is None) if r.key is None else _rate(r.share_known, r.count, p.known)
        if p.kind in ("month", "week"):
            _require(all(type(r.key) is str for r in p.rows) and sum(r.count for r in p.rows) == p.known)
            for r in p.rows:
                dt = datetime.strptime(r.key, "%Y-%m" if p.kind == "month" else "%Y-%m-%d")
                _require(r.key == dt.strftime("%Y-%m" if p.kind == "month" else "%Y-%m-%d"))
                _require(p.kind != "week" or dt.weekday() == 0)
        else:
            _require(sum(r.count for r in p.rows) == p.population)
            _require(sum(r.count for r in p.rows if r.key is None) == p.missing)
    if query == "Q08":
        for basis in ("original_listed_time", "listed_time"):
            pair = [p for p in demo.partitions if p.name.startswith(basis + ":")]
            _require(len({(p.population, p.known, p.missing) for p in pair}) == 1)
    if query == "Q06":
        _require(len({(s.dimension, s.bucket) for s in demo.skills}) == len(demo.skills))
        overall = [s for s in demo.skills if s.dimension == "global"]
        _require(len(overall) == 1 and overall[0].bucket is None)
        for s in demo.skills:
            _require(type(s) is SkillScope and s.dimension in ("global", "group", "experience"))
            _require(s.bucket is None or type(s.bucket) is str)
            _count(s.population)
            _count(s.zero_hit)
            _require(s.zero_hit <= s.population and type(s.rows) is tuple)
            _require(len({r.code for r in s.rows}) == len(s.rows))
            for r in s.rows:
                _require(type(r) is Skill and type(r.code) is str and r.code.startswith("DEMO_") and type(r.name) is str)
                _count(r.count)
                _require(r.count <= s.population - s.zero_hit)
                _rate(r.share, r.count, s.population)
        base = overall[0]
        for dimension in ("group", "experience"):
            parts = [s for s in demo.skills if s.dimension == dimension]
            _require(bool(parts) and sum(s.population for s in parts) == base.population
                     and sum(s.zero_hit for s in parts) == base.zero_hit)
            totals = Counter()
            for s in parts:
                totals.update({r.code: r.count for r in s.rows})
            _require(totals == Counter({r.code: r.count for r in base.rows}))
    return demo


def bucket_label(key):
    if key is None:
        return "Không xác định (NULL)"
    if type(key) is bool:
        return "TRUE" if key else "FALSE"
    return key
