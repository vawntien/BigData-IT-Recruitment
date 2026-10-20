"""Audit all frozen A05 evidence; write recommendations, never manual labels."""
import argparse
import collections
import csv
import hashlib
import json
from pathlib import Path

from a05_recommendation_candidate import advise, VERSION
from apply_a04_decisions import read_sheet
from tv2_csv import ROOT, sha256, csv_rows


def run(output):
    out=Path(output)
    if out.exists() or not out.resolve().is_relative_to(ROOT):
        raise ValueError('Use a new repository output directory')
    workbook=ROOT/'tmp/a05_approval_queue_20261019/a05_final_approval_pending.xlsx'
    frozen=ROOT/'data/analytics/a05_development_v0_1_2_20261014/technical_skill_evidence.jsonl'
    dictionary=ROOT/'config/tech_skills.json'
    assignment=Path('C:/Ke_hoach_BigData_Tuyen_dung_CNTT_3_nguoi.xlsm')
    protected=[workbook,frozen,dictionary,ROOT/'src/tech_skill_extractor.py',ROOT/'src/a05_spark.py',
               ROOT/'data/analytics/a05_spark_parity_20261019/run02/parity_manifest.json',assignment]
    before={str(p):sha256(p) for p in protected}
    rows=read_sheet(workbook,'EVIDENCE_661')['rows']
    additions=read_sheet(workbook,'BO_SUNG_5')['rows']
    ev=[json.loads(s) for s in frozen.read_text(encoding='utf-8').splitlines()]
    index={e['evidence_id']:e for e in ev}
    assert len(index)==len(rows)==661 and len(additions)==5
    wanted={str(e['job_id']) for e in ev}|{r['job_id'] for r in additions}
    raw={str(r['job_id']):r for r in csv_rows(ROOT/'data/raw/postings.csv') if str(r['job_id']) in wanted}
    assert set(raw)==wanted
    def check(e):
        text=raw[str(e['job_id'])]['description']
        assert hashlib.sha256(text.encode()).hexdigest()==e['source_text_sha256']
        assert text[e['raw_excerpt_start']:e['raw_excerpt_end']]==e['excerpt']
        assert ''.join(text[a:b] for a,b in e['raw_match_ranges'])==e['matched_text']
        return text
    recommendations=[]
    for r in rows:
        e=index[r['evidence_id']];text=check(e)
        assert r['original_evidence_quote']==e['excerpt']
        assert r['source_description_sha256']==e['source_text_sha256']
        d=advise(e,text);kind=d['kind']
        action='CHUA_RO' if kind is None else 'LOAI' if kind=='EXCLUDE' else 'NHAN' if not e['accepted'] else 'GIU_NHAN' if kind==e['mention_type'] else 'SUA_LOAI'
        recommendations.append(dict(record_key=e['evidence_id'],record_type='FROZEN_EVIDENCE',job_id=e['job_id'],
            skill_code=e['skill_code'],source_field=e['source_field'],source_text_sha256=e['source_text_sha256'],
            raw_ranges=json.dumps(e['raw_match_ranges']),matched_text=e['matched_text'],quote=e['excerpt'],
            full_title_for_context=raw[str(e['job_id'])]['title'],machine_type=e['mention_type'],machine_accepted=e['accepted'],
            previous_proposal=r['pending_action'],recommended_action=action,recommended_type=kind if kind not in (None,'EXCLUDE') else '',
            reason_code=d['rule'],reason=REASONS[d['rule']],decision_quote=d['decision_quote'],confidence=d['confidence'],
            proposal_version=VERSION,status='MACHINE_RECOMMENDATION_NOT_APPROVED',final_decision='',reviewer='',reviewed_date=''))
    for r in additions:
        text=raw[r['job_id']]['description'];a,b=json.loads(r['original_raw_ranges'])[0]
        assert text[a:b]==r['alias'] and r['original_evidence_quote'] in text
        assert hashlib.sha256(text.encode()).hexdigest()==r['source_description_sha256']
        # These proposed spans sit in glued tokens. Do not silently relax word
        # boundaries to reproduce the five review suggestions.
        recommendations.append(dict(record_key=r['approval_key'],record_type='ADDITIONAL_CANDIDATE',job_id=int(r['job_id']),
            skill_code=r['proposed_skill'],source_field='postings.description',source_text_sha256=r['source_description_sha256'],
            raw_ranges=r['original_raw_ranges'],matched_text=text[a:b],quote=r['original_evidence_quote'],
            full_title_for_context=raw[r['job_id']]['title'],machine_type='',machine_accepted=False,previous_proposal=r['pending_action'],
            recommended_action='CHUA_RO',recommended_type='',reason_code='GLUED_TOKEN_BOUNDARY',
            reason='Tên kỹ năng có trong chuỗi dính chữ; range/quote đúng nhưng không đạt ranh giới từ v0.1.2. Giữ ứng viên riêng; chưa tự nới alias hoặc thêm vào bridge.',
            decision_quote=text[max(0,a-35):b+40],confidence='Chưa đủ',proposal_version=VERSION,
            status='MACHINE_RECOMMENDATION_NOT_APPROVED',final_decision='',reviewer='',reviewed_date=''))
    assert len({r['record_key'] for r in recommendations})==666
    assert all(not r[k] for r in recommendations for k in ('final_decision','reviewer','reviewed_date'))
    out.mkdir(parents=True,exist_ok=False)
    def save(name,data):
        with (out/name).open('x',encoding='utf-8-sig',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(recommendations[0]));w.writeheader();w.writerows(data)
    save('recommendations_666.csv',recommendations)
    unknown=[r for r in recommendations if r['recommended_action']=='CHUA_RO']
    save('unclear_only.csv',unknown)
    changed=[r for r in recommendations if r['record_type']=='FROZEN_EVIDENCE' and r['recommended_action'] not in ('CHUA_RO','GIU_NHAN')]
    save('proposed_changes.csv',changed)
    assert all(sha256(Path(p))==h for p,h in before.items())
    manifest=dict(status='RECOMMENDATIONS_ONLY_NOT_ACCEPTED',version=VERSION,
                  records=666,evidence=661,additions=5,raw_jobs_checked=len(raw),source_checks_passed=666,
                  actions=dict(collections.Counter(r['recommended_action'] for r in recommendations)),
                  unclear_reasons=dict(collections.Counter(r['reason_code'] for r in unknown)),
                  proposed_changes=len(changed),
                  transition_counts=dict(collections.Counter(r['machine_type']+' -> '+(r['recommended_type'] or r['recommended_action']) for r in recommendations if r['record_type']=='FROZEN_EVIDENCE')),
                  protected_hashes=before,protected_inputs_unchanged=True,manual_labels_created=False,
                  extraction_or_spark_run=False,production_ready_input='BLOCKED_D06_FULL',
                  method='Deterministic conservative context audit of each frozen hit; independent of prior proposed decisions. Not a new extraction run or accuracy measurement.')
    (out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in manifest.items() if k not in ('protected_hashes','transition_counts')},ensure_ascii=False))


REASONS={
    'DISTINCT_REACT_PRODUCT_OR_PACKAGE':'Hit nằm trong React Native hoặc tên package; không suy React độc lập.',
    'AZURE_DEVOPS_NOT_AZURE_CLOUD':'Tên sản phẩm Azure DevOps không đủ chứng minh Azure cloud tại hit này.',
    'NOSQL_NOT_SQL':'SQL là phần của no-SQL, không phải kỹ năng SQL độc lập.',
    'OBJECTIVE_C_NOT_C':'Hit nằm trong Objective-C, không phải C độc lập.',
    'ORDINARY_WORD_OR_IDENTIFIER':'Ký tự/từ thuộc mã định danh, từ thông thường hoặc sản phẩm khác.',
    'OTHER_ORACLE_PRODUCT_NOT_DATABASE':'Sản phẩm Oracle cloud/ERP/reporting không chứng minh Oracle Database.',
    'ORACLE_PRODUCT_UNSPECIFIED':'Tên Oracle chưa chỉ rõ Database; không suy sản phẩm từ thương hiệu.',
    'HISTORICAL_COMPARISON_NOT_REQUIREMENT':'Hit trong mệnh đề predates là so sánh, không tự là yêu cầu/nhiệm vụ.',
    'EXISTING_NEGATION_OR_OUTSIDE_SCOPE':'Evidence đã có trạng thái phủ định hoặc ngoài phạm vi vị trí; giữ loại khỏi bridge.',
    'RAW_MAPPING_UNAVAILABLE':'Chưa có ánh xạ nguồn tin cậy.',
    'ROLE_LABEL_WITHOUT_REQUIREMENT_OR_TASK':'Tên vai trò không có căn cứ yêu cầu/ưu tiên/nhiệm vụ tại unit này.',
    'ROLE_INTRO_NOT_TASK':'Working as chỉ giới thiệu vai trò, không mô tả nhiệm vụ cụ thể.',
    'MIXED_UNSEGMENTED_SCOPE':'Unit trộn nhiệm vụ và yêu cầu; không truyền cue qua ranh giới chưa xác định.',
    'LOCAL_IS_A_PLUS':'Cue is/are a plus cục bộ hỗ trợ PREFERRED, ưu tiên hơn heading required chung.',
    'LOCAL_REQUIRED_SUFFIX':'Suffix required/mandatory/essential gắn sau hit hỗ trợ REQUIRED.',
    'PRECEDING_PREFERENCE_HEADING':'Heading ưu tiên đứng trước hit và gần unit; không dùng heading xuất hiện sau hit.',
    'ALIAS_CONTEXT_NOT_PROVEN':'Ranh giới alias chưa đủ xác nhận nghĩa công nghệ của hit này.',
    'LONG_UNIT_CUE_SCOPE_NOT_PROVEN':'Nội dung được giữ nguyên nhưng scope cue trong unit dài chưa chứng minh; không bỏ text.',
    'LOCAL_PREFERENCE_CUE':'Unit có cue ưu tiên; cần hiểu đây là đề xuất theo scope tự động, không nhãn tay.',
    'PREFERRED_SECTION':'Hit nằm trong section ưu tiên, không tự là yêu cầu bắt buộc.',
    'TASK_SECTION_AND_ACTION':'Section nhiệm vụ/vai trò có động từ hành động thực tế, không chỉ tên chức danh.',
    'REQUIREMENT_CUE_OR_SECTION':'Có cue yêu cầu/kinh nghiệm hoặc section yêu cầu trước hit.',
    'POSITION_AND_ACTION':'Có chủ thể vị trí và hành động dùng công nghệ.',
    'INSUFFICIENT_LOCAL_SCOPE':'Chưa đủ căn cứ tại hit để chốt REQUIRED/PREFERRED/TASK.',
}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True)
    args=p.parse_args();run(args.output)
