"""Synthetic audio and provider doubles test the protocol, never quality evidence."""
import copy
import hashlib
import json
import wave
from pathlib import Path
import pytest
from moin_benchmark.core import BenchmarkError, validate_corpus, registry, digest, secret_free
from moin_benchmark.engine import Benchmark


def save(path, value):
    path.write_text(json.dumps(value))


@pytest.fixture
def setup(tmp_path, monkeypatch):
    root = tmp_path/'corpus'
    root.mkdir()
    clips=[]
    for i in range(32):
        p = root/f'{i}.wav'
        with wave.open(str(p),'wb') as w:
            w.setparams((1,2,16000,0,'NONE','not compressed'))
            w.writeframes((i+1).to_bytes(2,'little')*1600)
        clips.append({'id':f'clip-{i}', 'audio':p.name, 'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),
                      'split':'development' if i<12 else 'final', 'speaker':f'speaker-{i%3}',
                      'source':{'uri':f'https://example.org/{i}','title':'fixture','retrieved_at':'2026-09-21'},
                      'source_start_seconds':i, 'duration_seconds':.1,
                      'permission':{'decision':'permitted','basis':'synthetic test','reviewer':'test','date':'2026-09-21'},
                      'tags':[['ordinary-teaching','islamic-terminology','natural-fast-speech','quran-adjacent'][i%4]],
                      'transcript':{'state':'verified','text':'مرجع بشري','reviewer':'fixture','date':'2026-09-21'}})
    save(root/'corpus.json',clips)
    config={'id':'baseline','name':'Private provider name','adapter':'baseline',
            'asr':{'model':'asr','revision':'a'*40},'translation':{'model':'mt','revision':'b'*40},
            'settings':{},'prompts':{'en':'','fr':''}}
    configs=tmp_path/'configs.json'
    save(configs,[config])
    def process(cfg,path,**kwargs):
        r={'arabic':'حديث عادي','en':'Teaching','fr':'Enseignement','timing_ms':{'total':5},'uncertainty':None,'failure':None}
        if kwargs.get('translation_guard'):
            decision=kwargs['translation_guard'](r['arabic'])
            if decision:
                r.update(en=decision['en'],fr=decision['fr'])
        return r
    monkeypatch.setattr('moin_benchmark.adapters.process', process)
    b=Benchmark(root,tmp_path/'private')
    b.lock(configs)
    return b, clips, configs


def review(b, split, tmp_path, misses=0):
    p=tmp_path/f'review-{split}'
    b.package(split,p)
    value=json.loads((p/'review.json').read_text())
    n=0
    for item in value['items']:
        item['label']='faithful'
        if item['language']=='fr' and n<misses:
            item['label']='partly_wrong'
            n+=1
    save(p/'review.json',value)
    b.submit(split,p/'review.json','human-fixture')
    return p


def compose(b,tmp_path):
    b.run('development','baseline')
    review(b,'development',tmp_path)
    r=tmp_path/'renderings.json'
    save(r,{'schema_version':1,'detection_ready':True,'renderings':[
        {'arabic':'بسم الله الرحمن الرحيم','english':{'text':'fixture only','source':'test','version':'1','approved':True},
         'french':{'text':'fixture seulement','source':'test','version':'1','approved':True}}]})
    b.select('baseline',r)
    b.run('development','moin')
    b.freeze()


def test_corpus_constraints(setup):
    b,clips,_=setup
    assert len(validate_corpus(b.corpus,'development'))==12
    with pytest.raises(BenchmarkError,match='frozen'):
        validate_corpus(b.corpus,'final')
    bad=copy.deepcopy(clips);bad[-1]['sha256']=bad[0]['sha256']
    save(b.corpus/'corpus.json',bad)
    with pytest.raises(BenchmarkError,match='Duplicate audio'):
        registry(b.corpus)


@pytest.mark.parametrize('mutation', ['speaker','transcript','permission','tags'])
def test_corpus_rejects_invalid_development(setup,mutation):
    b,clips,_=setup
    for c in clips[:12]:
        if mutation=='speaker': c['speaker']='same'
        if mutation=='transcript': c['transcript']['state']='draft'
        if mutation=='permission': c['permission']['decision']='unknown'
        if mutation=='tags': c['tags']=['ordinary-teaching']
    save(b.corpus/'corpus.json',clips)
    with pytest.raises(BenchmarkError): validate_corpus(b.corpus,'development')


def test_unknown_clip_no_partial_and_no_rerun(setup):
    b,_,_=setup
    with pytest.raises(BenchmarkError,match='Unknown clip'):
        b.run('development','baseline','missing')
    assert not (b.work/'runs').exists()
    b.run('development','baseline','clip-0')
    with pytest.raises(BenchmarkError,match='recorded'):
        b.run('development','baseline','clip-0')


def test_anonymous_review_immutable_and_no_early_reveal(setup,tmp_path):
    b,_,_=setup
    b.run('development','baseline')
    p=tmp_path/'review'
    b.package('development',p)
    text=(p/'review.json').read_text()
    assert 'baseline' not in text and 'Private provider' not in text and 'configuration' not in text
    with pytest.raises(BenchmarkError,match='Incomplete review'):
        b.report('development')
    with pytest.raises(BenchmarkError,match='Missing or invalid label'):
        b.submit('development',p/'review.json','reviewer')
    v=json.loads(text)
    for row in v['items']: row['label']='faithful'
    save(p/'review.json',v)
    b.submit('development',p/'review.json','reviewer')
    assert b.report('development')['candidates'][0]['languages']['fr']['faithful']==12
    with pytest.raises(BenchmarkError,match='Immutable'):
        b.submit('development',p/'review.json','reviewer')


@pytest.mark.parametrize('misses,earned',[(2,True),(3,False)])
def test_final_independent_gates_and_exactly_once(setup,tmp_path,misses,earned):
    b,_,_=setup
    with pytest.raises(BenchmarkError,match='frozen'):
        b.run('final','moin')
    compose(b,tmp_path)
    b.run('final','moin')
    with pytest.raises(BenchmarkError,match='consumed'):
        b.run('final','moin')
    review(b,'final',tmp_path,misses)
    report=b.report('final')
    assert report['quality_claim_90_percent'] is earned
    langs=report['candidates'][0]['languages']
    assert langs['en']['earned_90_percent'] is True
    assert langs['fr']['faithful']==20-misses
    assert langs['fr']['earned_90_percent'] is earned


def test_provider_crash_recorded_without_secret(setup,monkeypatch,tmp_path):
    b,_,_=setup
    def crash(*a,**k): raise RuntimeError('Bearer secret-data')
    monkeypatch.setattr('moin_benchmark.adapters.process',crash)
    b.run('development','baseline')
    r=b.results('development')
    assert len(r)==12 and all(x['failure'] for x in r)
    assert 'secret-data' not in json.dumps(r)
    p=tmp_path/'review'
    b.package('development',p)
    v=json.loads((p/'review.json').read_text())
    for row in v['items']: row['label']='faithful'
    save(p/'review.json',v)
    with pytest.raises(BenchmarkError,match='cannot pass'):
        b.submit('development',p/'review.json','reviewer')


def test_configuration_and_corpus_tampering_rejected(setup):
    b,clips,_=setup
    clips[0]['transcript']['text']='edited'
    save(b.corpus/'corpus.json',clips)
    with pytest.raises(BenchmarkError,match='Corpus changed'):
        b.run('development','baseline')


def test_secret_metadata_rejected():
    for value in ({'api_key':'secret'}, {'prompts':{'en':'Bearer key'}}, {'url':'https://user:pass@example.com'}):
        with pytest.raises(BenchmarkError): secret_free(value)
    secret_free({'credential_env':'BENCHMARK_TOKEN'})


def test_withheld_composition_stays_normalized(setup,tmp_path,monkeypatch):
    b,_,_=setup
    compose(b,tmp_path)
    def uncertain(cfg,path,**kwargs):
        return {'arabic':'كلام','en':'','fr':'','timing_ms':{'total':1},'uncertainty':'low_confidence','failure':None}
    monkeypatch.setattr('moin_benchmark.adapters.process',uncertain)
    b.run('final','moin')
    records=b.results('final')
    assert all(r['en']=='' and r['safety']['outcome']=='withheld' for r in records)
    p=tmp_path/'final-withheld'
    b.package('final',p)
    v=json.loads((p/'review.json').read_text())
    assert all(x['unavailable'] for x in v['items'])


def test_runtime_change_rejected(setup,monkeypatch):
    b,_,_=setup
    monkeypatch.setattr('moin_benchmark.adapters.runtime_identity',lambda: {'python':'changed'})
    with pytest.raises(BenchmarkError,match='runtime changed'):
        b.run('development','baseline')


def test_source_overlap_rejected(setup):
    b,clips,_=setup
    clips[-1]['source']['uri']=clips[0]['source']['uri']
    clips[-1]['source_start_seconds']=0
    save(b.corpus/'corpus.json',clips)
    with pytest.raises(BenchmarkError,match='overlapping'):
        registry(b.corpus)


def test_named_markdown_report(setup,tmp_path):
    from moin_benchmark.reporting import markdown
    b,_,_=setup
    compose(b,tmp_path)
    b.run('final','moin')
    review(b,'final',tmp_path,3)
    text=markdown(b.report('final'))
    assert '20/20' in text and '17/20' in text
    assert 'FR 18/20 threshold: MISSED' in text
    assert '90% quality claim: NOT earned.' in text


def test_interrupted_final_is_sealed_without_retry(setup,tmp_path,monkeypatch):
    b,_,_=setup
    compose(b,tmp_path)
    def interrupted(*args,**kwargs):
        raise KeyboardInterrupt()
    monkeypatch.setattr('moin_benchmark.adapters.process',interrupted)
    with pytest.raises(KeyboardInterrupt):
        b.run('final','moin')
    assert b.finalize_interrupted()=={'recorded_failures':20,'provider_calls':0}
    assert all(r['failure']['code']=='interrupted_final_attempt' for r in b.results('final'))
    with pytest.raises(BenchmarkError,match='consumed'):
        b.run('final','moin')


def test_partial_development_run_continues_without_replacing_outputs(setup,monkeypatch):
    b,_,_=setup
    b.run('development','baseline','clip-0')
    original=b.result_path('development','baseline','clip-0').read_bytes()
    calls=[]
    def process(cfg,path,**kwargs):
        calls.append(path.name)
        return {'arabic':'test','en':'test','fr':'test','timing_ms':{'total':1},'uncertainty':None,'failure':None}
    monkeypatch.setattr('moin_benchmark.adapters.process',process)
    r=b.run('development','baseline')
    assert r['recorded']==11 and r['reused']==1 and len(calls)==11
    assert '0.wav' not in calls
    assert b.result_path('development','baseline','clip-0').read_bytes()==original


def nine_clip_benchmark(setup, tmp_path):
    original, clips, configs = setup
    save(original.corpus/'corpus.json', clips[:9])
    save(original.corpus/'protocol.json', {'mode':'nine-clip-comparison'})
    b = Benchmark(original.corpus, tmp_path/'nine-private')
    b.lock(configs)
    return b


def test_nine_clip_comparison_counts_and_no_independent_claim(setup, tmp_path):
    from moin_benchmark.reporting import markdown
    b = nine_clip_benchmark(setup, tmp_path)
    assert len(validate_corpus(b.corpus, 'development')) == 9
    assert b.run('development', 'baseline')['recorded'] == 9
    review(b, 'development', tmp_path, misses=1)
    report = b.report('development')
    languages = report['candidates'][0]['languages']
    assert languages['en']['faithful'] == languages['en']['total'] == 9
    assert languages['fr']['faithful'] == 8
    assert languages['fr']['total'] == 9
    assert report['quality_claim_90_percent'] is False
    assert report['protocol']['final_clips'] == 0
    assert 'same nine clips' in report['limitations']
    assert '9/9' in markdown(report) and '8/9' in markdown(report)
    for action in (lambda: b.run('final','moin'), lambda: b.report('final'),
                   lambda: validate_corpus(b.corpus,'final',final_allowed=True)):
        with pytest.raises(BenchmarkError, match='no separate final'):
            action()


def test_nine_clip_profile_cannot_change_after_lock(setup, tmp_path):
    b = nine_clip_benchmark(setup, tmp_path)
    (b.corpus/'protocol.json').unlink()
    with pytest.raises(BenchmarkError, match='Protocol changed'):
        b.run('development','baseline')


def test_nine_clip_profile_rejects_wrong_count(setup, tmp_path):
    b = nine_clip_benchmark(setup, tmp_path)
    clips = json.loads((b.corpus/'corpus.json').read_text())
    save(b.corpus/'corpus.json', clips[:8])
    with pytest.raises(BenchmarkError, match='exactly 9'):
        validate_corpus(b.corpus, 'development')


def test_readiness_audit_is_blind_and_does_not_change_evidence(setup, tmp_path):
    from tools.check_v1 import check, main
    b = nine_clip_benchmark(setup, tmp_path)
    b.run('development', 'baseline')
    package = tmp_path/'anonymous-review'
    b.package('development', package)
    paths = list(b.work.rglob('*.json')) + [package/'review.json']
    before = {p: p.read_bytes() for p in paths}
    status = check(b.corpus, b.work, package)
    assert status['integrity'] == 'passed'
    assert status['judgements_required'] == 18
    assert status['labels_in_exported_file'] == 0
    assert status['human_review_submitted'] is False
    assert 'Private provider name' not in json.dumps(status)
    assert 'baseline' not in json.dumps(status)
    assert main(['--corpus', str(b.corpus), '--workspace', str(b.work), '--package', str(package)]) == 3
    assert {p: p.read_bytes() for p in paths} == before


def test_readiness_audit_detects_swapped_review_audio(setup, tmp_path):
    from tools.check_v1 import check
    b = nine_clip_benchmark(setup, tmp_path)
    b.run('development', 'baseline')
    package = tmp_path/'anonymous-review'
    b.package('development', package)
    audio = sorted((package/'audio').glob('*.wav'))
    audio[0].write_bytes(audio[1].read_bytes())
    with pytest.raises(BenchmarkError, match='Review audio changed'):
        check(b.corpus, b.work, package)
