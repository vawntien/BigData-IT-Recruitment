"""A09-A11 from saved official SUCCESS only; otherwise honest waiting content."""
from __future__ import annotations

import argparse
import csv
import html
import json
from pathlib import Path

from tv2_csv import sha256, write_json

QUESTIONS = ["Nhóm nghề CNTT", "Cấp kinh nghiệm", "Địa điểm đăng tuyển", "Loại việc và cờ remote", "Nhãn chức năng nguồn", "Kỹ năng công nghệ", "Lương cùng đơn vị/nguồn", "Thời gian UTC"]
LIMITS = ["Phụ thuộc taxonomy D06; không suy nghề từ ngành doanh nghiệp.",
          "Nhãn cấp bậc không tương đương số năm kinh nghiệm.",
          "Giữ chuỗi location; chưa suy quốc gia/địa điểm làm việc thực tế.",
          "NULL remote không phải false; không suy ba loại remote/hybrid/onsite.",
          "Nhãn đa giá trị, tổng tỷ lệ có thể vượt 100%; không phải Python/SQL.",
          "Mẫu số gồm PROCESSED_NO_MATCH; missing/failed/partial không phải zero-hit; mention không đồng nghĩa bắt buộc.",
          "Không gộp currency/pay_period/compensation_type/salary_source; quantile của min và max riêng, không tự quy đổi.",
          "Hai timestamp riêng; kỳ biên/thưa không chứng minh xu hướng toàn thị trường."]


CHART_CONTRACT = {
    'Q01': ('q01_role_groups', 'countDistinct(job_id) by primary group; share=count/N', 'N IT'),
    'Q02': ('q02_experience', 'countDistinct(job_id) by source level incl NULL; known share separately', 'N IT; known level separately'),
    'Q03': ('q03_location', 'countDistinct(job_id) by trimmed location; top-k; no geographic inference', 'known location; coverage=known/N'),
    'Q04': ('q04_work_type', 'countDistinct(job_id) by work type; remote flag table retains true/false/NULL', 'N IT'),
    'Q05': ('q05_functional_labels', 'countDistinct(job_id) per source skill_abr; multi-label percent may exceed 100%', 'jobs with mapped source label; coverage/N'),
    'Q06': ('q06_skills_global', 'distinct job-skill; by-group/level denominator includes successful zero-hit', 'PROCESSED_WITH_MATCH + PROCESSED_NO_MATCH'),
    'Q07': ('q07_salary_separate_units', 'independent n_min/n_max and exact Q1/median/Q3/IQR; group/currency/period/type/source never pooled', 'n_min/n_max per cell; coverage uses B_g including missing salary'),
    'Q08': ('q08_original_month', 'distinct jobs per UTC month; listed_time and weekly tables separate', 'valid original_listed_time; other timestamp separately')}


def chart_sources(manifest, manifest_path):
    return {q:dict(table=table+'.csv',calculation=calculation,denominator_definition=denom,
                   denominator=manifest.get('queries',{}).get(q,{}).get('denominator'),
                   query_status=manifest.get('queries',{}).get(q,{}).get('status','BLOCKED_DEPENDENCY'),
                   run_id=manifest.get('run_id'),manifest=str(manifest_path),manifest_sha256=sha256(Path(manifest_path)),
                   table_sha256=manifest.get('tables',{}).get(table,{}).get('csv_sha256'),
                   scope='OFFICIAL_VERIFIED' if official_success(manifest) else 'WAITING_OFFICIAL_INPUT_NO_NUMERIC_CHART')
            for q,(table,calculation,denom) in CHART_CONTRACT.items()}


def official_success(m):
    return (m.get("status") == "SUCCESS" and m.get("run_kind") == "OFFICIAL" and
            all(m.get("dependencies", {}).get(k) for k in ["D05", "D06", "A05", "D07"]) and
            all(m.get("queries", {}).get(f"Q{i:02d}", {}).get("status") == "SUCCESS" for i in range(1,9)))


def read_tables(folder, manifest):
    result = {}
    if not official_success(manifest):
        return result
    for name, spec in manifest["tables"].items():
        path = (folder / spec["csv"]).resolve()
        if not path.is_relative_to(folder.resolve()) or sha256(path) != spec["csv_sha256"]:
            raise ValueError("Saved table missing/changed; do not publish insights")
        with path.open(encoding="utf-8-sig", newline="") as stream:
            result[name] = list(csv.DictReader(stream))
    return result


def bars(rows, label, value="job_count", chronological=False):
    rows = sorted(rows, key=lambda r:r[label]) if chronological else sorted(rows,key=lambda r:int(r[value]),reverse=True)[:8]
    if not rows:
        return '<p class="waiting">Không có quan sát hợp lệ; không vẽ giá trị giả.</p>'
    maximum = max(int(r[value]) for r in rows) or 1
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 %d" role="img" aria-label="Số tin từ bảng đã kiểm chứng">' % (len(rows)*42+25)]
    for i,row in enumerate(rows):
        name = row[label] or "Thiếu"
        width = int(row[value])/maximum*530
        svg.append(f'<text x="0" y="{i*42+28}" font-size="17">{html.escape(name[:34])}</text><rect x="350" y="{i*42+8}" width="{width}" height="25" fill="#286a96"/><text x="{360+width}" y="{i*42+28}" font-size="17">{int(row[value])}</text>')
    return "".join(svg)+"</svg>"


def workflow(labels):
    svg = ['<svg viewBox="0 0 1000 150" role="img" aria-label="Sơ đồ phương pháp; không phải số liệu thị trường">']
    for i,label in enumerate(labels):
        x = i*250
        svg.append(f'<rect x="{x+5}" y="25" width="215" height="80" rx="12" fill="#e3eef6" stroke="#286a96"/><text x="{x+112}" y="70" text-anchor="middle" font-size="19">{html.escape(label)}</text>')
        if i<3:svg.append(f'<text x="{x+230}" y="74" font-size="28">→</text>')
    return "".join(svg)+"</svg>"


def insights(manifest, tables):
    if not official_success(manifest):
        return [f"Q{i:02d} — CHỜ INPUT: chưa có run OFFICIAL SUCCESS; chưa xác định tử số/mẫu số chính thức. {LIMITS[i-1]}" for i in range(1,9)]
    n = manifest["confirmed_it_jobs"]
    results = []
    names = ["q01_role_groups","q02_experience","q03_location","q04_work_type","q05_functional_labels","q06_skills_global"]
    for i,name in enumerate(names,1):
        rows = tables[name]
        valid = [r for r in rows if r.get("category", "present")]
        if not valid:
            text = "Không có quan sát có nhãn hợp lệ; không kết luận nhóm dẫn đầu."
        else:
            top = max(valid,key=lambda r:int(r["job_count"]))
            label = top.get("category") or top.get("skill_name")
            denominator = manifest["queries"][f"Q{i:02d}"]["denominator"]
            text = f"Giá trị có số tin cao nhất là {label}: {top['job_count']}/{denominator}; N CNTT={n}."
        results.append(f"Q{i:02d} — {text} Nguồn {name}.csv; coverage={manifest['queries'][f'Q{i:02d}']['coverage']}. {LIMITS[i-1]}")
    rows = tables["q07_salary_separate_units"]
    if rows:
        r = sorted(rows,key=lambda r:(r["currency"],r["pay_period"],r["salary_source"]))[0]
        text = f"Ô {r['a02_group']}/{r['currency']}/{r['pay_period']}/{r['compensation_type']}/{r['salary_source']}: n_min={r['n_min']}, n_max={r['n_max']}, B_g={r['population_n']}; min median/IQR={r['min_salary_median']}/{r['min_salary_iqr']}; max median/IQR={r['max_salary_median']}/{r['max_salary_iqr']}. Không gộp các ô khác đơn vị hoặc nguồn."
    else:text = "Không có lương hợp lệ cùng bộ đơn vị; chưa đủ dữ liệu để so sánh."
    results.append("Q07 — "+text+" Nguồn q07_salary_separate_units.csv. "+LIMITS[6])
    rows = tables["q08_original_month"]
    text = (f"original_listed_time ghi nhận {len(rows)} tháng quan sát; tổng {sum(int(r['job_count']) for r in rows)} tin có timestamp, N={n}." if rows else "Không có original_listed_time hợp lệ.")
    results.append("Q08 — "+text+" Nguồn q08_original_month.csv; listed_time ở bảng riêng. "+LIMITS[7])
    return results


def render(manifest_path, output):
    manifest_path, output = Path(manifest_path), Path(output)
    if output.exists():raise FileExistsError("New report directory required")
    m = json.loads(manifest_path.read_text(encoding="utf-8"))
    tables = read_tables(manifest_path.parent,m)
    verified = official_success(m)
    claims = insights(m,tables)
    output.mkdir(parents=True,exist_ok=False)
    sources=chart_sources(m,manifest_path)
    write_json(output/'chart_sources.json',sources,exclusive=True)
    (output/'chart_sources.md').write_text('# Nguồn và cách tính biểu đồ\n\n'+
        '\n\n'.join(f"{q}: `{s['table']}`; {s['calculation']}. Mẫu số: {s['denominator_definition']}; giá trị={s['denominator']}; trạng thái={s['query_status']}. Manifest/hash: `{s['manifest']}` / `{s['manifest_sha256']}`. Table hash={s['table_sha256']}." for q,s in sources.items())+
        '\n\nSơ đồ workflow là hình phương pháp, không có số liệu thống kê. Nguồn: A01 và hồ sơ phương pháp TV2. Các ô chờ không phải giá trị 0.\n',encoding='utf-8')
    status = "Candidate — CHỜ OFFICIAL SUCCESS" if not verified else "Candidate — số liệu đã đối soát, chờ rà soát nội dung"
    a09 = "# A09 — Nhận xét có kiểm soát nguồn\n\n"+status+"\n\n"+f"Nguồn: `{manifest_path}`; SHA-256 `{sha256(manifest_path)}`.\n\n"
    a09 += "\n\n".join(f"{i}. {text}" for i,text in enumerate(claims,1))
    a09 += "\n\nChưa có run chính thức thì các dòng trên là nội dung chờ input, không phải 8 nhận xét kết quả đã nghiệm thu. Không dùng 105 tin phát triển làm tổng thể; không suy đại diện thị trường Việt Nam hoặc quan hệ nhân quả.\n"
    (output/"a09_insights.md").write_text(a09,encoding="utf-8")
    a10 = "# A10 — Chương phân tích tuyển dụng CNTT\n\n"+status+"\n\n"
    a10 += "## Mục tiêu và tập phân tích\n\nMô tả cơ cấu nghề, kinh nghiệm, địa điểm, việc làm, nhãn nguồn, công nghệ, lương và thời gian trong bộ LinkedIn Job Postings 2023–2024. N phải lấy từ D06 được TV1 xác nhận, không dùng tổng raw hoặc mẫu phát triển. "
    a10 += f"N chính thức: {m.get('confirmed_it_jobs','CHỜ D06')}.\n\n"
    a10 += "## Phương pháp\n\nD05 giữ grain một job; bảng cầu nhiều nhãn chỉ được dùng trên nhánh riêng. D06 cung cấp ACCEPT/true và version/hash taxonomy; TV2 không chạy lại bộ lọc. A05 tái sử dụng extractor và dictionary v0.1.2, namespace postings.description; chưa tự áp workbook quyết định đề nghị. Q06 đếm distinct job trên toàn bộ description xử lý thành công, kể cả zero-hit; missing/failed/partial báo riêng. Q07 chỉ nhận salary_clean có chính sách duyệt, tách tiền tệ/kỳ trả/loại thù lao/nguồn; min và max có quantile riêng. Q08 chỉ dùng timestamp UTC đã cast, giữ hai cột riêng.\n\n"
    a10 += "## Kết quả và đối soát\n\n"+("\n\n".join(claims) if verified else "BLOCKED_DEPENDENCY: chưa có run OFFICIAL SUCCESS. Chưa có bảng/biểu đồ kết quả CNTT để viết kết luận định lượng. Khung nhận xét A09 đã ghi rõ từng mẫu số và giới hạn cần bổ sung; không chèn số liệu phát triển hoặc synthetic.")
    a10 += "\n\n## Hạn chế và phối hợp\n\nDataset không tự đại diện thị trường/quốc gia. Nhãn level không phải số năm; địa điểm chưa chuẩn hóa quốc gia; remote NULL không phải onsite; nhãn chức năng khác kỹ năng công nghệ; mention không chứng minh bắt buộc; quan sát thời gian thưa không chứng minh tăng trưởng. TV1 phụ trách D05/D06/D07 và schema/path; TV2 phụ trách A05–A11; TV3 đối soát dashboard/V10. Chưa có dữ liệu chính thức, parity Spark/Parquet và người duyệt skill thì chưa nghiệm thu hoàn thành. Không tự điền người/ngày duyệt.\n\n"
    a10 += f"Nguồn run: `{manifest_path}`. Manifest hash: `{sha256(manifest_path)}`. Không có commit/push tự động.\n"
    a10 += '\n\n## Spark SQL/PySpark và kiểm thử\n\nGROUP BY/countDistinct giữ grain job_id; semi-JOIN giới hạn bridge theo D06, distinct job-skill trước tổng hợp; NULL-safe JOIN cho nhóm thiếu. Không dùng raw làm IT. Quy tắc/nguồn/mẫu số biểu đồ tại chart_sources.json. Phân loại dùng hồ sơ A04 và taxonomy/version từ D06; trích kỹ năng giữ evidence/ranges/hash, không tự gán nhãn chuẩn.\n\n'
    a10 += json.dumps(m.get('technical_validation',{'status':'CHƯA XÁC NHẬN TRONG MANIFEST NÀY'}),ensure_ascii=False,indent=2)+'\n\nKết quả parity/phát triển không là thống kê IT hoặc accuracy. D06/D07 official còn chờ; giới hạn đại diện, missing, quy tắc kỹ năng và đơn vị lương giữ nguyên.\n'
    (output/"a10_analysis_report.md").write_text(a10,encoding="utf-8")
    chart = {}
    if verified:
        for key,name,label in [("roles","q01_role_groups","category"),("experience","q02_experience","category"),("location","q03_location","category"),("work","q04_work_type","category"),("functions","q05_functional_labels","skill_name"),("skills","q06_skills_global","skill_name"),("time","q08_original_month","period")]:
            chart[key] = bars(tables[name],label,chronological=key=="time")
            (output/(name+".svg")).write_text(chart[key] if chart[key].startswith("<svg") else '<svg xmlns="http://www.w3.org/2000/svg"><text x="10" y="30">No valid data</text></svg>',encoding="utf-8")
    waiting = '<div class="waiting">CHỜ INPUT CHÍNH THỨC — chưa vẽ số liệu thị trường</div>'
    slides = [
        ("Phân tích tuyển dụng CNTT bằng Big Data",["Đồng Viết Dũng — TV2", "LinkedIn Job Postings 2023–2024", "Bản nội dung candidate; kết quả chỉ công bố sau run chính thức"],"Mở đầu bằng mục tiêu mô tả dataset. Không gọi số raw hoặc mẫu phát triển là tổng tin IT.",workflow(["Câu hỏi A01","Dữ liệu TV1","Phân tích TV2","Dashboard TV3"])),
        ("Dữ liệu đi qua những bước nào?",["CSV nguồn được giữ nguyên", "D05/D06/D07 do TV1 xác nhận", "Phân tích từ Parquet, không chạy lại taxonomy"],"Đọc trạng thái D05 từ hồ sơ tiếp nhận đi cùng run; phân biệt canonical đã nhận với D06/D07 còn chờ. Không trình bày pipeline dự kiến như đã chạy.",workflow(["Raw CSV","D05 canonical","D06 IT jobs","Parquet analytics"])),
        ("Tin IT được xác định như thế nào?",["D06 dùng taxonomy đã được TV1 xác nhận", "ACCEPT, REJECT, REVIEW được giữ riêng", "Một job_id, một nhóm chính; lưu lý do và version"],"Tóm tắt A02/A04 hiện hữu, không tối ưu lại. Active v0.2.0 và candidate v0.2.2 khác nhau; phiên bản official lấy từ D06. Chưa có đánh giá độc lập thì không báo accuracy.",workflow(["Title/mô tả","Rule đã chốt","Decision + nhóm","Evidence/hash"])),
        ("Trích kỹ năng có bằng chứng",["Tái sử dụng dictionary v0.1.2", "Java khác JavaScript; C/C++ cần ranh giới", "Một job–skill chỉ được tính một lần"],"Nhắc ba loại REQUIRED/PREFERRED/TASK. Không dùng nhãn IT/ENG của LinkedIn thay Python/SQL. Workbook đề nghị chưa được duyệt không tự áp; 105 tin là tập phát triển.",workflow(["Mô tả gốc","Alias + context","Evidence/ranges","Bridge unique"])),
        ("Tổng quan tập IT chính thức",[f"N = {m.get('confirmed_it_jobs','CHỜ D06')}", "Báo độ phủ và thiếu theo từng thuộc tính", "Manifest và mẫu số đi cùng mỗi bảng"],"Không điền 0 thay số chưa biết. Chỉ lấy N từ run OFFICIAL SUCCESS; báo cả source status của A05.",chart.get("roles",waiting)),
        ("Cơ cấu nghề CNTT",["Q01: distinct job_id theo nhóm", "Giữ IT_OTHER/thiếu riêng", "Nhóm nghề không phải ngành doanh nghiệp"],claims[0],chart.get("roles",waiting)),
        ("Kinh nghiệm, địa điểm, việc làm",["Q02: nhãn cấp bậc, không phải số năm", "Q03: chuỗi location và độ phủ", "Q04: work type; remote true/false/NULL riêng"],"Nếu có dữ liệu, đối chiếu cả ba bảng và mẫu số; remote NULL không phải không được làm từ xa. Không tự kết luận Việt Nam.",chart.get("experience",waiting)+chart.get("location","")+chart.get("work","")),
        ("Nhãn chức năng và kỹ năng công nghệ",["Q05: nhãn nguồn đa giá trị; tổng tỷ lệ có thể vượt 100%", "Q06: Top skill, theo nhóm/kinh nghiệm; gồm successful zero-hit", "Hai nguồn nhãn riêng; ghi dictionary/run, không suy kỹ năng bắt buộc"],claims[4]+" "+claims[5],chart.get("functions",waiting)+chart.get("skills",waiting)),
        ("Lương và phân bố thời gian",["Q07 chỉ sau duyệt D07; cùng đơn vị và nguồn", "Ghi n và quantile min/max riêng", "Q08: hai timestamp UTC; không suy xu hướng thị trường"],claims[6]+" "+claims[7],chart.get("time",waiting)),
        ("Kết luận và câu hỏi phản biện",["Kết luận định lượng: CHỜ RUN SUCCESS" if not verified else "Đọc 3 kết luận đã đối soát từ A09", "Giới hạn: đại diện, missing, nhãn và đơn vị", "Tiếp theo: TV1 input/runtime → A05 → kiểm tra kết quả"],"Phản biện: Vì sao không dùng 105 tin? Vì đó là mẫu phát triển. Vì sao zero-hit nằm ở mẫu số? Vì mô tả đã xử lý thành công. Vì sao không gộp lương? Vì khác đơn vị/nguồn. Đối soát dashboard/V10 với TV3 trước buổi trình bày.",workflow(["TV1 xác nhận","Spark/Parquet","Người duyệt","A09–A11 chốt"]))]
    markdown = "# A11 — Nội dung và ghi chú thuyết trình (10 slide)\n\n"+status+"\n\n"
    parts = []
    slide_questions={5:['Q01'],6:['Q01'],7:['Q02','Q03','Q04'],8:['Q05','Q06'],9:['Q07','Q08']}
    for i,(title,bullets,notes,visual) in enumerate(slides,1):
        if i==4:
            notes+=' Kiểm thử kỹ thuật, tách khỏi kết quả thị trường: '+json.dumps(m.get('technical_validation',{'status':'CHỜ HỒ SƠ TEST'}),ensure_ascii=False)
        if i in slide_questions:
            provenance=' | '.join(q+': '+sources[q]['table']+'; mẫu số '+sources[q]['denominator_definition']+'; '+sources[q]['query_status'] for q in slide_questions[i])
        else:provenance='Sơ đồ phương pháp, không phải thống kê; nguồn A01, hồ sơ A04/A05 và manifest đi kèm.'
        visual+='<p class="source" style="font-size:13px">'+html.escape(provenance)+' — chart_sources.json; run '+html.escape(str(m.get('run_id')))+ '</p>'
        notes+=' Nguồn hình/cách tính: '+provenance
        markdown += f"## Slide {i}: {title}\n\n"+"\n".join("- "+b for b in bullets)+f"\n\nGhi chú nói: {notes}\n\n"
        parts.append(f'<section class="slide" data-slide="{i}"><small>TV2 · Đồng Viết Dũng · {i}/10</small><h1>{html.escape(title)}</h1><ul>'+"".join('<li>'+html.escape(b)+'</li>' for b in bullets)+f'</ul><div class="visual">{visual}</div><details open><summary>Ghi chú thuyết trình</summary><p>{html.escape(notes)}</p></details></section>')
    (output/"a11_slide_content.md").write_text(markdown,encoding="utf-8")
    document = '<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>A11 — TV2</title><style>body{margin:0;background:#edf2f6;color:#183248;font:21px/1.5 system-ui}.slide{box-sizing:border-box;min-height:100vh;max-width:1200px;margin:auto;padding:35px 55px;background:white;border-bottom:10px solid #286a96}h1{font-size:36px}small{color:#466579}svg{width:100%;max-height:270px}.waiting{padding:35px;border:2px dashed #9aafbe;background:#f2f5f7}details{font-size:17px;background:#edf2f6;padding:12px;margin-top:20px}nav{position:fixed;bottom:10px;right:15px;z-index:5}button{font-size:18px;padding:8px}body.present .slide{display:none}body.present .slide.active{display:block}@media print{nav{display:none}body.present .slide,.slide{display:block;page-break-after:always;height:100vh;min-height:0}details{font-size:12px}}</style><nav><button onclick="document.body.classList.toggle(\'present\');show(current)">Trình chiếu / cuộn</button><button onclick="show(current-1)">←</button><button onclick="show(current+1)">→</button></nav>'+"".join(parts)+'<script>let current=0;const slides=[...document.querySelectorAll(".slide")];function show(n){current=Math.max(0,Math.min(slides.length-1,n));slides.forEach((s,i)=>s.classList.toggle("active",i===current));if(!document.body.classList.contains("present"))slides[current].scrollIntoView()}document.addEventListener("keydown",e=>{if(e.key==="ArrowRight")show(current+1);if(e.key==="ArrowLeft")show(current-1)});slides[0].classList.add("active");</script></html>'
    (output/"a11_slides.html").write_text(document,encoding="utf-8")
    write_json(output/"publication_manifest.json",dict(status="CANDIDATE" if not verified else "CANDIDATE_VERIFIED_NUMBERS_PENDING_REVIEW",official_success=verified,input_manifest=str(manifest_path.resolve()),input_manifest_sha256=sha256(manifest_path),slides=10,market_results_published=verified,files={p.name:sha256(p) for p in output.iterdir() if p.is_file()}),exclusive=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest",required=True)
    p.add_argument("--output",required=True)
    a = p.parse_args()
    render(a.manifest,a.output)
