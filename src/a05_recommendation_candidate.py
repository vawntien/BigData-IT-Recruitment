"""Proposal-only context audit of source-mapped evidence, candidate 0.1.0.

Not imported by the extractor/Spark pipeline. No job IDs or approved labels.
This conservative layer can withhold a recommendation; it cannot approve one.
"""
import re

VERSION = 'a05-context-recommendations-0.1.0'
HEADINGS = re.compile(
    r'additional nice[- ]to[- ]haves|nice[- ]to[- ]haves?|bonus points(?: if)?|'
    r'desired skills(?: & experience)?|preferred (?:skills|qualifications|experience)|'
    r'skills preferred|plusses|pluses|'
    r'minimum qualifications(?: required)?|required skills(?: & experience)?|'
    r'skills required|must haves?|requirements|qualifications|'
    r'responsibilities|essential duties|job duties', re.I)
PREFERRED = re.compile(r'nice[- ]to[- ]have|bonus|desired|preferred|plusses|pluses',re.I)
REQ = re.compile(r'\b(?:experience|knowledge|proficien\w*|familiar\w*|expertise|ability|must|required|skills?|understanding|competenc\w*)\b',re.I)
TASK = re.compile(r'\b(?:develop\w*|build\w*|implement\w*|maintain\w*|configur\w*|deploy\w*|design\w*|use|using|work with|write|writing|code|coding|integrat\w*|administer\w*|monitor\w*|analy[sz]\w*|support\w*|stay current)\b',re.I)
ROLE = re.compile(r'(?:developer|engineer|architect|programmer|analyst|administrator|scientist)',re.I)


def advise(e, raw):
    """Return proposed kind (None = CHUA_RO), rule, justification quote, certainty.

    EXCLUDE means only the targeted skill mapping at this evidence range.
    Evidence raw coordinates remain untouched; cue strings are separate derived text.
    """
    ranges=e['raw_match_ranges']; a,b=ranges[0][0],ranges[-1][1]
    value=e['sentence_text']; i,j=e['normalized_start'],e['normalized_end']
    # Frozen normalized offsets index normalized sentence, not source text.
    value=' '.join(value.lower().split())
    # NFC differences are possible; raw products/ranges are always the primary anchor.
    before,after=raw[max(0,a-100):a],raw[b:b+100]
    code=e['skill_code']; matched=raw[a:b]
    def result(kind,rule,quote,confidence='Cao'):
        return dict(kind=kind,rule=rule,decision_quote=quote,confidence=confidence)
    if code=='REACT' and re.match(r'\s+native\b|[-.]\s*(?:dom|jss)\b',after,re.I):
        return result('EXCLUDE','DISTINCT_REACT_PRODUCT_OR_PACKAGE',matched+after[:30])
    if code=='AZURE' and re.match(r'\s+devops\b',after,re.I):
        return result('EXCLUDE','AZURE_DEVOPS_NOT_AZURE_CLOUD',matched+after[:35])
    if code=='SQL' and re.search(r'no[- ]?$',before,re.I):
        return result('EXCLUDE','NOSQL_NOT_SQL',before[-8:]+matched)
    if code=='C' and re.search(r'objective[- ]*$',before,re.I):
        return result('EXCLUDE','OBJECTIVE_C_NOT_C',before[-15:]+matched)
    if code in {'C','R','GO'} and e['mention_type']=='AMBIGUOUS_ALIAS':
        if re.search(r'\([cr]\)|\br-\d|\bgo-live\b|\bobjective[- ]c\b',raw[max(0,a-15):b+20],re.I):
            return result('EXCLUDE','ORDINARY_WORD_OR_IDENTIFIER',raw[max(0,a-15):b+20])
    if code=='ORACLE_DB' and matched.lower()=='oracle':
        if re.match(r'\s+(?:cloud|e-business|financial|reporting)',after,re.I):
            return result('EXCLUDE','OTHER_ORACLE_PRODUCT_NOT_DATABASE',matched+after[:60])
        return result(None,'ORACLE_PRODUCT_UNSPECIFIED',matched+after[:60],'Chưa đủ')
    if re.search(r'\bpredates\b[^.;!?]{0,90}$',before,re.I):
        return result('EXCLUDE','HISTORICAL_COMPARISON_NOT_REQUIREMENT',before+matched)
    if e['mention_type'] in {'NEGATED','COMPANY_ONLY','OUTSIDE_POSITION'}:
        return result('EXCLUDE','EXISTING_NEGATION_OR_OUTSIDE_SCOPE',e['excerpt'])
    if e.get('mapping_status')!='MAPPED_TO_RAW':
        return result(None,'RAW_MAPPING_UNAVAILABLE',e['excerpt'],'Chưa đủ')
    # Role labels alone are not task evidence. Work on the frozen unit, not title field.
    if ROLE.search(value) and not REQ.search(value) and not TASK.search(value):
        return result(None,'ROLE_LABEL_WITHOUT_REQUIREMENT_OR_TASK',e['excerpt'],'Chưa đủ')
    if re.search(r'\bworking as\b',value) and not re.match(r'(?:\d+\+? years? (?:of )?)?experience working as\b',value):
        return result(None,'ROLE_INTRO_NOT_TASK',e['excerpt'],'Chưa đủ')
    # Keep mixed units unresolved rather than propagating a far-away heading/cue.
    if len(value)>500 and 'MIXED_TASK_AND_QUALIFICATION' in e.get('rule_id',''):
        return result(None,'MIXED_UNSEGMENTED_SCOPE',e['excerpt'],'Chưa đủ')
    # A suffix with an explicit preference qualifies the preceding coordinated list.
    suffix=after.split('\n',1)[0]
    if re.match(r'[^.!?;:]{0,65}\b(?:is|are) (?:a |an )?plus\b',suffix,re.I):
        return result('PREFERRED','LOCAL_IS_A_PLUS',matched+suffix[:85])
    if re.match(r'\s*(?:is |are )?(?:required|mandatory|essential)\b',after,re.I):
        return result('REQUIRED','LOCAL_REQUIRED_SUFFIX',matched+after[:60])
    # A heading must precede the hit, and its scope must include this frozen unit.
    unit_start=e.get('raw_excerpt_start',a)
    prefix=raw[:a]
    headings=list(HEADINGS.finditer(prefix))
    last=headings[-1] if headings else None
    section=e.get('section','')
    if last and last.start()>=max(0,unit_start-250):
        h=last.group()
        if PREFERRED.search(h):
            return result('PREFERRED','PRECEDING_PREFERENCE_HEADING',h+' … '+matched,'Vừa')
        if re.search(r'responsibilities|duties',h,re.I):section='TASK'
        elif not re.search(r'\bbusiness\s*$',prefix[max(0,last.start()-20):last.start()],re.I):
            section='REQUIREMENTS'
    # Alias ambiguity is not cured just by a candidate/task cue.
    if e['mention_type']=='AMBIGUOUS_ALIAS':
        return result(None,'ALIAS_CONTEXT_NOT_PROVEN',e['excerpt'],'Chưa đủ')
    # Use cues in the immediate source clause; retain larger units as uncertain.
    if len(value)>500:
        return result(None,'LONG_UNIT_CUE_SCOPE_NOT_PROVEN',e['excerpt'],'Chưa đủ')
    next_heading = next((h for h in HEADINGS.finditer(value) if h.start() >= j), None)
    if next_heading:
        value = value[:next_heading.start()]
    if re.search(r'\b(?:is a plus|preferred|desired|preferably|nice[- ]to[- ]have|bonus)\b',value):
        return result('PREFERRED','LOCAL_PREFERENCE_CUE',e['excerpt'],'Vừa')
    if section=='PREFERRED':
        return result('PREFERRED','PREFERRED_SECTION',e['excerpt'],'Vừa')
    if section in {'TASK','ROLE'} and TASK.search(value) and not re.match(r'(?:(?:strong|good|proven|extensive|deep|solid) )?(?:experience|knowledge|familiar|ability|proficien|expertise|understanding)',value):
        return result('TASK','TASK_SECTION_AND_ACTION',e['excerpt'],'Vừa')
    if REQ.search(value) or section=='REQUIREMENTS':
        return result('REQUIRED','REQUIREMENT_CUE_OR_SECTION',e['excerpt'],'Vừa')
    if TASK.search(value) and (section in {'TASK','ROLE'} or re.search(r'\b(?:you|this role|this position|responsible)\b',value)):
        return result('TASK','POSITION_AND_ACTION',e['excerpt'],'Vừa')
    return result(None,'INSUFFICIENT_LOCAL_SCOPE',e['excerpt'],'Chưa đủ')
