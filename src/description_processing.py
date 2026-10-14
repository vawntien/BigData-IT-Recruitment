"""Configured description structure and exact source provenance for A02 v0.2.

This parser never supplies occupational aliases or manual labels. Long units are
retained; automatic matching uses local windows and reports unresolved structure.
"""
from __future__ import annotations

import difflib
import hashlib
import html
import re
import unicodedata
from html.parser import HTMLParser


def merge_ranges(ranges):
    result = []
    for start, end in ranges:
        if result and start <= result[-1][1]:
            result[-1][1] = max(end, result[-1][1])
        else:
            result.append([start, end])
    return result


class SourceDocument:
    def __init__(self, raw, text=None, origins=None, issues=None, removed=None):
        self.raw = raw
        self.text = raw if text is None else text
        self.origins = origins
        self.issues = issues or []
        self.removed = removed or []

    def ranges(self, start, end):
        if self.origins is None:
            return [[start, end]] if start < end else []
        return merge_ranges(span for span in self.origins[start:end] if span is not None)

    def mapped(self, start, end):
        return self.origins is None or all(span is not None or char.isspace()
                                          for char, span in zip(self.text[start:end], self.origins[start:end]))


class MappedHTML(HTMLParser):
    def __init__(self, raw, policy):
        super().__init__(convert_charrefs=False)
        self.raw, self.policy = raw, policy
        self.line_starts = [0] + [m.end() for m in re.finditer("\n", raw)]
        self.pieces, self.origins, self.issues, self.removed = [], [], [], []
        self.suppressed = []

    def position(self):
        line, column = self.getpos()
        return self.line_starts[line - 1] + column

    def boundary(self):
        self.pieces.append("\n")
        self.origins.append(None)

    def handle_starttag(self, tag, attrs):
        start = self.position()
        if tag in self.policy["remove_content_tags"]:
            self.suppressed.append((tag, start))
        if not self.suppressed and tag in self.policy["block_tags"]:
            self.boundary()

    def handle_startendtag(self, tag, attrs):
        if tag in self.policy["remove_content_tags"]:
            start = self.position()
            self.removed.append(dict(start=start, end=start + len(self.get_starttag_text()), reason=tag))
        elif not self.suppressed and tag in self.policy["block_tags"]:
            self.boundary()

    def handle_endtag(self, tag):
        if self.suppressed:
            if tag == self.suppressed[-1][0]:
                _, start = self.suppressed.pop()
                end = self.raw.find(">", self.position())
                self.removed.append(dict(start=start, end=end + 1 if end >= 0 else len(self.raw), reason=tag))
            return
        if tag in self.policy["block_tags"]:
            self.boundary()

    def handle_data(self, data):
        if self.suppressed:
            return
        start = self.position()
        self.pieces.append(data)
        if self.raw[start:start + len(data)] != data:
            self.issues.append("HTML_DATA_MAPPING_UNAVAILABLE")
            self.origins.extend([None] * len(data))
        else:
            self.origins.extend((start + i, start + i + 1) for i in range(len(data)))

    def reference(self, token):
        if self.suppressed:
            return
        start = self.position()
        end = start + len(token)
        if self.raw[end:end + 1] == ";":
            token += ";"
            end += 1
        decoded = html.unescape(token) if self.policy["decode_entities"] else token
        self.pieces.append(decoded)
        if decoded == token:
            self.origins.extend((start + i, start + i + 1) for i in range(len(token)))
        else:
            self.origins.extend([(start, end)] * len(decoded))

    def handle_entityref(self, name):
        self.reference("&" + name)

    def handle_charref(self, name):
        self.reference("&#" + name)

    def document(self):
        self.feed(self.raw)
        self.close()
        if self.suppressed:
            self.issues.append("UNCLOSED_SCRIPT_OR_STYLE")
            self.removed.extend(dict(start=start, end=len(self.raw), reason=tag) for tag, start in self.suppressed)
        text = "".join(self.pieces)
        assert len(text) == len(self.origins)
        return SourceDocument(self.raw, text, self.origins, self.issues, self.removed)


def normalized_spans(model, original):
    """Map normalized code points to half-open positions in pre-normalized text."""
    nfc = unicodedata.normalize("NFC", original)
    if nfc == original:
        spans = [(i, i + 1) for i in range(len(original))]
    else:
        spans = []
        for tag, a, b, c, d in difflib.SequenceMatcher(a=original, b=nfc, autojunk=False).get_opcodes():
            if tag == "equal":
                spans.extend((a + i, a + i + 1) for i in range(d - c))
            else:
                spans.extend((a, b) for _ in range(d - c))
    pieces, mapped = [], []
    for char, span in zip(nfc, spans):
        lowered = char.lower()
        pieces.append(lowered)
        mapped.extend([span] * len(lowered))
    value = "".join(pieces)
    for pattern, replacement in [*model.replacements, (model.whitespace, " ")]:
        pieces, changed, cursor = [], [], 0
        for hit in pattern.finditer(value):
            pieces.append(value[cursor:hit.start()])
            changed.extend(mapped[cursor:hit.start()])
            pieces.append(replacement)
            changed.extend([(mapped[hit.start()][0], mapped[hit.end() - 1][1])] * len(replacement))
            cursor = hit.end()
        pieces.append(value[cursor:])
        changed.extend(mapped[cursor:])
        value, mapped = "".join(pieces), changed
    left, right = len(value) - len(value.lstrip()), len(value.rstrip())
    assert value.strip() == model.normalize(original)
    return value.strip(), mapped[left:right]


class DescriptionProcessor:
    def __init__(self, model):
        self.model, self.policy = model, model.segment_config
        p, c = self.policy["parser"], self.policy["context_policy"]
        self.html_detector = re.compile(p["detect_tags_regex"], re.I)
        self.entity_detector = re.compile(p["entity_regex"])
        self.structural = re.compile("(?:" + p["newline_regex"] + ")|(?:" + p["bullet_regex"] + ")")
        self.protected = [re.compile(pattern, re.I if i < len(p["protected_regexes"]) - 1 else 0)
                          for i, pattern in enumerate(p["protected_regexes"])]
        self.sentences = re.compile(p["sentence_boundary_regex"])
        self.adversatives = re.compile(p["adversative_clause_regex"], re.I)
        self.headings = {model.normalize(heading): section for section, headings in c["section_headings"].items() for heading in headings}
        heading_alternatives = "|".join(re.escape(h) for h in sorted(self.headings, key=len, reverse=True))
        self.heading_pattern = re.compile(r"(?<!\w)(?:" + heading_alternatives + r")\s*:", re.I)
        self.context_patterns = {key: re.compile(c[key], re.I) for key in ["company_subject_regex", "other_actor_regex", "qualification_prefix_regex", "compensation_sentence_regex"]}
        self.negation = [re.compile(r"(?<!\w)" + re.escape(model.normalize(a)) + r"(?!\w)") for a in c["negation_aliases"]]
        self.collaboration = [re.compile(r"(?<!\w)" + re.escape(model.normalize(a)) + r"(?!\w)") for a in c["collaboration_aliases"]]

    def process(self, raw):
        p, c = self.policy["parser"], self.policy["context_policy"]
        parsed = bool(self.html_detector.search(raw) or (p["decode_entities"] and self.entity_detector.search(raw)))
        if parsed:
            try:
                document = MappedHTML(raw, p).document()
            except (ValueError, AssertionError):
                document = SourceDocument(raw, issues=["HTML_PARSER_INCOMPLETE_RAW_RETAINED"])
        else:
            document = SourceDocument(raw)
        text = document.text
        protection = sorted((m.start(), m.end()) for pattern in self.protected for m in pattern.finditer(text))

        def protected(index):
            return any(a <= index < b for a, b in protection)

        events = [(m.start(), m.end(), "BOUNDARY", None) for m in self.structural.finditer(text)]
        events += [(m.start(), m.end(), "BOUNDARY", None) for m in self.sentences.finditer(text) if not protected(m.start())]
        events += [(m.start(), m.end(), "BOUNDARY", None) for m in self.adversatives.finditer(text) if not protected(m.start())]
        events += [(m.start(), m.end(), "HEADING", self.headings[self.model.normalize(m.group().rstrip(":"))])
                   for m in self.heading_pattern.finditer(text)]
        for m in re.finditer(r"[^\r\n\u2028\u2029]+", text):
            name = self.model.normalize(m.group().strip().rstrip(":"))
            if name in self.headings:
                events.append((m.start(), m.end(), "HEADING", self.headings[name]))
        events.sort(key=lambda event: (event[0], 0 if event[2] == "HEADING" else 1, -event[1]))
        units, cursor, section = [], 0, c["default_section"]

        def emit(start, end, kind="TEXT"):
            unit_text = text[start:end]
            value = self.model.normalize(unit_text)
            if not value:
                return
            actor, blocks = "POSITION_OR_UNSPECIFIED", []
            cue = self.model.fast_patterns[c["self_cue_term_set"]].search(value)
            hiring = any(value.startswith(self.model.normalize(a)) for a in c["hiring_cues"])
            if kind == "HEADING":
                blocks.append("SECTION_HEADING")
            elif section not in c["eligible_sections"] and not (section == "COMPANY" and hiring):
                actor = section
                blocks.append("SECTION_" + section)
            elif self.context_patterns["compensation_sentence_regex"].search(value):
                actor = "COMPENSATION"
                blocks.append("COMPENSATION_SENTENCE")
            elif self.context_patterns["company_subject_regex"].search(value) and not hiring:
                actor = "COMPANY_OR_CUSTOMER"
                blocks.append("COMPANY_SUBJECT")
            elif self.context_patterns["qualification_prefix_regex"].search(value):
                actor = "QUALIFICATION"
                blocks.append("QUALIFICATION_SENTENCE")
            # Other-actor and collaboration checks depend on the matched task,
            # and are applied to each candidate window instead of the paragraph.
            long = len(value) > self.policy["max_normalized_characters"]
            mapped = document.mapped(start, end)
            if not mapped:
                blocks.append("SOURCE_MAPPING_UNAVAILABLE")
            incomplete = (long and not blocks) or not mapped
            units.append(dict(index=len(units), text=unit_text, normalized=value, derived_start=start, derived_end=end,
                              raw_ranges=document.ranges(start, end), normalized_characters=len(value), section=section,
                              actor=actor, blocked_reasons=blocks, kind=kind, long=long, explicit_self=bool(cue),
                              status="RETAINED_LONG_UNRESOLVED" if incomplete else "PROCESSED",
                              mapping_available=mapped))

        for start, end, kind, next_section in events:
            if start < cursor:
                continue
            emit(cursor, start)
            if kind == "HEADING":
                section = next_section
                emit(start, end, "HEADING")
            cursor = end
        emit(cursor, len(text))
        legacy_long = []
        start = 0
        for match in self.model.splitter.finditer(raw):
            if len(self.model.normalize(raw[start:match.start()])) > self.policy["max_normalized_characters"]:
                legacy_long.append((start, match.start()))
            start = match.end()
        if len(self.model.normalize(raw[start:])) > self.policy["max_normalized_characters"]:
            legacy_long.append((start, len(raw)))
        unresolved = sum(any(unit["status"] != "PROCESSED" and any(a < end and b > start for a, b in unit["raw_ranges"])
                             for unit in units) for start, end in legacy_long)
        stats = dict(version=self.model.config["description_processing_version"], parser="HTMLParser" if parsed else "plain_text",
                     source_sha256=hashlib.sha256(raw.encode("utf-8")).hexdigest(), derived_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
                     units=len(units), retained_long_units=sum(u["long"] for u in units),
                     unresolved_units=sum(u["status"] != "PROCESSED" for u in units),
                     legacy_oversize_units_total=len(legacy_long), legacy_oversize_units_processed=len(legacy_long) - unresolved,
                     legacy_oversize_units_unresolved=unresolved, parser_issues=document.issues,
                     removed_source_ranges=document.removed, source_mapping_available=not any(not u["mapping_available"] for u in units),
                     incomplete=bool(document.issues or any(u["status"] != "PROCESSED" for u in units)),
                     dropped_oversize_units=0, raw_offset_unit="original_field_unicode_codepoints_half_open")
        return document, units, stats

    def candidates(self, unit, term_sets):
        """Bounded local views; all original units remain in the output trace."""
        if unit["blocked_reasons"]:
            return []
        value = unit["normalized"]
        if not unit["long"]:
            return [(0, len(value))]
        tasks = [k for k in term_sets if k.endswith("_tasks")]
        anchor = tasks[0] if tasks else term_sets[0]
        size = self.policy["long_unit_policy"]["window_characters"]
        result = set()
        for hit in self.model.fast_patterns[anchor].finditer(value):
            if self.policy["long_unit_policy"]["require_explicit_self_cue_or_task_led_clause"]:
                if not unit["explicit_self"] and not (tasks and self.model.fast_patterns[anchor].match(value)):
                    continue
            start = max(0, hit.start() - size // 2)
            end = min(len(value), start + size)
            if end == len(value):
                start = max(0, end - size)
            # Keep complete words at either edge, never manufacture a partial alias.
            if start and value[start - 1].isalnum():
                while start < hit.start() and value[start].isalnum():
                    start += 1
            if end < len(value) and value[end].isalnum():
                while end > hit.end() and value[end - 1].isalnum():
                    end -= 1
            result.add((start, end))
        return sorted(result)

    def blocked_window(self, unit, start, end, term_sets):
        value = unit["normalized"][start:end]
        # A bounded view must not lose a negation or actor earlier in this
        # same clause. Adversatives were already split into separate clauses.
        if any(pattern.search(unit["normalized"]) for pattern in self.negation):
            return "NEGATED_CLAUSE"
        tasks = [k for k in term_sets if k.endswith("_tasks")]
        if not tasks:
            return None
        hit = self.model.fast_patterns[tasks[0]].search(value)
        if not hit:
            return None
        prefix = unit["normalized"][:start + hit.start()]
        if self.context_patterns["other_actor_regex"].search(prefix):
            return "OTHER_ACTOR_TASK"
        for pattern in self.collaboration:
            collab = pattern.search(prefix)
            if collab:
                cue = self.model.fast_patterns[self.policy["context_policy"]["self_cue_term_set"]].search(prefix[:collab.start()])
                own_task_before_collaboration = self.model.fast_patterns[tasks[0]].search(prefix[:collab.start()])
                if not cue and not own_task_before_collaboration:
                    return "COLLABORATION_WITHOUT_OWN_TASK"
        return None

    def evidence(self, document, unit, term_set, alias, hit_start, hit_end):
        value, spans = normalized_spans(self.model, unit["text"])
        assert value == unit["normalized"]
        a, b = spans[hit_start][0], spans[hit_end - 1][1]
        derived_start, derived_end = unit["derived_start"] + a, unit["derived_start"] + b
        raw_ranges = document.ranges(derived_start, derived_end)
        if not raw_ranges or not document.mapped(derived_start, derived_end):
            raise ValueError("Cannot emit unmapped automatic evidence")
        first, last = raw_ranges[0][0], raw_ranges[-1][1]
        maximum = self.model.config["proposed_output_contract"]["evidence_excerpt_max_characters"]
        lo = max(0, first - 40)
        if last - lo > maximum:
            lo = first
        hi = min(len(document.raw), lo + maximum)
        return dict(field="description", term_set_id=term_set, matched_alias=alias, segment_index=unit["index"],
                    excerpt=document.raw[lo:hi], raw_excerpt_start=lo, raw_excerpt_end=hi,
                    raw_match_ranges=raw_ranges, raw_offset_unit="original_field_unicode_codepoints_half_open",
                    normalized_start=hit_start, normalized_end=hit_end, normalized_coordinate_space="normalized_segment",
                    derived_start=derived_start, derived_end=derived_end, derived_coordinate_space="parser_text",
                    derived_matched_text=document.text[derived_start:derived_end], mapping_status="MAPPED_TO_RAW",
                    excerpt_covers_all_match_ranges=last <= hi, section=unit["section"], actor=unit["actor"])
