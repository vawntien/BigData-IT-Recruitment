"""Decision-support workbook only; no skill extraction, approval or pipeline run."""
import collections
import csv
import hashlib
import json
from pathlib import Path
import sys
import zipfile
from xml.sax.saxutils import escape

from apply_a04_decisions import read_sheet
from audit_a05_review import reconcile
from tv2_csv import ROOT,sha256

FINAL=['final_decision','final_skill_code','final_mention_type','final_raw_ranges','reviewer','reviewed_date','final_note']


def column(n):
    result=''
    while n:n,r=divmod(n-1,26);result=chr(65+r)+result
    return result


def write_workbook(path,sheets):
    """Plain OOXML, literal text cells, no macros/formulas/external dependencies."""
    ns='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
    with zipfile.ZipFile(path,'x',zipfile.ZIP_DEFLATED) as z:
        types='<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
        types+=''.join(f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' for i in range(1,len(sheets)+1))+'</Types>'
        z.writestr('[Content_Types].xml',types)
        z.writestr('_rels/.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
        z.writestr('xl/workbook.xml',f'<workbook xmlns="{ns}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>'+''.join(f'<sheet name="{name}" sheetId="{i}" r:id="rId{i}"/>' for i,(name,_) in enumerate(sheets,1))+'</sheets></workbook>')
        rels='<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'+''.join(f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>' for i in range(1,len(sheets)+1))+f'<Relationship Id="rId{len(sheets)+1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>'
        z.writestr('xl/_rels/workbook.xml.rels',rels)
        z.writestr('xl/styles.xml',f'<styleSheet xmlns="{ns}"><fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="11"/><color rgb="FFFFFFFF"/><name val="Calibri"/></font></fonts><fills count="4"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FF24556D"/><bgColor indexed="64"/></patternFill></fill><fill><patternFill patternType="solid"><fgColor rgb="FFFFF2CC"/><bgColor indexed="64"/></patternFill></fill></fills><borders count="1"><border/></borders><cellStyleXfs count="1"><xf/></cellStyleXfs><cellXfs count="3"><xf fontId="0" fillId="0" borderId="0" xfId="0"><alignment vertical="top" wrapText="1"/></xf><xf fontId="1" fillId="2" borderId="0" xfId="0" applyFill="1"><alignment wrapText="1"/></xf><xf fontId="0" fillId="3" borderId="0" xfId="0" applyFill="1"><alignment vertical="top" wrapText="1"/></xf></cellXfs><cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>')
        for i,(name,rows) in enumerate(sheets,1):
            headers=list(rows[0]);data=[headers]+[[r.get(k,'') for k in headers] for r in rows]
            xml=f'<worksheet xmlns="{ns}"><sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews><cols>'
            for c,key in enumerate(headers,1):
                width=65 if any(s in key for s in ['quote','context','reason','handling','description','note','finding']) else 24
                xml+=f'<col min="{c}" max="{c}" width="{width}" customWidth="1"/>'
            xml+='</cols><sheetData>'
            for n,row in enumerate(data,1):
                xml+=f'<row r="{n}">'
                for c,value in enumerate(row,1):
                    cell=f'{column(c)}{n}';style=1 if n==1 else 2 if headers[c-1] in FINAL else 0
                    if isinstance(value,bool):xml+=f'<c r="{cell}" s="{style}" t="b"><v>{int(value)}</v></c>'
                    else:
                        text='' if value is None else str(value)
                        if len(text)>32767:raise ValueError('Excel cell too long; do not truncate source')
                        xml+=f'<c r="{cell}" s="{style}" t="inlineStr"><is><t xml:space="preserve">{escape(text)}</t></is></c>'
                xml+='</row>'
            xml+='</sheetData>'+f'<autoFilter ref="A1:{column(len(headers))}{len(data)}"/>'
            if 'final_decision' in headers:
                c=column(headers.index('final_decision')+1)
                xml+=f'<dataValidations count="1"><dataValidation type="list" allowBlank="1" sqref="{c}2:{c}{len(data)}"><formula1>"CONFIRM_PROPOSAL,OVERRIDE_PROPOSAL,CHUA_RO"</formula1></dataValidation></dataValidations>'
            z.writestr(f'xl/worksheets/sheet{i}.xml',xml+'</worksheet>')


def assessment(r,source):
    p=r['Quyết định đề nghị'];skill=r['Skill nguồn'];job=str(r['job_id']);eid=r['evidence_id']
    if p=='GIU_NHAN':return 'KEEP_PENDING_CONFIRMATION','Đề nghị giữ nhãn đã có; chưa được người duyệt xác nhận.'
    if p=='CHUA_RO':
        reason=r['Lý do']
        if 'React Native' in reason and job=='3898171523':
            return 'REVIEW_SCOPE_OR_POLICY','Chốt React Native có thuộc REACT hay mã riêng; không suy từ dependency. Hit này là React trong React Native; phân biệt hit React đứng riêng 28a90f6b… cùng câu.'
        if 'React-DOM' in reason:return 'REVIEW_SCOPE_OR_POLICY','Chốt có gộp react-Dom/react-jss vào họ REACT không; đã có mention React trực tiếp khác, không tự nhân hoặc suy nhãn từ package.'
        if job=='3901347312':return 'REVIEW_SCOPE_OR_POLICY','Đọc cả danh sách công nghệ và câu “knowledge which predates …”; không tự coi mốc so sánh là REQUIRED cho framework đó.'
        if job=='3900960573':return 'REVIEW_SCOPE_OR_POLICY','Câu giới thiệu tên vai trò chưa xác định REQUIRED/PREFERRED/TASK của hit; kiểm riêng các evidence Power BI khác, không lấy chúng gán loại cho hit này.'
        return 'REVIEW_SCOPE_OR_POLICY','Tên công nghệ trong role/title: xác nhận cách xử lý mention title và phạm vi loại đề cập; không suy REQUIRED/TASK chỉ từ chức danh.'
    if p=='LOAI' and skill in ['AZURE','ORACLE_DB']:
        return 'REVIEW_SCOPE_OR_POLICY','Có thể xác minh tên sản phẩm gốc; người duyệt chốt ranh giới Azure DevOps/Azure cloud hoặc Oracle ERP/cloud/Oracle Database. Chưa đủ chứng cứ của sản phẩm mục tiêu không có nghĩa cả tin không dùng sản phẩm đó.'
    if p=='SUA_KY_NANG':return 'REVIEW_SCOPE_OR_POLICY','Nguồn có Microsoft SQL ServerCisco…; tên SQL Server có căn cứ nhưng phải chốt code/range mới và ranh giới dính chữ; giữ range gốc, không áp sửa tự động.'
    if job=='3887916439' and skill=='SQL' and p=='NHAN':
        assert 'Additional Nice-to-Haves' in source
        return 'PROPOSAL_CONFLICT','Hai hit SQL nằm dưới Additional Nice-to-Haves, trái đề nghị REQUIRED. Đề nghị người duyệt xem PREFERRED; không tự điền loại cuối.'
    if job=='3898171523' and skill in ['PYTHON','MYSQL'] and p=='SUA_LOAI':
        assert 'is a plus' in r['Quote nguyên văn']
        return 'PROPOSAL_CONFLICT','Cue is a plus gắn với Python hoặc MySQL; đề nghị REQUIRED có bằng chứng trái chiều. Cần người duyệt chốt PREFERRED/khác, không lan heading required qua cue cục bộ.'
    if eid.startswith('eb5cf3c9'):return 'REVIEW_SCOPE_OR_POLICY','Heavily in Azure cloud xác nhận môi trường công nghệ nhưng chưa giao hành động cụ thể cho hit này; cần chốt TASK hay loại khác.'
    if job=='3903487406' and skill in ['REACT','ANGULAR']:
        return 'REVIEW_SCOPE_OR_POLICY','Danh sách bị dính/lặp cạnh CI/CD a plus và WorkDay/eTime huge plus; xác nhận phạm vi cue trước khi gán REQUIRED.'
    if job=='3903458524' and skill=='POWER_BI':return 'REVIEW_SCOPE_OR_POLICY','MUST HAVE và cụm Power BI and Azure experience is a plus chung một đoạn; người duyệt phân xử phạm vi is a plus, không mặc định chỉ áp Azure.'
    if job=='3901938680' and skill=='DOTNET':return 'REVIEW_SCOPE_OR_POLICY','Stay current with … .NET Core là nhiệm vụ cập nhật kiến thức; chốt có thuộc TASK theo định nghĩa review hay loại khác, không suy nhiệm vụ xây .NET.'
    if p=='LOAI':return 'EVIDENCE_SUPPORTS_PROPOSAL','Range/ngữ cảnh ủng hộ loại hit chữ thường/mã pháp lý/Objective-C/NoSQL; chỉ kết luận về hit này, không về mọi kỹ năng của job. Chờ người duyệt ký.'
    return 'EVIDENCE_SUPPORTS_PROPOSAL','Tên công nghệ và cue nhiệm vụ/kinh nghiệm/ưu tiên trong nguồn ủng hộ đề nghị; đọc quote, range và context trước khi ký. Đây là nhận xét hỗ trợ, không phải gold label hoặc quyết định đã duyệt.'


def write_reading_notes(out,rows):
    text='# A05 — 19 evidence CHUA_RO / 9 tin, chờ người duyệt\n\n'
    text+='Đề nghị xử lý là hỗ trợ rà soát, không phải nhãn cuối. Offset là Unicode codepoint nửa mở của description nguồn.\n\n'
    for i,r in enumerate(rows,1):
        text+=f"## {i}. {r['job_id']} — {r['source_skill']}\n\nEvidence ID: `{r['evidence_id']}`. Range: `{r['original_raw_ranges']}`. Source SHA-256: `{r['source_description_sha256']}`.\n\n"
        text+='Evidence nguyên văn:\n\n'+'\n'.join('> '+line for line in r['original_evidence_quote'].splitlines())+'\n\n'
        text+='Lý do chưa rõ trong workbook: '+r['original_reason']+'\n\nĐề nghị xử lý (chưa duyệt): '+r['suggested_handling']+'\n\n'
    (out/'chua_ro_19.md').write_text(text,encoding='utf-8')


def main():
    out=ROOT/'tmp/a05_final_acceptance_20261019';out.mkdir(parents=True,exist_ok=False)
    workbook=ROOT/'data/analytics/a05_review/A05_Review_661_Evidence.xlsx'
    base=ROOT/'data/analytics/a05_development_v0_1_2_20261014'
    snapshot=ROOT/'data/analytics/a04_taxonomy_v0_2_2_20261014/baseline/source_rows.json'
    protected=[workbook,snapshot,base/'technical_skill_evidence.jsonl',base/'skill_source_processing.jsonl',base/'job_skill_technical.csv',ROOT/'config/tech_skills.json',ROOT/'src/tech_skill_extractor.py',ROOT/'src/a05_spark.py']
    before={p.as_posix():sha256(p) for p in protected}
    parity=json.loads((ROOT/'data/analytics/a05_spark_parity_20261019/run02/parity_manifest.json').read_text(encoding='utf-8'))
    assert sha256(snapshot)==parity['source_snapshot_sha256']
    prior=json.loads((ROOT/'data/analytics/tv2_readiness_20261019/a05_acceptance/review_audit.json').read_text(encoding='utf-8'))
    assert sha256(workbook)==prior['workbook_sha256']
    sources=json.loads(snapshot.read_text(encoding='utf-8'));jobs={str(r['job_id']):r for a in sources.values() for r in a}
    evidence=[json.loads(x) for x in (base/'technical_skill_evidence.jsonl').read_text(encoding='utf-8').splitlines()]
    index={e['evidence_id']:e for e in evidence}
    rows=read_sheet(workbook,'Review 661 evidence')['rows'];additional=read_sheet(workbook,'Bo sot de nghi')['rows']
    reconciliation=reconcile(rows,evidence)
    assert not reconciliation['source_mismatches'] and not reconciliation['missing_ids']
    assert reconciliation['reviewer_nonempty']==reconciliation['approval_date_nonempty']==0
    rich=[]
    for r in rows:
        text=jobs[str(r['job_id'])]['description'];e=index[r['evidence_id']]
        assert hashlib.sha256(text.encode()).hexdigest()==e['source_text_sha256']
        if e['mapping_status']=='MAPPED_TO_RAW':
            assert text[e['raw_excerpt_start']:e['raw_excerpt_end']]==e['excerpt']
            assert ''.join(text[a:b] for a,b in e['raw_match_ranges'])==e['matched_text']
        ranges=e['raw_match_ranges'];a,b=ranges[0] if ranges else (0,0)
        triage,handling=assessment(r,text)
        row=dict(source_excel_row=str(r['_excel_row']),evidence_id=r['evidence_id'],job_id=r['job_id'],title=r['Chức danh'],
            source_skill=r['Skill nguồn'],source_mention_type=r['Loại nguồn'],machine_accepted=r['Máy nhận'],proposal=r['Quyết định đề nghị'],
            proposed_skill=r['Skill đề nghị'],proposed_mention_type=r['Loại đề nghị'],original_reason=r['Lý do'],
            original_evidence_quote=r['Quote nguyên văn'],matched_text=r['Matched text nguồn'],original_raw_ranges=r['Raw ranges nguồn'],
            source_context_start=str(max(0,a-650)),source_context=text[max(0,a-650):min(len(text),b+450)],
            source_description_sha256=e['source_text_sha256'],evidence_fact_check='PASS_FROZEN_SOURCE_QUOTE_RANGES_HASH',
            decision_support=triage,suggested_handling=handling,existing_reviewer=r['Người duyệt'],existing_reviewed_date=r['Ngày duyệt'])
        row.update({k:'' for k in FINAL});rich.append(row)
    changed=[r for r in rich if r['proposal']!='GIU_NHAN'];unclear=[r for r in rich if r['proposal']=='CHUA_RO']
    supported=[r for r in changed if r['decision_support']=='EVIDENCE_SUPPORTS_PROPOSAL']
    adjudicate=[r for r in changed if r['decision_support']!='EVIDENCE_SUPPORTS_PROPOSAL']
    assert len(rich)==661 and len(changed)==182 and len(unclear)==19 and len({r['job_id'] for r in unclear})==9
    # Every CHUA_RO remains adjudication; do not confuse the paired React ranges.
    assert all(r in adjudicate for r in unclear)
    assert next(r for r in rich if r['evidence_id'].startswith('28a90f6b'))['original_raw_ranges']=='[[2985,2990]]'
    assert next(r for r in unclear if r['evidence_id'].startswith('03a2dde1'))['original_raw_ranges']=='[[2993,2998]]'
    additions=[]
    for r in additional:
        text=jobs[str(r['job_id'])]['description'];a,b=int(r['Raw start']),int(r['Raw end'])
        assert r['Quote nguồn'] in text and text[a:b]==r['Alias']
        q=dict(job_id=r['job_id'],proposed_skill=r['Skill đề nghị'],alias=r['Alias'],original_raw_ranges=json.dumps([[a,b]]),
               original_evidence_quote=r['Quote nguồn'],decision_support='SOURCE_FACT_CHECKED_PENDING_APPROVAL',suggested_handling='Xác nhận code/alias/range và scope; đây là đề nghị bổ sung, không tự gán vào bridge 355 cặp.')
        q.update({k:'' for k in FINAL});additions.append(q)
    checklist=[dict(item=x,status='PENDING_HUMAN_CONFIRMATION',reviewer='',reviewed_date='',final_note='') for x in [
        'Chốt ranh giới React Native/React-DOM/React-JSS, Azure DevOps/cloud, Oracle ERP/cloud/DB; không tự mở rộng dictionary.',
        'Phân xử title-only, câu predates, môi trường và phạm vi cue is a plus/MUST HAVE.',
        'Xem 4 ca PROPOSAL_CONFLICT; đối chiếu nguồn trước khi chọn loại cuối.',
        'Duyệt cả 182 thay đổi và 479 GIU_NHAN, không chỉ 19 CHUA_RO.',
        'Duyệt 5 mention bổ sung, kiểm unique evidence/range và chống double count job-skill.',
        'Chỉ người duyệt điền final_decision/final_skill_code/final_mention_type/final_raw_ranges/reviewer/reviewed_date.',
        'Không sửa bản v0.1.2; thay đổi sau phê duyệt phải có version riêng và regression/parity tương ứng.',
        'Nhận D06 Full + receipt/hash/schema/validation, chốt nguồn description trước A05 official.',
        'Q05 job_functions cần chốt cho A06; D07 cần cho lương, không phải đầu vào extractor A05.',
        'Nghiệm thu kỹ thuật/parity không thay nhãn kỹ năng; không tính accuracy hoặc thống kê IT từ 105 mẫu.']]
    instructions=[dict(topic='Trạng thái',note='PROPOSED_NOT_APPROVED. Mọi nhận xét ở decision_support/suggested_handling là hỗ trợ rà soát, không phải quyết định cuối.'),
        dict(topic='Đối chiếu',note=f'661 nguồn; 182 khác GIU_NHAN gồm 19 CHUA_RO/9 tin; {len(supported)} có căn cứ ủng hộ đề nghị, {len(adjudicate)} cần phân xử thêm. Tất cả vẫn cần người duyệt ký.'),
        dict(topic='Các sheet lặp cùng evidence_id',note='TOAN_BO_661 là bảng ghi quyết định chính; các sheet con là bản đọc ưu tiên. Không ghi quyết định trái nhau ở nhiều sheet; chỉ cập nhật bảng chính, dùng evidence_id làm khóa.'),
        dict(topic='Cột vàng',note='Chỉ người duyệt ghi final_decision (CONFIRM_PROPOSAL/OVERRIDE_PROPOSAL/CHUA_RO), code/type/range cuối và người/ngày duyệt thực tế. Để trống nếu chưa có xác nhận.'),
        dict(topic='Phân biệt React',note='28a90f6b… [2985,2990) là React độc lập (SUA_LOAI); 03a2dde1… [2993,2998) là React trong React Native (CHUA_RO). Không gộp hai evidence.'),
        dict(topic='Giới hạn',note='Mẫu phát triển; không D06, không tổng thể IT, không gold skill, không accuracy; không chạy extraction/parity trong lần tạo workbook.')]
    jobrows=[dict(job_id=j,title=jobs[j]['title'],source_description=jobs[j]['description'],source_sha256=hashlib.sha256(jobs[j]['description'].encode()).hexdigest()) for j in sorted({r['job_id'] for r in unclear})]
    sheets=[('HUONG_DAN',instructions),('CHUA_RO_19',unclear),('DE_NGHI_182',changed),('CO_CAN_CU',supported),('CAN_PHAN_XU',adjudicate),('TOAN_BO_661',rich),('BO_SUNG_5',additions),('NGUON_9_TIN',jobrows),('CHECKLIST',checklist)]
    output=out/'a05_final_acceptance_pending.xlsx';write_workbook(output,sheets)
    with zipfile.ZipFile(output) as z:assert z.testzip() is None
    for name,data in sheets:
        readback=read_sheet(output,name)
        assert not readback['formulas'] and len(readback['rows'])==len(data)
        for expected,actual in zip(data,readback['rows']):
            assert all(actual.get(k,'')==v for k,v in expected.items()),(name,expected.get('evidence_id'))
            assert all(actual.get(k,'')=='' for k in FINAL)
    for name,data in [('chua_ro_19',unclear),('changes_182',changed),('adjudication',adjudicate)]:
        with (out/(name+'.csv')).open('x',encoding='utf-8-sig',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
    write_reading_notes(out,unclear)
    summary=dict(status='PASS_PENDING_HUMAN_APPROVAL',source_workbook=str(workbook),source_workbook_sha256=sha256(workbook),
        workbook=str(output),workbook_sha256=sha256(output),counts=dict(evidence=661,changes=182,unclear=19,unclear_jobs=9,supported_proposals=len(supported),adjudication=len(adjudicate),additional=5),
        decision_support_counts=dict(collections.Counter(r['decision_support'] for r in changed)),all_final_fields_blank=True,
        evidence_source_checks_passed=True,workbook_zip_crc_passed=True,all_sheets_readback_exact=True,
        extractor_executed=False,parity_executed=False,A04_executed=False,decisions_applied=False,
        protected_input_hashes=before)
    assert all(sha256(Path(p))==h for p,h in before.items())
    (out/'validation_manifest.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(summary['counts'],ensure_ascii=True));return out,summary


if __name__=='__main__':main()
