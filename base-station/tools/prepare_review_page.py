"""Add an offline anonymous review form to an exported benchmark package."""
import argparse
import json
from pathlib import Path


def build(package_dir):
    root = Path(package_dir)
    data = json.loads((root / 'review.json').read_text())
    # Inline JSON is data, never HTML or executable reviewer content.
    payload = json.dumps(data, ensure_ascii=False).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    page = '''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Moin blind review</title><style>
body{font:17px system-ui;max-width:850px;margin:40px auto;padding:0 20px;background:#f5f4f0;color:#183a35}
article{background:white;padding:24px;margin:22px 0;border:1px solid #ccc;border-radius:10px}
select,textarea,button{font:inherit;padding:10px}textarea{display:block;width:90%;margin-top:14px}
.output{white-space:pre-wrap;line-height:1.6}audio{width:100%}button{cursor:pointer}
</style><h1>Moin · Blind meaning review</h1>
<p>Listen to the Arabic recording, then judge each English or French output independently.
Only <b>faithful</b> passes. Model names stay hidden until all judgements are submitted.</p>
<p>Faithful: preserves meaning and religious claims. Partly wrong: changes, omits, or adds meaning.
Serious meaning error: false religious claim, reversal, wrong Qur’an handling, or confident fabrication.</p>
<p>Your edits stay in this page until you download them. Save a draft before closing; import it to resume.</p>
<label>Resume saved review <input type="file" id="resume" accept=".json"></label>
<p id="progress"></p><button id="save">Download review.json</button><main id="items"></main>
<script type="application/json" id="data">PAYLOAD</script><script>
const data=JSON.parse(document.getElementById('data').textContent);
const el=(tag,text)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;return n};
function progress(){document.getElementById('progress').textContent=data.items.filter(x=>x.label).length+' / '+data.items.length+' judgements completed';}
function draw(){const main=document.getElementById('items');main.replaceChildren();for(const item of data.items){
 const a=el('article');a.append(el('h2',item.clip+' · '+item.system+' · '+item.language.toUpperCase()));
 const audio=el('audio');audio.controls=true;audio.preload='none';audio.src=item.audio;a.append(audio);
 const text=el('p',item.text||'[No output]');text.className='output';a.append(text);
 if(item.unavailable)a.append(el('p','Unavailable or withheld: this output cannot pass.'));
 if(item.rendering_source&&Object.keys(item.rendering_source).length)a.append(el('p','Rendering source: '+JSON.stringify(item.rendering_source)));
 const label=el('label','Judgement '),select=el('select');
 for(const [value,name] of [['','Choose…'],['faithful','Faithful'],['partly_wrong','Partly wrong'],['serious_meaning_error','Serious meaning error']]){const o=el('option',name);o.value=value;o.disabled=item.unavailable&&value==='faithful';select.append(o);}
 select.value=item.label||'';select.onchange=()=>{item.label=select.value||null;progress()};label.append(select);a.append(label);
 const note=el('textarea');note.placeholder='Optional comment';note.setAttribute('aria-label','Comment for '+item.id);note.value=item.comment||'';note.oninput=()=>item.comment=note.value;a.append(note);main.append(a);
}progress();}
document.getElementById('save').onclick=()=>{const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)+'\\n'],{type:'application/json'}));const link=el('a');link.href=url;link.download='review.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000)};
document.getElementById('resume').onchange=async event=>{try{const incoming=JSON.parse(await event.target.files[0].text());
 const immutable=x=>JSON.stringify(Object.fromEntries(Object.entries(x).filter(([k])=>!['label','comment'].includes(k))));
 if(JSON.stringify(incoming.protocol)!==JSON.stringify(data.protocol)||incoming.items.length!==data.items.length)throw Error();
 for(let i=0;i<data.items.length;i++){const x=incoming.items[i];if(immutable(x)!==immutable(data.items[i])||![null,'faithful','partly_wrong','serious_meaning_error'].includes(x.label)||typeof x.comment!=='string'||x.unavailable&&x.label==='faithful')throw Error();}
 incoming.items.forEach((x,i)=>{data.items[i].label=x.label;data.items[i].comment=x.comment});draw();
 }catch{alert('This file does not match this review package. No changes imported.')}};
draw();</script></html>'''.replace('PAYLOAD', payload)
    target = root / 'index.html'
    with target.open('x') as f:
        f.write(page)
    return target


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('package', type=Path)
    print(build(parser.parse_args().package))
