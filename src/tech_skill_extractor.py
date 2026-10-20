"""A05 dictionary extraction with independent skill scope and raw provenance.

Only description is inspected. A04's source-mapping primitives are reused;
its occupation gates, qualification blockers and 500-character windows are not.
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import Path

from description_processing import MappedHTML, SourceDocument, normalized_spans
from tv2_csv import integer_key

EXTRACTOR_VERSION = "a05-source-mapped-v1.2"
SOURCE_FIELD = "postings.description"
OFFSET_UNIT = "original_field_unicode_codepoints_half_open"


def literal_pattern(value):
    phrase = r"\s+".join(re.escape(part) for part in value.split())
    return re.compile(r"(?<![\w+#])" + phrase + r"(?![\w+#])")


class TechSkillExtractor:
    def __init__(self, config_path=None, *, config_bytes=None):
        if (config_path is None) == (config_bytes is None):
            raise ValueError("Supply exactly one dictionary path or byte payload")
        raw = Path(config_path).read_bytes() if config_bytes is None else config_bytes
        self.config = json.loads(raw.decode("utf-8"))
        self.sha256 = hashlib.sha256(raw).hexdigest()
        self.version = self.config["version"]
        if self.config["schema_version"] != 1 or not re.fullmatch(r"\d+\.\d+\.\d+", self.version):
            raise ValueError("Unsupported dictionary schema/version")
        n = self.config["normalization"]
        if n != dict(unicode_form="NFC", case="lower", strip_diacritics=False,
                     whitespace="collapse", preserve_punctuation=True,
                     missing_tokens=["", "null", "n/a", "na"]):
            raise ValueError("Unsupported skill normalization")
        if self.config["source_fields"] != [SOURCE_FIELD]:
            raise ValueError("Only postings.description is enabled")
        if self.config["matching"]["overlap"] != "longest_alias_first_no_implied_parent_skill":
            raise ValueError("Unsupported alias arbitration")
        self.whitespace, self.replacements = re.compile(r"\s+"), []
        self.skills, self.aliases, seen = {}, [], set()
        self.contexts = self.config["contexts"]
        for skill in self.config["skills"]:
            code = skill["code"]
            if not re.fullmatch(r"[A-Z][A-Z0-9_]*", code) or code in self.skills:
                raise ValueError("Invalid/duplicate stable skill code")
            if not skill["name"] or not skill["group"] or not skill["aliases"]:
                raise ValueError("Incomplete skill definition")
            self.skills[code] = skill
            for alias in skill["aliases"]:
                value = self.normalize(alias["text"])
                if not value or value in seen or (alias.get("context") and alias["context"] not in self.contexts):
                    raise ValueError("Duplicate alias or unknown context")
                seen.add(value)
                self.aliases.append(dict(code=code, alias=alias["text"], value=value,
                                         context=alias.get("context"), pattern=literal_pattern(value)))
        self.context_regexes = {
            key: dict(patterns=[re.compile(p) for p in c.get("patterns", [])],
                      excluded=[re.compile(p) for p in c.get("excluded_patterns", [])],
                      nearby=[literal_pattern(self.normalize(t)) for t in c.get("nearby_terms", [])])
            for key, c in self.contexts.items()}
        self.list_separator = re.compile(self.config["matching"]["technology_list_separator_regex"])
        self.parser = self.config["parser"]
        if self.parser["long_description_policy"] != "retain_all_units_no_500_character_cutoff":
            raise ValueError("A05 must retain long descriptions")
        self.structural = re.compile(self.parser["structural_regex"])
        self.sentences = re.compile(self.parser["sentence_boundary_regex"])
        self.adversatives = re.compile(self.parser["adversative_regex"], re.I)
        self.protected = [re.compile(p, re.I) for p in self.parser["protected_regexes"]]
        self.headings = {}
        for section, names in self.config["sections"].items():
            for name in names:
                value = self.normalize(name)
                if value in self.headings:
                    raise ValueError("Ambiguous section heading")
                self.headings[value] = section
        self.heading_pattern = re.compile(r"(?<!\w)(?:" + "|".join(
            re.escape(h) for h in sorted(self.headings, key=len, reverse=True)) + r")\s*:", re.I)
        for key in ["position", "company", "requirement", "preferred", "task"]:
            setattr(self, key, re.compile(self.config[key + "_cue_regex"] if key in {"position", "company"}
                                         else self.config[key + "_regex"], re.I))

    def normalize(self, text):
        return self.whitespace.sub(" ", unicodedata.normalize("NFC", text).lower()).strip()

    def _document(self, raw):
        if re.search(r"</?(?:p|div|span|br|li|ul|ol|h[1-6]|section|article|table|a|b|strong|em|i|script|style)\b[^>]*>|&(?:[A-Za-z]\w*|#\d+|#x[0-9A-Fa-f]+);", raw, re.I):
            return MappedHTML(raw, self.parser).document()
        return SourceDocument(raw)

    def _units(self, document):
        text = document.text
        protected = [(h.start(), h.end()) for p in self.protected for h in p.finditer(text)]
        events = [(h.start(), h.end(), None) for h in self.structural.finditer(text)]
        events += [(h.start(), h.end(), None) for h in self.sentences.finditer(text)
                   if not any(a <= h.start() < b for a, b in protected)]
        events += [(h.start(), h.end(), None) for h in self.adversatives.finditer(text)]
        events += [(h.start(), h.end(), self.headings[self.normalize(h.group().rstrip(": "))])
                   for h in self.heading_pattern.finditer(text)]
        for h in re.finditer(r"[^\r\n\u2028\u2029]+", text):
            name = self.normalize(h.group().strip().rstrip(":"))
            if name in self.headings:
                events.append((h.start(), h.end(), self.headings[name]))
        events.sort(key=lambda e: (e[0], e[2] is None, -e[1]))
        cursor, section, units = 0, "UNKNOWN", []

        def emit(start, end):
            original = text[start:end]
            value, spans = normalized_spans(self, original)
            if value:
                units.append(dict(index=len(units), start=start, end=end, text=original,
                                  normalized=value, spans=spans, section=section))

        for start, end, next_section in events:
            if start < cursor:
                continue
            emit(cursor, start)
            if next_section:
                section = next_section
            cursor = end
        emit(cursor, len(text))
        return units

    def _hits(self, value):
        all_hits = [dict(alias, start=h.start(), end=h.end())
                    for alias in self.aliases for h in alias["pattern"].finditer(value)]
        chosen = []
        for hit in sorted(all_hits, key=lambda h: (-(h["end"] - h["start"]), h["start"], h["code"], h["alias"])):
            if not any(hit["start"] < old["end"] and hit["end"] > old["start"] for old in chosen):
                chosen.append(hit)
        return sorted(chosen, key=lambda h: (h["start"], h["end"], h["code"]))

    def _contexts(self, value, hits):
        decisions = {}
        excluded = set()
        for i, hit in enumerate(hits):
            key = hit["context"]
            if not key:
                decisions[i] = "ALIAS_LITERAL_BOUNDARY"
                continue
            c = self.context_regexes[key]
            if any(m.start() < hit["end"] and m.end() > hit["start"]
                   for p in c["excluded"] for m in p.finditer(value)):
                excluded.add(i)
                continue
            radius = self.config["matching"]["context_radius_codepoints"]
            nearby = value[max(0, hit["start"] - radius):hit["end"] + radius]
            if any(m.start() <= hit["start"] and m.end() >= hit["end"]
                   for p in c["patterns"] for m in p.finditer(value)) or any(p.search(nearby) for p in c["nearby"]):
                decisions[i] = "CTX_" + key + "_EXPLICIT"
        # A list must be connected to an already grounded technology, not two
        # ambiguous words mutually validating one another (e.g. 'Go or R').
        while True:
            changed = False
            for i, hit in enumerate(hits):
                if i in decisions or i in excluded or not self.contexts[hit["context"]].get("allow_technology_list"):
                    continue
                for j in [i - 1, i + 1]:
                    if j not in decisions:
                        continue
                    left, right = sorted([hit, hits[j]], key=lambda h: h["start"])
                    between = value[left["end"]:right["start"]]
                    if between and self.list_separator.fullmatch(between):
                        decisions[i] = "CTX_" + hit["context"] + "_TECHNOLOGY_LIST"
                        changed = True
                        break
            if not changed:
                break
        return decisions

    @staticmethod
    def _negated(value, hit):
        # Requirement negation has its own scope; unrelated 'not only' and
        # 'no less than' do not negate a skill. Semicolons/adversatives are units.
        positive_boundary = re.compile(r",(?=\s*\w+(?:\s+\w+){0,2}\s+(?:is|are)\s+(?:required|preferred))")
        prefixes = [r"\bno\s+(?:(?:prior|previous|professional)\s+)?(?:experience|knowledge|proficiency|expertise|background|skills?)\b",
                    r"\bno\b(?!\s+(?:less|fewer|more)\b)(?=[^.;!?]{0,80}\b(?:required|needed|necessary)\b)",
                    r"\b(?:do(?:es)? not|don't|doesn't)\s+(?:require|need|expect|use)\b",
                    r"\b(?:not|never)\s+(?:use|using|work with|write|code|develop|require|need)\b",
                    r"\bwithout\s+(?:any\s+)?(?:prior\s+)?(?:experience|knowledge|using|needing)\b",
                    r"\bkhông\s+(?:yêu cầu|cần|đòi hỏi|bắt buộc)\b"]
        for pattern in prefixes:
            for neg in re.finditer(pattern, value):
                end = next((b.start() for b in positive_boundary.finditer(value, neg.end())), len(value))
                if neg.start() <= hit["start"] < end:
                    return True
        for neg in re.finditer(r"\b(?:not required|not necessary|not needed|not mandatory|not a requirement)\b", value):
            start = value.rfind(",", 0, neg.start()) + 1
            if start <= hit["start"] < neg.end():
                return True
        return False

    def _mention_type(self, unit, hit, hits):
        value, section = unit["normalized"], unit["section"]
        if self._negated(value, hit):
            return "NEGATED", "NEGATED_SKILL_REQUIREMENT_OR_USE"
        owns_position = bool(self.position.search(value))
        if section == "COMPANY" and not owns_position:
            return "COMPANY_ONLY", "SECTION_COMPANY_WITHOUT_POSITION_CUE"
        if section in {"BENEFITS", "EEO"}:
            return "OUTSIDE_POSITION", "SECTION_" + section
        company = self.company.search(value)
        strong_company = re.match(r"(?:we|our|the company)\b", value)
        if company and not owns_position and (strong_company or
                (not self.requirement.search(value) and not self.task.search(value))):
            return "COMPANY_ONLY", "COMPANY_SUBJECT_WITHOUT_POSITION_CUE"
        if len(value) > 500 and self.task.search(value) and re.search(
                r"\b(?:minimum qualifications|required qualifications|required skills|preferred skills|qualifications)\b",
                value):
            return "AMBIGUOUS_SCOPE", "MIXED_TASK_AND_QUALIFICATION_WITHOUT_UNIT_BOUNDARY"
        following = next((h["start"] for h in hits if h["start"] > hit["start"]), len(value))
        suffix = value[hit["end"]:min(following, hit["end"] + 80)]
        # The immediate suffix wins ('Python required, Java preferred').
        if self.preferred.search(suffix):
            return "PREFERRED", "PREFERRED_SUFFIX"
        if re.search(r"\b(?:required|mandatory|essential)\b", suffix):
            return "REQUIRED", "REQUIRED_SUFFIX"
        candidate_prefix = re.match(
            r"(?:(?:strong|good|excellent|deep|extensive|proven|working)\s+)?"
            r"(?:experience|knowledge|understanding|proficien\w*|familiar\w*|expertise|ability|skills|"
            r"qualifications|minimum|bachelor|master|you (?:have|must)|the ideal candidate)\b", value)
        hiring = re.match(r"we (?:are (?:seeking|hiring)|are looking for)\b", value)
        if section in {"TASK", "ROLE"} and not candidate_prefix and not hiring:
            return "TASK", "POSITION_TASK_WITHOUT_CANDIDATE_PREFIX"
        cues = [(m.start(), "PREFERRED") for m in self.preferred.finditer(value[:hit["start"]])]
        cues += [(m.start(), "REQUIRED") for m in self.requirement.finditer(value[:hit["start"]])]
        if cues:
            return max(cues)[1], "CANDIDATE_CUE"
        if section == "PREFERRED":
            return "PREFERRED", "SECTION_PREFERRED"
        if section == "REQUIREMENTS":
            return "REQUIRED", "SECTION_REQUIREMENTS"
        if self.requirement.search(value):
            return "REQUIRED", "CANDIDATE_REQUIREMENT_SENTENCE"
        if self.preferred.search(value):
            return "PREFERRED", "CANDIDATE_PREFERRED_SENTENCE"
        if section in {"TASK", "ROLE"} or owns_position or self.task.search(value):
            return "TASK", "POSITION_TASK_OR_ROLE"
        return "AMBIGUOUS_SCOPE", "NO_POSITION_OR_CANDIDATE_SCOPE"

    def extract(self, description, job_id=None, *, run_id="development"):
        job = integer_key(str(job_id)) if job_id is not None else None
        if job_id is not None and job is None:
            raise ValueError("Missing job_id")
        if not isinstance(run_id, str) or not run_id:
            raise ValueError("Missing run_id")
        common = dict(job_id=job, run_id=run_id, dictionary_version=self.version,
                      dictionary_sha256=self.sha256, extractor_version=EXTRACTOR_VERSION,
                      source_field=SOURCE_FIELD)
        source_hash = hashlib.sha256(description.encode("utf-8")).hexdigest() if isinstance(description, str) else None
        status = dict(common, source_text_sha256=source_hash, source_status=None,
                      error_code=None, review_required=False, accepted_skill_count=0,
                      accepted_evidence_count=0, excluded_evidence_count=0,
                      ambiguous_evidence_count=0, technical_skills=None, parser_issues=[],
                      units=0, long_units_retained=0, dropped_oversize_units=0)
        result = dict(job_skills=[], evidence=[], processing=status)
        if description is None or (isinstance(description, str) and self.normalize(description) in self.config["normalization"]["missing_tokens"]):
            status["source_status"] = "SOURCE_MISSING"
            return result
        if not isinstance(description, str):
            status.update(source_status="FAILED", error_code="INVALID_DESCRIPTION_TYPE")
            return result
        try:
            document = self._document(description)
            units = self._units(document)
            status.update(parser_issues=document.issues, units=len(units),
                          long_units_retained=sum(len(u["normalized"]) > 500 for u in units))
            mapping_issues = False
            for unit in units:
                value = unit["normalized"]
                hits = self._hits(value)
                contexts = self._contexts(value, hits)
                for i, hit in enumerate(hits):
                    a, b = unit["spans"][hit["start"]][0], unit["spans"][hit["end"] - 1][1]
                    start, end = unit["start"] + a, unit["start"] + b
                    ranges = document.ranges(start, end)
                    mapped = bool(ranges) and document.mapped(start, end)
                    kind, scope_rule = self._mention_type(unit, hit, hits)
                    context_rule = contexts.get(i, "AMBIGUOUS_ALIAS_CONTEXT")
                    if not mapped:
                        mapping_issues = True
                        kind, scope_rule = "AMBIGUOUS_MAPPING", "SOURCE_MAPPING_UNAVAILABLE"
                    elif i not in contexts and kind not in {"NEGATED", "COMPANY_ONLY", "OUTSIDE_POSITION"}:
                        kind, scope_rule = "AMBIGUOUS_ALIAS", "ALIAS_CONTEXT_NOT_CONFIRMED"
                    accepted = mapped and i in contexts and kind in self.config["accepted_mention_types"]
                    unit_ranges = document.ranges(unit["start"], unit["end"])
                    lo, hi = (unit_ranges[0][0], unit_ranges[-1][1]) if unit_ranges else (None, None)
                    identity = json.dumps([job, hit["code"], ranges, self.sha256], separators=(",", ":"))
                    skill = self.skills[hit["code"]]
                    result["evidence"].append(dict(common, skill_code=hit["code"], skill_name=skill["name"],
                        skill_group=skill["group"], evidence_id=hashlib.sha256(identity.encode("utf-8")).hexdigest(),
                        matched_alias=hit["alias"], matched_text="".join(description[x:y] for x, y in ranges) if mapped else None,
                        derived_matched_text=document.text[start:end], raw_match_ranges=ranges if mapped else None,
                        raw_offset_unit=OFFSET_UNIT, excerpt=description[lo:hi] if lo is not None else None,
                        raw_excerpt_start=lo, raw_excerpt_end=hi, sentence_text=unit["text"],
                        unit_index=unit["index"], section=unit["section"], normalized_start=hit["start"],
                        normalized_end=hit["end"], derived_start=start, derived_end=end,
                        source_text_sha256=source_hash, mapping_status="MAPPED_TO_RAW" if mapped else "UNAVAILABLE",
                        mention_type=kind, accepted=accepted, rule_id=context_rule + ":" + scope_rule))
            for code in sorted({e["skill_code"] for e in result["evidence"] if e["accepted"]}):
                accepted = [e for e in result["evidence"] if e["accepted"] and e["skill_code"] == code]
                skill = self.skills[code]
                result["job_skills"].append(dict(common, skill_code=code, skill_name=skill["name"],
                    skill_group=skill["group"], mention_types=sorted({e["mention_type"] for e in accepted}),
                    evidence_ids=[e["evidence_id"] for e in accepted], evidence_count=len(accepted)))
            ambiguous = sum(e["mention_type"].startswith("AMBIGUOUS") for e in result["evidence"])
            count = len(result["job_skills"])
            partial = bool(document.issues or mapping_issues)
            status.update(source_status="PARTIAL" if partial else "PROCESSED_WITH_MATCH" if count else "PROCESSED_NO_MATCH",
                          technical_skills=[s["skill_code"] for s in result["job_skills"]] if count or not partial else None,
                          review_required=bool(ambiguous or partial), ambiguous_evidence_count=ambiguous,
                          accepted_skill_count=count, accepted_evidence_count=sum(e["accepted"] for e in result["evidence"]),
                          excluded_evidence_count=sum(not e["accepted"] for e in result["evidence"]))
        except (ValueError, AssertionError, UnicodeError) as error:
            # Processing failures must never masquerade as successful zero-hit.
            result["job_skills"], result["evidence"] = [], []
            status.update(source_status="FAILED", error_code=type(error).__name__, review_required=True,
                          technical_skills=None, accepted_skill_count=0, accepted_evidence_count=0)
        return result
