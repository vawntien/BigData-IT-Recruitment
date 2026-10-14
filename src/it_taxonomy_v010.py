"""Reusable A02 JSON interpreter for A04 and TV1 integration.

No independent keyword list, metadata decisions, ETL, or gold labels. The same
class can be loaded once per Spark worker; native JVM parity remains a TV1 check.
"""
from __future__ import annotations

import difflib
import hashlib
import json
import re
import unicodedata
from pathlib import Path

from tv2_csv import integer_key

# Java's \p{Z} plus default ASCII \s, independent of occupational rules.
Z_CHARS = "".join(chr(c) for c in [32, 160, 5760, *range(8192, 8203), 8232, 8233, 8239, 8287, 12288])


def java_space_regex(pattern):
    return re.compile(pattern.replace(r"\p{Z}", Z_CHARS), re.ASCII)


class Taxonomy:
    def __init__(self, config_path):
        raw = Path(config_path).read_bytes()
        self.config = json.loads(raw.decode("utf-8"))
        self.sha256 = hashlib.sha256(raw).hexdigest()
        self.version = self.config["version"]
        n = self.config["normalization"]
        if self.config["schema_version"] != 1 or n["unicode_form"] != "NFC" or n["case"] != "lower" or n["strip_diacritics"]:
            raise ValueError("Unsupported normalization/schema; integration must be explicit")
        if self.config["inputs"]["metadata_policy"]["enabled_for_decision"]:
            raise ValueError("Metadata decisions are not implemented or authorized for this interpreter")
        if n["literal_match"]["mode"] != "unicode_token_bounded_literal_phrase":
            raise ValueError("Unsupported literal match mode")
        self.missing_tokens = set(n["missing_tokens"])
        self.replacements = [(re.compile(r["pattern"]), r["replacement"]) for r in n["replacements"]]
        self.whitespace = java_space_regex(n["whitespace_regex"])
        self.segment_config = n["description_segments"]
        self.splitter = java_space_regex(self.segment_config["split_pattern"])
        self.groups = {g["code"]: g for g in self.config["groups"]}
        self.subgroups = {g["code"]: g for g in self.config["subgroups"]}
        self.tiers = {t["code"]: t["rank"] for t in self.config["rule_language"]["evidence_tiers"]}
        self.aliases, self.patterns, self.fast_patterns = {}, {}, {}
        for key, term_set in self.config["term_sets"].items():
            aliases = [(alias, self.normalize(alias)) for alias in term_set["aliases"]]
            if not aliases or any(not normalized for _, normalized in aliases) or len({v for _, v in aliases}) != len(aliases):
                raise ValueError(f"Invalid/duplicate normalized aliases: {key}")
            self.aliases[key] = aliases
            # Python Unicode \w is L/N/underscore; NFC retains Vietnamese accents.
            patterns = [r"\s+".join(re.escape(t) for t in a.split(" ")) for _, a in aliases]
            self.patterns[key] = [(alias, re.compile(r"(?<![\w])" + p + r"(?![\w])")) for (alias, _), p in zip(aliases, patterns)]
            self.fast_patterns[key] = re.compile(r"(?<![\w])(?:" + "|".join(patterns) + r")(?![\w])")
        self.rules = self.config["include_rules"] + self.config["general_it_rules"] + self.config["exclusion_rules"]
        subgroup_rules = [r for g in self.subgroups.values() for r in g["rules"]]
        all_rules = self.rules + subgroup_rules
        if len({r["id"] for r in all_rules}) != len(all_rules):
            raise ValueError("Duplicate rule id")
        for rule in all_rules:
            self.validate_condition(rule["condition"])
            if "group_code" in rule and rule["group_code"] not in self.groups:
                raise ValueError("Unknown group")
            if "evidence_tier" in rule and rule["evidence_tier"] not in self.tiers:
                raise ValueError("Unknown tier")
        for key in self.segment_config["blocked_term_sets"]:
            if key not in self.aliases:
                raise ValueError("Unknown blocked term set")
        policy = self.config["decision_policy"]
        if policy["unresolved_it_group_code"] not in self.groups or policy["subgroup_policy"]["fallback_code"] not in self.subgroups:
            raise ValueError("Unknown fallback")

    def is_missing(self, text):
        return text is None or text.strip().lower() in self.missing_tokens

    def normalize(self, text):
        if self.is_missing(text):
            return ""
        text = unicodedata.normalize("NFC", text).lower()
        for pattern, replacement in self.replacements:
            text = pattern.sub(replacement, text)
        return self.whitespace.sub(" ", text).strip()

    def validate_condition(self, condition):
        if len(condition) != 1:
            raise ValueError("One operator required per predicate")
        op, value = next(iter(condition.items()))
        if op in {"any", "all"}:
            if not value:
                raise ValueError("Empty predicates")
            for part in value:
                self.validate_condition(part)
        elif op == "is_missing":
            if value not in self.config["inputs"]["search_fields"]:
                raise ValueError("Unknown input field")
        elif op in {"match", "full_match", "same_segment"}:
            if value["field"] not in self.config["inputs"]["search_fields"]:
                raise ValueError("Unknown input field")
            keys = value["all_term_sets"] if op == "same_segment" else [value["term_set"]]
            if not keys or any(key not in self.aliases for key in keys):
                raise ValueError("Unknown/empty term sets")
            if op == "same_segment" and value["field"] != "description":
                raise ValueError("same_segment requires description")
        else:
            raise ValueError(f"Unknown operator: {op}")

    def excerpt(self, original, normalized, start, end):
        """Map a normalized hit back to a real source slice, including late hits."""
        nfc = unicodedata.normalize("NFC", original)
        spans = []
        for tag, a, b, c, d in difflib.SequenceMatcher(a=original, b=nfc, autojunk=False).get_opcodes():
            if tag == "equal":
                spans.extend((a + i, a + i + 1) for i in range(d - c))
            else:
                spans.extend((a, max(a + 1, b)) for _ in range(d - c))
        lowered, mapped = [], []
        for char, span in zip(nfc, spans):
            lowered.extend(char.lower())
            mapped.extend([span] * len(char.lower()))
        value = "".join(lowered)
        for pattern, replacement in [*self.replacements, (self.whitespace, " ")]:
            pieces, remapped, cursor = [], [], 0
            for hit in pattern.finditer(value):
                pieces.append(value[cursor:hit.start()])
                remapped.extend(mapped[cursor:hit.start()])
                pieces.append(replacement)
                remapped.extend([(mapped[hit.start()][0], mapped[hit.end() - 1][1])] * len(replacement))
                cursor = hit.end()
            pieces.append(value[cursor:])
            remapped.extend(mapped[cursor:])
            value, mapped = "".join(pieces), remapped
        left = len(value) - len(value.lstrip())
        mapped = mapped[left:len(value.rstrip())]
        if value.strip() != normalized or not mapped:
            raise ValueError("Evidence normalization/offset mapping mismatch")
        source_start, source_end = mapped[start][0], mapped[end - 1][1]
        maximum = self.config["proposed_output_contract"]["evidence_excerpt_max_characters"]
        lo = max(0, source_start - 50)
        if source_end - lo > maximum:
            lo = source_start
        return original[lo:min(len(original), lo + maximum)]

    def classify(self, title, description, job_id=None):
        normalized = {"title": self.normalize(title), "description": self.normalize(description)}
        source = {"title": title or "", "description": description or ""}
        segments, skipped = [], False
        if not self.is_missing(description):
            for i, raw in enumerate(self.splitter.split(description)):
                value = self.normalize(raw)
                if len(value) > self.segment_config["max_normalized_characters"]:
                    skipped = True
                elif value:
                    segments.append((i, raw, value))
        cache = {}

        def matches(field, term_set, segment=None, full=False):
            key = (field, term_set, segment[0] if segment else None, full)
            if key in cache:
                return cache[key]
            raw, value = (segment[1], segment[2]) if segment else (source[field], normalized[field])
            if not value or (full and value not in {v for _, v in self.aliases[term_set]}) or (not full and not self.fast_patterns[term_set].search(value)):
                cache[key] = []
                return []
            evidence = []
            for alias, pattern in self.patterns[term_set]:
                for hit in pattern.finditer(value):
                    if full and hit.span() != (0, len(value)):
                        continue
                    evidence.append(dict(field=field, term_set_id=term_set, matched_alias=alias, segment_index=segment[0] if segment else None, excerpt=self.excerpt(raw, value, hit.start(), hit.end())))
            cache[key] = evidence
            return evidence

        blocked_cache = {}

        def evaluate(condition):
            op, value = next(iter(condition.items()))
            if op == "all":
                result = []
                for part in value:
                    success, evidence = evaluate(part)
                    if not success:
                        return False, []
                    result.extend(evidence)
                return True, result
            if op == "any":
                parts = [evaluate(part) for part in value]
                return any(ok for ok, _ in parts), [e for ok, ev in parts if ok for e in ev]
            if op == "is_missing":
                return self.is_missing(source[value]), []
            if op in {"match", "full_match"}:
                evidence = matches(value["field"], value["term_set"], full=op == "full_match")
                return bool(evidence), evidence
            if op == "same_segment":
                result = []
                for segment in segments:
                    if segment[0] not in blocked_cache:
                        blocked_cache[segment[0]] = any(self.fast_patterns[k].search(segment[2]) for k in self.segment_config["blocked_term_sets"])
                    if blocked_cache[segment[0]]:
                        continue
                    evidence = []
                    for term_set in value["all_term_sets"]:
                        hit = matches("description", term_set, segment)
                        if not hit:
                            break
                        evidence.extend(hit)
                    else:
                        result.extend(evidence)
                return bool(result), result
            raise ValueError(op)

        rule_evidence = {}

        def collect(rules):
            matched = []
            for rule in rules:
                ok, evidence = evaluate(rule["condition"])
                if ok:
                    matched.append(rule)
                    rule_evidence[rule["id"]] = [dict(rule_id=rule["id"], **e) for e in evidence]
            return matched

        group_matches = collect(self.config["include_rules"])
        general = collect(self.config["general_it_rules"])
        excluded = collect(self.config["exclusion_rules"])
        policy = self.config["decision_policy"]

        def rule_sort(rule, priority):
            return self.tiers[rule["evidence_tier"]], priority, rule["rule_priority"], rule["id"]

        group_matches.sort(key=lambda r: rule_sort(r, self.groups[r["group_code"]]["priority"]))
        candidates = list(dict.fromkeys(r["group_code"] for r in group_matches))
        reasons = ["DESCRIPTION_SEGMENT_SKIPPED"] if skipped else []
        if len(candidates) > 1:
            reasons.append("MULTIPLE_GROUP_CANDIDATES")
        decision, primary, subgroup, selected = None, None, None, None
        if (group_matches or general) and excluded:
            decision = "REVIEW"
            reasons.insert(0, "POSITIVE_EXCLUSION_CONFLICT")
        elif excluded:
            decision = "REJECT"
            reasons.insert(0, "OUTSIDE_IT_ROLE")
        elif group_matches:
            decision, selected = "ACCEPT", group_matches[0]
            primary = selected["group_code"]
            reasons.insert(0, selected["evidence_tier"])
        elif general:
            decision = "ACCEPT"
            selected = min(general, key=lambda r: rule_sort(r, self.groups[r["group_code"]]["priority"]))
            primary = policy["unresolved_it_group_code"]
            reasons.insert(0, "GENERAL_IT_UNCLASSIFIED")
        else:
            ambiguous = matches("title", policy["ambiguous_title_term_set"]) or matches("title", policy["ambiguous_title_full_match_term_set"], full=True)
            if self.is_missing(title):
                reasons.insert(0, "MISSING_TITLE")
            if ambiguous:
                reasons.insert(0, "AMBIGUOUS_TITLE_WITHOUT_CONTEXT")
            decision = "REVIEW" if reasons else "REJECT"
            if decision == "REJECT":
                reasons = ["NO_IT_ROLE_EVIDENCE"]
        if primary == policy["subgroup_policy"]["parent"]:
            sub_matches = []
            for group in self.subgroups.values():
                sub_matches.extend((group, rule) for rule in collect(group["rules"]))
            sub_matches.sort(key=lambda pair: rule_sort(pair[1], pair[0]["priority"]))
            subgroup = sub_matches[0][0]["code"] if sub_matches else policy["subgroup_policy"]["fallback_code"]
            if len({g["code"] for g, _ in sub_matches}) > 1:
                reasons.append("MULTIPLE_SUBGROUP_CANDIDATES")
        result = dict(taxonomy_version=self.version, taxonomy_sha256=self.sha256, it_decision=decision, is_it={"ACCEPT": True, "REJECT": False, "REVIEW": None}[decision], primary_group_code=primary, subgroup_code=subgroup, candidate_group_codes=candidates, selected_rule_id=selected["id"] if selected else None, reason_codes=list(dict.fromkeys(reasons)), matched_rule_ids=sorted(rule_evidence), match_evidence=[e for key in sorted(rule_evidence) for e in rule_evidence[key]])
        if job_id is not None:
            result["job_id"] = integer_key(job_id)
            if result["job_id"] is None:
                raise ValueError("Missing job_id")
        return result

    def check_illustrative_cases(self):
        failures = []
        for case in self.config["illustrative_cases"]:
            actual = self.classify(case["input"].get("title"), case["input"].get("description"))
            if any(actual[key] != value for key, value in case["expected"].items()):
                failures.append(dict(case_id=case["case_id"], expected=case["expected"], actual=actual))
        if failures:
            raise AssertionError(json.dumps(failures, ensure_ascii=False))
        return len(self.config["illustrative_cases"])
