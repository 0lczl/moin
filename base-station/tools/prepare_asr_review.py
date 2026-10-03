#!/usr/bin/env python3
"""Build a static anonymous Arabic ASR listening/review page."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_new(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".pending-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as output:
            output.write(text)
            output.flush()
            os.fsync(output.fileno())
        os.link(temporary, path)
    except FileExistsError:
        raise SystemExit(f"Refusing to replace immutable review artifact: {path}")
    finally:
        Path(temporary).unlink(missing_ok=True)


def build(workspace: Path, corpus: Path, output: Path):
    lock, report = read(workspace / "lock.json"), read(workspace / "report.json")
    candidates = sorted(report["candidates"], key=lambda item: hashlib.sha256(
        f"{lock['corpus_identity']}:{item['identity']}".encode()).hexdigest())
    labels = {item["id"]: chr(65 + index) for index, item in enumerate(candidates)}
    by_candidate = {item["id"]: {clip["clip_id"]: clip for clip in item["clips"]} for item in candidates}
    clips = []
    for clip in lock["corpus_snapshot"]:
        clips.append({
            "id": clip["id"],
            "audio": os.path.relpath((corpus / clip["audio"]).resolve(), output.parent.resolve()),
            "reference": clip["reference"]["text"],
            "primaryIncluded": clip["primary_score"]["included"],
            "exclusionReason": clip["primary_score"]["exclusion_reason"],
            "systems": [{
                "label": labels[item["id"]],
                "text": by_candidate[item["id"]][clip["id"]]["raw_hypothesis"],
                "status": by_candidate[item["id"]][clip["id"]]["status"],
            } for item in candidates],
        })
    data = {"version": 1, "corpusIdentity": lock["corpus_identity"], "clips": clips}
    mapping = {
        "schema_version": 1, "corpus_identity": lock["corpus_identity"],
        "note": "Keep this identity map separate until Arabic review is exported.",
        "systems": {label: candidate_id for candidate_id, label in labels.items()},
    }
    write_new(workspace / "review-map.json", json.dumps(mapping, ensure_ascii=False, indent=2) + "\n")
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    html = TEMPLATE.replace("__REVIEW_DATA__", payload)
    write_new(output, html)


TEMPLATE = r'''<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>مراجعة التعرّف على الكلام — مُعين</title>
<style>
@font-face{font-family:PlexArabic;src:url('../../../../brand/presentation/plex-arabic-400.ttf')}@font-face{font-family:PlexArabic;src:url('../../../../brand/presentation/plex-arabic-700.ttf');font-weight:700}
:root{--ink:#123b32;--green:#0d5a49;--gold:#b98a36;--ivory:#f7f2e7;--paper:#fffdf7;--line:#d8cfbd;--bad:#9b3d2f;--muted:#6e746e}
*{box-sizing:border-box}body{margin:0;background:var(--ivory);color:var(--ink);font-family:PlexArabic,serif;line-height:1.8}.shell{max-width:1180px;margin:auto;padding:42px 24px 90px}
header{display:grid;grid-template-columns:1fr auto;gap:32px;align-items:end;border-bottom:2px solid var(--gold);padding-bottom:25px;margin-bottom:32px}h1{font-size:clamp(2rem,5vw,4.7rem);line-height:1.05;margin:0;letter-spacing:-.04em}header p{max-width:680px;color:var(--muted);margin:16px 0 0}.seal{width:104px;height:104px;border:1px solid var(--gold);border-radius:50%;display:grid;place-items:center;font-weight:700;color:var(--green);transform:rotate(-7deg)}
.tools{position:sticky;top:0;z-index:5;display:flex;gap:10px;align-items:center;flex-wrap:wrap;background:rgba(247,242,231,.94);backdrop-filter:blur(10px);padding:13px 0;border-bottom:1px solid var(--line)}button,input,textarea,select{font:inherit}button{border:1px solid var(--green);background:var(--green);color:white;padding:8px 17px;border-radius:999px;cursor:pointer}.ghost{background:transparent;color:var(--green)}#progress{margin-inline-start:auto;font-variant-numeric:tabular-nums}
.clip{margin-top:44px;background:var(--paper);border:1px solid var(--line);box-shadow:0 18px 45px rgba(18,59,50,.07);padding:clamp(20px,4vw,42px);position:relative;overflow:hidden}.clip:before{content:attr(data-index);position:absolute;left:22px;top:-24px;font-size:7rem;font-weight:700;color:rgba(13,90,73,.055);line-height:1}.clip h2{margin:0 0 12px;font-size:1.35rem}.clip audio{width:100%;accent-color:var(--green)}.reference{border-right:4px solid var(--gold);padding:12px 18px;margin:22px 0;background:#fbf5e8}.reference b{display:block;font-size:.8rem;color:var(--gold);letter-spacing:.12em}.excluded{color:var(--bad);font-size:.88rem;margin:8px 0}
.systems{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}.system{border-top:1px solid var(--line);padding-top:16px}.badge{display:inline-grid;place-items:center;background:var(--green);color:white;width:34px;height:34px;border-radius:50%;font-weight:700;margin-left:8px}.hyp{min-height:126px;font-size:1.05rem}.failed{color:var(--bad)}.verdicts{display:flex;gap:7px;flex-wrap:wrap;margin:13px 0}.verdicts label{border:1px solid var(--line);padding:5px 10px;border-radius:999px;cursor:pointer}.flags{display:grid;grid-template-columns:repeat(2,1fr);font-size:.86rem;color:var(--muted)}textarea{width:100%;min-height:76px;border:1px solid var(--line);background:white;padding:10px;margin-top:10px;color:var(--ink)}
footer{margin-top:45px;border-top:1px solid var(--line);padding-top:18px;color:var(--muted)}@media(max-width:760px){header{grid-template-columns:1fr}.seal{display:none}.systems{grid-template-columns:1fr}.tools{position:static}#progress{width:100%;margin:0}.flags{grid-template-columns:1fr}}
</style>
</head>
<body><main class="shell"><header><div><h1>مراجعة الصوت<br>قبل اختيار النموذج</h1><p>استمع إلى المقطع، وقارن النص المرجعي بالنظامين المجهولين. راقب الأسماء والمصطلحات الشرعية والآيات والنفي والحذف والزيادة. لا تظهر الدرجات الآلية هنا حتى لا تؤثر في حكمك.</p></div><div class="seal">مُعين</div></header>
<div class="tools"><input id="reviewer" placeholder="اسم المراجع (اختياري)" aria-label="اسم المراجع"><button id="export">تصدير المراجعة</button><button class="ghost" id="clear">مسح المدخلات</button><span id="progress"></span></div><section id="clips"></section><footer>هذه المواد للتقييم المحلي الخاص. المقطع الرابع مستبعد من الدرجة الآلية بسبب نهاية غير واضحة، لكنه معروض للمراجعة البشرية.</footer></main>
<script>
const DATA=__REVIEW_DATA__;const KEY='moin-asr-review:'+DATA.corpusIdentity;const flags=['مصطلح شرعي','اسم عَلَم','نص قرآني','نفي/قلب معنى','حذف','زيادة'];let state=JSON.parse(localStorage.getItem(KEY)||'{"reviewer":"","judgments":{}}');
const esc=s=>(s||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function entry(cid,label){state.judgments[cid]??={};return state.judgments[cid][label]??={verdict:'',flags:[],comment:''}}
function save(){state.reviewer=document.querySelector('#reviewer').value;localStorage.setItem(KEY,JSON.stringify(state));progress()}
function progress(){let done=0,total=0;DATA.clips.forEach(c=>c.systems.forEach(s=>{total++;if(entry(c.id,s.label).verdict)done++}));document.querySelector('#progress').textContent=`${done} من ${total} حكمًا`}
function render(){document.querySelector('#reviewer').value=state.reviewer||'';document.querySelector('#clips').innerHTML=DATA.clips.map((c,i)=>`<article class="clip" data-index="${String(i+1).padStart(2,'0')}"><h2>المقطع ${i+1}</h2><audio controls preload="metadata" src="${esc(c.audio)}"></audio><div class="reference"><b>النص المرجعي</b>${esc(c.reference)}</div>${c.primaryIncluded?'':`<p class="excluded">لا يدخل هذا المقطع في التجميع الآلي: ${esc(c.exclusionReason)}</p>`}<div class="systems">${c.systems.map(s=>system(c,s)).join('')}</div></article>`).join('');bind();progress()}
function system(c,s){const e=entry(c.id,s.label);return `<div class="system" data-cid="${esc(c.id)}" data-label="${s.label}"><h3><span class="badge">${s.label}</span>النظام ${s.label}</h3><p class="hyp ${s.status==='ok'?'':'failed'}">${s.status==='ok'?esc(s.text):'فشل النظام ولم يُستبدل ناتجه.'}</p><div class="verdicts">${[['correct','صحيح'],['minor','خطأ محدود'],['serious','خطأ مؤثر']].map(([v,t])=>`<label><input type="radio" name="${c.id}-${s.label}" value="${v}" ${e.verdict===v?'checked':''}> ${t}</label>`).join('')}</div><div class="flags">${flags.map(f=>`<label><input type="checkbox" value="${f}" ${e.flags.includes(f)?'checked':''}> ${f}</label>`).join('')}</div><textarea placeholder="ملاحظة محددة…">${esc(e.comment)}</textarea></div>`}
function bind(){document.querySelectorAll('.system').forEach(el=>{const e=entry(el.dataset.cid,el.dataset.label);el.querySelectorAll('input[type=radio]').forEach(x=>x.onchange=()=>{e.verdict=x.value;save()});el.querySelectorAll('input[type=checkbox]').forEach(x=>x.onchange=()=>{e.flags=[...el.querySelectorAll('input[type=checkbox]:checked')].map(y=>y.value);save()});el.querySelector('textarea').oninput=x=>{e.comment=x.target.value;save()}});document.querySelector('#reviewer').oninput=save}
document.querySelector('#export').onclick=()=>{save();const out={schema_version:1,corpus_identity:DATA.corpusIdentity,exported_at:new Date().toISOString(),...state};const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify(out,null,2)],{type:'application/json'}));a.download='moin-asr-review.json';a.click();URL.revokeObjectURL(a.href)};document.querySelector('#clear').onclick=()=>{if(confirm('مسح جميع الأحكام والملاحظات؟')){localStorage.removeItem(KEY);state={reviewer:'',judgments:{}};render()}};render();
</script></body></html>'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    build(args.workspace, args.corpus, args.output)


if __name__ == "__main__":
    main()
