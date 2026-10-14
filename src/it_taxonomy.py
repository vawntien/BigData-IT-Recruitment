"""Versioned A02 interpreter: unchanged occupation rules, structured v0.2 descriptions.

Loading the frozen v0.1.0 JSON delegates to the exact archived implementation.
No metadata classifications, manual labels, ETL or Spark/JVM parity claims.
"""
from __future__ import annotations

from description_processing import DescriptionProcessor, normalized_spans
from it_taxonomy_v010 import Taxonomy as LegacyTaxonomy
from tv2_csv import integer_key


class Taxonomy(LegacyTaxonomy):
    def __init__(self, config_path):
        super().__init__(config_path)
        mode = self.segment_config.get("mode", "legacy_v010")
        if mode == "legacy_v010":
            if self.version != "0.1.0":
                raise ValueError("Legacy description policy requires version 0.1.0")
            self.processor = None
        elif mode == "structured_source_v1":
            if self.version not in {"0.2.0", "0.2.1", "0.2.2"} or self.config.get("description_processing_version") != "structured-source-v1":
                raise ValueError("Unsupported structured description version")
            expected = {
                "oversize_policy": "retain_full_unit_use_task_anchored_windows_flag_unresolved_structure",
                "length_unit": "unicode_codepoints_after_NFC_lower_replacements_whitespace_collapse",
            }
            if any(self.segment_config.get(k) != v for k, v in expected.items()):
                raise ValueError("Unsupported long-unit policy")
            p = self.segment_config["parser"]
            if p["html_engine"] != "stdlib_html.parser.HTMLParser" or p["split_comma_and_and"]:
                raise ValueError("Unsupported parser behavior")
            c = self.segment_config["context_policy"]
            enums = [
                (p, "malformed_policy", "retain_text_mark_incomplete_no_unmapped_automatic_evidence"),
                (p, "implicit_heading_policy", "only_explicit_configured_heading_followed_by_colon_or_standalone_line"),
                (c, "negation_scope", "one_sentence_adversative_clause"),
                (c, "collaboration_scope", "block_only_when_before_task_and_no_explicit_self_cue_before_collaboration"),
                (c, "company_scope", "subject_prefix_or_company_section_except_explicit_hiring_sentence"),
                (c, "section_reset", "explicit_heading_only_no_cross_section_evidence"),
                (c, "unknown_actor_long_unit", "retain_mark_incomplete_no_automatic_evidence"),
                (self.segment_config["long_unit_policy"], "window_anchor", "required_task_term_set_or_first_required_set"),
                (self.segment_config["long_unit_policy"], "window_scope", "one_retained_sentence_clause_and_section"),
                (self.segment_config["long_unit_policy"], "status", "RETAINED_LONG_UNRESOLVED"),
                (self.segment_config["long_unit_policy"], "no_match_policy", "REVIEW_DESCRIPTION_PROCESSING_INCOMPLETE"),
            ]
            if any(policy.get(key) != expected_value for policy, key, expected_value in enums):
                raise ValueError("Unsupported description policy semantics")
            if c["default_section"] not in c["eligible_sections"]:
                raise ValueError("Default section must be eligible but actor checks still apply")
            if self.segment_config["long_unit_policy"]["window_characters"] != self.segment_config["max_normalized_characters"]:
                raise ValueError("Window and character diagnostic limits must agree")
            if not self.segment_config["long_unit_policy"]["preserve_full_unit"] or not self.segment_config["long_unit_policy"]["resolved_ineligible_section_is_complete"]:
                raise ValueError("Long units must be retained; scoped boilerplate is processed")
            if c["self_cue_term_set"] not in self.aliases:
                raise ValueError("Unknown self cue term set")
            self.processor = DescriptionProcessor(self)
        else:
            raise ValueError("Unknown description policy")

    def classify(self, title, description, job_id=None):
        if self.processor is None:
            return super().classify(title, description, job_id)
        normalized = {"title": self.normalize(title), "description": self.normalize(description)}
        source = {"title": title or "", "description": description or ""}
        document, units, processing = self.processor.process(source["description"])
        segments = [(u["index"], u["text"], u["normalized"]) for u in units]
        units_by_index = {u["index"]: u for u in units}
        cache = {}

        def matches(field, term_set, segment=None, full=False, window=None):
            key = (field, term_set, segment[0] if segment else None, full, window)
            if key in cache:
                return cache[key]
            raw, value = (segment[1], segment[2]) if segment else (source[field], normalized[field])
            if not value or (full and value not in {v for _, v in self.aliases[term_set]}) or (not full and not self.fast_patterns[term_set].search(value)):
                cache[key] = []
                return []
            evidence = []
            offset = window[0] if window else 0
            if window:
                value = value[window[0]:window[1]]
            for alias, pattern in self.patterns[term_set]:
                for hit in pattern.finditer(value):
                    if full and hit.span() != (0, len(value)):
                        continue
                    if segment:
                        evidence.append(self.processor.evidence(document, units_by_index[segment[0]], term_set, alias,
                                                                hit.start() + offset, hit.end() + offset))
                    else:
                        _, spans = normalized_spans(self, raw)
                        a, b = spans[hit.start()][0], spans[hit.end() - 1][1]
                        maximum = self.config["proposed_output_contract"]["evidence_excerpt_max_characters"]
                        lo = max(0, a - 40)
                        if b - lo > maximum:
                            lo = a
                        hi = min(len(raw), lo + maximum)
                        evidence.append(dict(field=field, term_set_id=term_set, matched_alias=alias, segment_index=None,
                                             excerpt=raw[lo:hi], raw_excerpt_start=lo, raw_excerpt_end=hi,
                                             raw_match_ranges=[[a, b]], raw_offset_unit="original_field_unicode_codepoints_half_open",
                                             normalized_start=hit.start(), normalized_end=hit.end(), normalized_coordinate_space="normalized_title",
                                             mapping_status="MAPPED_TO_RAW", excerpt_covers_all_match_ranges=b <= hi))
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
                term_sets = value["all_term_sets"]
                for segment in segments:
                    unit = units_by_index[segment[0]]
                    if unit["blocked_reasons"] or not all(self.fast_patterns[k].search(segment[2]) for k in term_sets):
                        continue
                    for a, b in self.processor.candidates(unit, term_sets):
                        window_value = segment[2][a:b]
                        if not all(self.fast_patterns[k].search(window_value) for k in term_sets):
                            continue
                        block = self.processor.blocked_window(unit, a, b, term_sets)
                        unit.setdefault("window_diagnostics", []).append(dict(term_sets=term_sets, normalized_start=a,
                                                                            normalized_end=b, blocked_reason=block))
                        if block:
                            continue
                        evidence = []
                        for term_set in term_sets:
                            hit = matches("description", term_set, segment, window=(a, b))
                            if not hit:
                                break
                            evidence.extend(hit)
                        else:
                            result.extend(evidence)
                unique = {(e["term_set_id"], e["matched_alias"], e["segment_index"], e["normalized_start"], e["normalized_end"]): e for e in result}
                return bool(unique), list(unique.values())
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
        reasons = ["DESCRIPTION_PROCESSING_INCOMPLETE"] if processing["incomplete"] else []
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
        result["description_processing"] = processing
        result["description_segments"] = [{k: v for k, v in unit.items() if k != "normalized"} for unit in units]
        return result

