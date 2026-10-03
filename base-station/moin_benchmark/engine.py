"""Append-only benchmark workflow; the private workspace is operator-only."""
from __future__ import annotations
import random
import shutil
import statistics
import time
from pathlib import Path
from . import adapters, safety
from .core import (BenchmarkError, require, read, write_new, digest, identifier,
                   secret_free, now, registry, validate_corpus, audio_path, corpus_counts, require_split)

LABELS = ('faithful', 'partly_wrong', 'serious_meaning_error')
PROTOCOL = {
    'version': 'moin-v1-1', 'development_clips': 12, 'final_clips': 20,
    'languages': ['en', 'fr'], 'passing_label': 'faithful',
    'rubric': {
        'faithful': 'Preserves intended meaning, including religious claims; word order need not match.',
        'partly_wrong': 'Meaning is partly altered, omitted, invented, or materially softened.',
        'serious_meaning_error': 'False religious claim, reversed meaning, wrong Qur’an handling, or confident fabrication.'},
    'method': 'A bilingual Arabic-English-French human reviews anonymous systems independently in each language. Identities are revealed only after all development judgements are submitted. Failures and withheld outputs cannot pass.',
    'final_gate': 'At least 18 faithful out of 20 separately in English AND French. No overall average can earn this claim.',
}


class Benchmark:
    def __init__(self, corpus, workspace):
        self.corpus, self.work = Path(corpus), Path(workspace)

    def protocol(self):
        counts = corpus_counts(self.corpus)
        if counts['final']:
            return PROTOCOL
        return {**PROTOCOL, 'version': 'moin-v1-nine-clip-comparison',
                'development_clips': 9, 'final_clips': 0,
                'final_gate': 'No held-out test. Report English and French faithful counts out of nine; no independent 90% quality claim.',
                'limitations': 'The same nine clips are used for model selection and evaluation. Results describe this sample only, not unseen-audio performance.'}

    def lock(self, configs_path):
        require(not (self.work / 'comparison.json').exists(), 'Comparison already locked; use a new workspace for a new development comparison')
        configs = read(configs_path)
        require(isinstance(configs, list) and 1 <= len(configs) <= 4, 'Lock one to four candidate configurations')
        seen = set()
        for c in configs:
            identifier(c.get('id'))
            require(c['id'] not in seen and c['id'] != 'moin', 'Duplicate or reserved candidate ID')
            seen.add(c['id'])
            secret_free(c)
            adapters.validate_config(c)
        validate_corpus(self.corpus, 'development')
        clips = registry(self.corpus)
        require(sum(c['split'] == 'final' for c in clips) == corpus_counts(self.corpus)['final'], 'Final clip count does not match the selected protocol')
        write_new(self.work / 'comparison.json', {
            'locked_at': now(), 'protocol': self.protocol(), 'corpus_identity': digest(clips),
            'implementation_identity': self.implementation_identity(), 'runtime': adapters.runtime_identity(),
            'candidates': {c['id']: {'config': c, 'identity': digest(c)} for c in configs}})
        return {'locked': list(seen), 'protocol': self.protocol()}

    @staticmethod
    def implementation_identity():
        return digest({p.name: p.read_text() for p in Path(__file__).parent.glob('*.py')})

    def comparison(self):
        data = read(self.work / 'comparison.json')
        require(data['protocol'] == self.protocol(), 'Protocol changed after comparison lock')
        require(data['implementation_identity'] == self.implementation_identity(), 'Benchmark implementation changed after comparison lock')
        require(data['runtime'] == adapters.runtime_identity(), 'Benchmark runtime changed after comparison lock')
        require(data['corpus_identity'] == digest(registry(self.corpus)), 'Corpus changed after lock; start a new comparison')
        for c in data['candidates'].values():
            require(digest(c['config']) == c['identity'], 'Locked candidate was altered')
        return data

    def composition(self):
        c = read(self.work / 'composition.json')
        require(digest(c['composition']) == c['identity'], 'Composition was altered')
        comparison = self.comparison()
        require(c['composition']['selected_identity'] == comparison['candidates'][c['composition']['selected_candidate']]['identity'], 'Selected candidate changed')
        return c

    def frozen(self):
        require_split(self.corpus, 'final')
        require((self.work / 'freeze.json').exists(), 'Final access requires a frozen Moin composition')
        f = read(self.work / 'freeze.json')
        c = self.composition()
        require(f['identity'] == c['identity'], 'Only the frozen composition is eligible')
        require(c['composition']['implementation_identity'] == digest({p.name: p.read_text() for p in Path(__file__).parent.glob('*.py')}), 'Implementation changed after composition freeze')
        return c

    def run(self, split, candidate, clip_id=None):
        require(split in ('development', 'final'), 'Unknown split')
        require_split(self.corpus, split)
        identifier(candidate)
        if clip_id is not None:
            identifier(clip_id)
        comparison = self.comparison()
        composition = None
        if split == 'final':
            require(candidate == 'moin' and clip_id is None, 'Final requires the full frozen Moin run')
            require((self.work / 'freeze.json').exists(), 'Final access requires a frozen Moin composition')
            composition = self.frozen()
            require(not (self.work / 'final-started.json').exists(), 'Final run already consumed; no rerun or replacement is permitted')
        elif candidate == 'moin':
            composition = self.composition()
        if composition:
            cfg = composition['composition']['config']
            identity = composition['identity']
        else:
            require(candidate in comparison['candidates'], 'Unknown locked candidate')
            cfg = comparison['candidates'][candidate]['config']
            identity = comparison['candidates'][candidate]['identity']
        clips = validate_corpus(self.corpus, split, final_allowed=composition is not None and split == 'final')
        if clip_id:
            clips = [c for c in clips if c['id'] == clip_id]
            require(clips, 'Unknown clip in requested split')
        pending = []
        for clip in clips:
            path = self.result_path(split, candidate, clip['id'])
            if path.exists():
                require(split == 'development' and clip_id is None, 'Result already recorded; no substitution allowed')
                existing = read(path)
                self.validate_result(existing)
                require(existing['configuration_identity'] == identity and existing['audio_sha256'] == clip['sha256'] and existing['clip_id'] == clip['id'] and existing['candidate'] == candidate, 'Existing result identity mismatch')
            else:
                pending.append(clip)
        reused = len(clips) - len(pending)
        clips = pending
        if split == 'final':
            write_new(self.work / 'final-started.json', {'identity': identity, 'started_at': now(), 'clips': [c['id'] for c in clips]})
        for clip in clips:
            started = time.perf_counter()
            safety_ms = 0.0
            def guard(arabic):
                nonlocal safety_ms
                gate_started = time.perf_counter()
                decision = safety.route(arabic, '', '', None, composition['composition']['renderings'])
                safety_ms += (time.perf_counter() - gate_started) * 1000
                return None if decision['outcome'] == 'ordinary_translation' else decision
            try:
                kwargs = {'translation_guard': guard} if composition else {}
                result = adapters.process(cfg, audio_path(self.corpus, clip), **kwargs)
                self.validate_result(result)
            except Exception:
                result = {'arabic':'', 'en':'', 'fr':'', 'timing_ms':{'total':0},
                          'uncertainty':'candidate_failure',
                          'failure':{'stage':'candidate','code':'candidate_failure','message':'Candidate failed or returned malformed output','retryable':False}}
            if composition:
                gate_started = time.perf_counter()
                decision = safety.route(result['arabic'], result['en'], result['fr'], result['uncertainty'] or ('provider_failure' if result['failure'] else None), composition['composition']['renderings'])
                result.update(en=decision['en'] or '', fr=decision['fr'] or '', safety=decision)
                safety_ms += (time.perf_counter() - gate_started) * 1000
                result['timing_ms']['safety'] = round(safety_ms, 3)
            result['timing_ms']['total'] = round((time.perf_counter() - started) * 1000, 3)
            # Audio only goes to adapters; reference transcripts are never supplied.
            write_new(self.result_path(split, candidate, clip['id']), {
                'runtime': comparison['runtime'], 'clip_id': clip['id'], 'audio_sha256': clip['sha256'], 'candidate': candidate,
                'configuration_identity': identity, 'date': now(), **result})
        return {'recorded': len(clips), 'reused': reused, 'candidate': candidate, 'split': split}

    def finalize_interrupted(self):
        """Seal unprocessed final clips as failures; never call a candidate again."""
        composition = self.frozen()
        attempt = read(self.work / 'final-started.json')
        clips = [c for c in registry(self.corpus) if c['split'] == 'final']
        require(attempt['identity'] == composition['identity'] and attempt['clips'] == [c['id'] for c in clips], 'Final attempt identity mismatch')
        missing = [c for c in clips if not self.result_path('final','moin',c['id']).exists()]
        require(missing, 'Final attempt already has all results')
        for clip in missing:
            write_new(self.result_path('final','moin',clip['id']), {
                'clip_id':clip['id'], 'audio_sha256':clip['sha256'], 'candidate':'moin',
                'configuration_identity':composition['identity'], 'date':now(),
                'runtime':self.comparison()['runtime'], 'arabic':'', 'en':'', 'fr':'',
                'timing_ms':{'total':0}, 'uncertainty':'interrupted_final_attempt',
                'failure':{'stage':'candidate','code':'interrupted_final_attempt',
                           'message':'Final attempt interrupted; no output available and no retry performed', 'retryable':False},
                'safety':{'outcome':'withheld','en':None,'fr':None,'reason':'interrupted_final_attempt','sources':[]}})
        return {'recorded_failures':len(missing),'provider_calls':0}

    @staticmethod
    def validate_result(r):
        require(isinstance(r, dict), 'Malformed adapter result')
        require(all(isinstance(r.get(k), str) for k in ('arabic','en','fr')), 'Malformed adapter text')
        require(isinstance(r.get('timing_ms'), dict) and all(isinstance(v, (int,float)) and 0 <= v < float('inf') for v in r['timing_ms'].values()), 'Malformed adapter timing')
        require(r.get('uncertainty') is None or isinstance(r['uncertainty'], str), 'Malformed uncertainty')
        require(r.get('failure') is None or isinstance(r['failure'], dict), 'Malformed failure')

    def result_path(self, split, candidate, clip):
        return self.work / 'runs' / split / candidate / f'{clip}.json'

    def results(self, split):
        require_split(self.corpus, split)
        comparison = self.comparison()
        candidates = comparison['candidates'] if split == 'development' else {'moin': self.frozen()}
        clips = [c for c in registry(self.corpus) if c['split'] == split]
        results = []
        for cid, candidate in candidates.items():
            for clip in clips:
                path = self.result_path(split, cid, clip['id'])
                require(path.exists(), f'Missing run: {cid}/{clip["id"]}')
                r = read(path)
                require(r['clip_id'] == clip['id'] and r['candidate'] == cid, 'Result clip/candidate mismatch')
                require(r['configuration_identity'] == candidate['identity'] and r['audio_sha256'] == clip['sha256'], 'Result identity mismatch')
                self.validate_result(r)
                results.append(r)
        return results

    def package(self, split, output):
        require(split in ('development', 'final'), 'Invalid review split')
        output = Path(output).resolve()
        require(not output.exists(), 'Review destination must be new')
        require(not output.is_relative_to(self.work.resolve()) and not output.is_relative_to(self.corpus.resolve()), 'Export reviewer material outside the private workspace and corpus')
        results = self.results(split)
        require(not (self.work / f'{split}-review-map.json').exists(), 'A review package already exists')
        candidates = sorted({r['candidate'] for r in results})
        random.SystemRandom().shuffle(candidates)
        labels = {c: f'System-{i+1}' for i,c in enumerate(candidates)}
        clips = {c['id']: c for c in registry(self.corpus) if c['split'] == split}
        clip_labels = {cid: f'Clip-{i+1:02}' for i,cid in enumerate(clips)}
        items, mapping = [], {}
        output.mkdir(parents=True)
        (output / 'audio').mkdir()
        for cid, clip in clips.items():
            shutil.copyfile(audio_path(self.corpus, clip), output / 'audio' / f'{clip_labels[cid]}.wav')
        random.SystemRandom().shuffle(results)
        for r in results:
            for lang in ('en','fr'):
                item_id = f'item-{len(items)+1:04}'
                item = {'id': item_id, 'system': labels[r['candidate']], 'clip': clip_labels[r['clip_id']],
                        'audio': f'audio/{clip_labels[r["clip_id"]]}.wav', 'language': lang,
                        'text': r[lang], 'rendering_source': r.get('safety',{}).get('sources',{}).get(lang,{}) if isinstance(r.get('safety',{}).get('sources'),dict) else {}, 'unavailable': bool(not r[lang].strip() or (r['failure'] and r['failure'].get('stage') not in ({'en','fr'} - {lang})) or r.get('safety',{}).get('outcome') == 'withheld'),
                        'label': None, 'comment': ''}
                items.append(item)
                mapping[item_id] = {'candidate': r['candidate'], 'clip_id': r['clip_id'], 'language': lang,
                                    'result_identity': digest(r), 'unavailable': item['unavailable']}
        package = {'protocol': self.protocol(), 'items': items}
        write_new(output / 'review.json', package)
        write_new(self.work / f'{split}-review-map.json', {'created_at': now(), 'labels': labels, 'items': mapping, 'package': package})
        (output / 'README.txt').write_text('Listen to each audio file. Set each label in review.json to faithful, partly_wrong, or serious_meaning_error; add an optional comment. Return the JSON to the operator. Do not change other fields. No candidate identities are supplied.\n')
        return {'package': str(output / 'review.json'), 'judgements': len(items)}

    def submit(self, split, review_path, reviewer):
        require(isinstance(reviewer,str) and reviewer.strip(), 'Reviewer identity required')
        secret_free(reviewer)
        mapping = read(self.work / f'{split}-review-map.json')
        submitted = read(review_path)
        expected = mapping['package']
        require(submitted.get('protocol') == expected['protocol'], 'Review protocol changed')
        items = submitted.get('items', [])
        require(isinstance(items,list) and len(items) == len(expected['items']), 'Review count mismatch')
        expected_by_id = {r['id']: r for r in expected['items']}
        seen = set()
        for row in items:
            key = row.get('id')
            require(key in expected_by_id and key not in seen, 'Unknown or duplicate review item')
            seen.add(key)
            require({k:v for k,v in row.items() if k not in ('label','comment')} == {k:v for k,v in expected_by_id[key].items() if k not in ('label','comment')}, 'Review source/output changed')
            require(row.get('label') in LABELS, f'Missing or invalid label: {row.get("system")}/{row.get("clip")}/{row.get("language")} ({key})')
            require(isinstance(row.get('comment',''),str), 'Invalid review comment')
            require(not mapping['items'][key]['unavailable'] or row['label'] != 'faithful', 'Failed or withheld output cannot pass')
        write_new(self.work / f'{split}-reviews.json', {'reviewer': reviewer, 'submitted_at': now(), 'items': items})
        return {'submitted': len(items), 'immutable': True}

    def report(self, split):
        results = self.results(split)
        map_path = self.work / f'{split}-review-map.json'
        require(map_path.exists(), 'Create the blind review package first')
        mapping = read(map_path)
        review_path = self.work / f'{split}-reviews.json'
        require(review_path.exists(), 'Incomplete review: submit all clip/language labels before revealing identities; missing: ' + ', '.join(mapping['items']))
        reviews = read(review_path)
        by_key = {(r['candidate'],r['clip_id']): r for r in results}
        scores = {}
        require(len(reviews['items']) == len(mapping['items']) and {r['id'] for r in reviews['items']} == set(mapping['items']), 'Incomplete or duplicate stored reviews')
        for row in reviews['items']:
            meta = mapping['items'][row['id']]
            r = by_key[(meta['candidate'],meta['clip_id'])]
            require(digest(r) == meta['result_identity'], 'Run changed after blind review')
            require(row['label'] in LABELS, 'Invalid stored review')
            require(not meta['unavailable'] or row['label'] != 'faithful', 'Unavailable output cannot pass')
            counts = scores.setdefault(meta['candidate'], {}).setdefault(meta['language'], {k:0 for k in LABELS})
            counts[row['label']] += 1
        comparison = self.comparison()
        named = []
        for cid, langs in scores.items():
            records = [r for r in results if r['candidate'] == cid]
            for lang, counts in langs.items():
                n = sum(counts.values())
                require(n == require_split(self.corpus, split), 'Incomplete stored review')
                counts.update(total=n, faithful_rate=counts['faithful']/n)
                if split == 'final':
                    counts['earned_90_percent'] = counts['faithful'] >= 18 and n == 20
            times = [r['timing_ms'].get('total',0) for r in records]
            config = comparison['candidates'][cid]['config'] if cid != 'moin' else self.frozen()['composition']['config']
            named.append({'candidate': cid, 'name': config['name'] if cid != 'moin' else 'Moin Quality Pipeline',
                          'anonymous_label': mapping['labels'][cid], 'configuration': config,
                          'configuration_identity': records[0]['configuration_identity'], 'languages': langs,
                          'failures': sum(bool(r['failure']) for r in records),
                          'withheld': sum(r.get('safety',{}).get('outcome') == 'withheld' for r in records),
                          'timing_ms': {'median': statistics.median(times), 'max': max(times),
                                        'stages': {stage: {'median': statistics.median([r['timing_ms'].get(stage,0) for r in records])}
                                                   for stage in sorted(set().union(*(r['timing_ms'] for r in records))) }},
                          'run_dates': sorted({r['date'] for r in records})})
        report = {'split': split, 'protocol': self.protocol(), 'candidates': named, 'runtime': comparison['runtime'], 'implementation_identity': comparison['implementation_identity'],
                  'quality_claim_90_percent': split == 'final' and all(x['languages'][lang]['earned_90_percent'] for x in named for lang in ('en','fr')),
                  'limitations': 'Human-reviewed sample results, not a population-wide accuracy guarantee. Final-set failures remain in the denominator.'}
        if corpus_counts(self.corpus)['final'] == 0:
            report['limitations'] = self.protocol()['limitations']
        if split == 'final':
            report['composition'] = self.frozen()
        secret_free(report)
        return report

    def select(self, candidate, renderings_path):
        require(not (self.work / 'composition.json').exists(), 'Composition already selected; use a new comparison to tune further')
        self.report('development')  # complete blind scoring is a prerequisite
        comparison = self.comparison()
        require(candidate in comparison['candidates'], 'Select a locked development candidate')
        renderings = read(renderings_path)
        secret_free(renderings)
        safety.validate_renderings(renderings)
        c = comparison['candidates'][candidate]
        composition = {'selected_candidate': candidate, 'selected_identity': c['identity'], 'config': c['config'],
                       'renderings': renderings, 'safety_version': 'moin-conservative-v1',
                       'implementation_identity': digest({p.name: p.read_text() for p in Path(__file__).parent.glob('*.py')})}
        identity = digest(composition)
        write_new(self.work / 'composition.json', {'created_at': now(), 'identity': identity, 'composition': composition})
        return {'composition_identity': identity}

    def freeze(self):
        c = self.composition()
        current = digest({p.name:p.read_text() for p in Path(__file__).parent.glob('*.py')})
        require(c['composition']['implementation_identity'] == current, 'Implementation changed since composition selection')
        for clip in validate_corpus(self.corpus, 'development'):
            r = read(self.result_path('development','moin',clip['id']))
            self.validate_result(r)
            require(r['clip_id'] == clip['id'] and r['candidate'] == 'moin' and r['audio_sha256'] == clip['sha256'], 'Moin development result mismatch')
            require(r['configuration_identity'] == c['identity'], 'Run the full Moin development set before freeze')
        write_new(self.work / 'freeze.json', {'identity':c['identity'], 'frozen_at':now()})
        return {'frozen_identity': c['identity']}
