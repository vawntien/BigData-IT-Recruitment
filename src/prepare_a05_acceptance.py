"""Build a read-only human acceptance queue from the existing proposed workbook."""
import argparse
import collections
import json
from pathlib import Path
from apply_a04_decisions import read_sheet
from audit_a05_review import run as audit
from tv2_csv import ROOT, write_csv, write_json


def prepare(workbook, output):
    workbook, output=Path(workbook),Path(output)
    if output.exists():raise FileExistsError('Choose a new output')
    result=audit(workbook,output)
    if not result['source_validation_passed']:raise ValueError('Resolve evidence source mismatches first')
    rows=read_sheet(workbook,'Review 661 evidence')['rows']
    additions=read_sheet(workbook,'Bo sot de nghi')['rows']
    queue=[]
    for r in rows:
        queue.append(dict(evidence_id=r['evidence_id'],job_id=r['job_id'],
            source_skill=r['Skill nguồn'],source_type=r['Loại nguồn'],machine_accepted=r['Máy nhận'],
            proposal=r['Quyết định đề nghị'],proposed_skill=r['Skill đề nghị'],proposed_type=r['Loại đề nghị'],
            reason=r['Lý do'],matched_text=r['Matched text nguồn'],raw_ranges=r['Raw ranges nguồn'],
            source_quote=r['Quote nguyên văn'],priority='UNRESOLVED' if r['Quyết định đề nghị']=='CHUA_RO' else 'CHANGE_OR_NEW' if r['Quyết định đề nghị']!='GIU_NHAN' else 'CONFIRM_KEEP',
            existing_reviewer=r['Người duyệt'],existing_reviewed_date=r['Ngày duyệt'],
            final_decision='',final_skill='',final_mention_type='',reviewer='',reviewed_date='',review_note=''))
    fields=list(queue[0])
    write_csv(output/'manual_acceptance_queue.csv',queue,fields,exclusive=True,bom=True)
    unclear=[r for r in queue if r['proposal']=='CHUA_RO']
    write_csv(output/'chua_ro.csv',unclear,fields,exclusive=True,bom=True)
    changed=[r for r in queue if r['proposal']!='GIU_NHAN']
    write_csv(output/'changes_requiring_confirmation.csv',changed,fields,exclusive=True,bom=True)
    write_csv(output/'additional_mentions_pending.csv',[
        dict(job_id=r['job_id'],proposed_skill=r['Skill đề nghị'],alias=r['Alias'],raw_start=r['Raw start'],raw_end=r['Raw end'],
             source_quote=r['Quote nguồn'],existing_reviewer=r['Người duyệt'],existing_reviewed_date=r['Ngày duyệt'],
             final_decision='',reviewer='',reviewed_date='',review_note='') for r in additions],
        ['job_id','proposed_skill','alias','raw_start','raw_end','source_quote','existing_reviewer','existing_reviewed_date','final_decision','reviewer','reviewed_date','review_note'],exclusive=True,bom=True)
    counts=collections.Counter(r['proposal'] for r in queue)
    write_csv(output/'acceptance_summary.csv',[dict(category=k,proposed_evidence=n,acceptance_status='PENDING_HUMAN_REVIEW',reviewer='',reviewed_date='') for k,n in sorted(counts.items())]+[
        dict(category='ADDITIONAL_MENTIONS',proposed_evidence=len(additions),acceptance_status='PENDING_HUMAN_REVIEW',reviewer='',reviewed_date='')],
        ['category','proposed_evidence','acceptance_status','reviewer','reviewed_date'],exclusive=True,bom=True)
    summary=dict(status='PROPOSED_NOT_APPROVED',requested_filename_present=(workbook.parent/'a05_skill_review_decisions.xlsx').exists(),
        actual_workbook=str(workbook),workbook_sha256=result['workbook_sha256'],source_validation_passed=True,
        proposed_evidence=len(queue),unclear=len(unclear),changed_or_unclear=len(changed),additional_mentions=len(additions),
        all_proposals_require_human_confirmation=True,decisions_applied=False,reviewer_and_dates_created=False,proposal_counts=dict(counts))
    write_json(output/'acceptance_manifest.json',summary,exclusive=True)
    text='# A05 — bảng tổng hợp chờ nghiệm thu\n\nTrạng thái PROPOSED_NOT_APPROVED. File tên yêu cầu chưa có; đã đọc workbook thực tế có hash trong manifest. Không sửa workbook, extractor/dictionary hoặc nhãn.\n\n'
    text+=f"{len(queue)} evidence và {len(additions)} đề nghị bổ sung cần xác nhận; {len(unclear)} CHUA_RO; {len(changed)} đề nghị khác GIU_NHAN. GIU_NHAN cũng chưa được tự duyệt. Các con số là rà soát mẫu phát triển, không là accuracy hoặc thống kê IT.\n\n"
    text+='Ưu tiên đọc chua_ro.csv, changes_requiring_confirmation.csv và additional_mentions_pending.csv; mở đúng job_id/evidence_id trong nguồn. Chốt final_decision, skill, mention type (REQUIRED/PREFERRED/TASK hoặc loại trừ/chưa rõ), lý do và quote/ranges; chỉ người duyệt điền reviewer/ngày. Không suy nhãn skill từ nhãn nghề A04. Giữ CHUA_RO nếu chứng cứ chưa đủ. Sau phê duyệt, lập thay đổi riêng có version/test, không tự áp vào v0.1.2.\n\n'
    text+='| job_id | evidence_id | Skill | Lý do đề nghị CHUA_RO |\n| --- | --- | --- | --- |\n'
    for r in unclear:text+='| '+ ' | '.join(str(r[k]).replace('|','/').replace('\n',' ') for k in ['job_id','evidence_id','source_skill','reason'])+' |\n'
    (output/'acceptance_summary.md').write_text(text,encoding='utf-8')
    return summary


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--workbook',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();prepare(a.workbook,a.output)
