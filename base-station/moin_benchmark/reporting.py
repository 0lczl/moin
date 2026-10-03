"""Human-readable evidence report derived only from completed blind judgements."""
import json


def markdown(report):
    def cell(value):
        return str(value).replace('|', '\\|').replace('\n', ' ')
    lines = [f"# Moin V1 — {report['split']} evidence", '',
             '| Candidate | English faithful | French faithful | Failures | Withheld | Median / max ms |',
             '| --- | ---: | ---: | ---: | ---: | ---: |']
    for c in report['candidates']:
        en,fr = c['languages']['en'],c['languages']['fr']
        t=c['timing_ms']
        lines.append(f"| {cell(c['name'])} ({cell(c['candidate'])}; {c['anonymous_label']}) | {en['faithful']}/{en['total']} | {fr['faithful']}/{fr['total']} | {c['failures']} | {c['withheld']} | {t['median']:.1f} / {t['max']:.1f} |")
    lines += ['', report['protocol']['method'], '', report['limitations'], '']
    if report['split']=='final':
        for c in report['candidates']:
            for lang in ('en','fr'):
                earned=c['languages'][lang]['earned_90_percent']
                lines.append(f"- {lang.upper()} 18/20 threshold: {'earned' if earned else 'MISSED'}.")
        lines += ['', '90% quality claim: ' + ('earned for this final sample.' if report['quality_claim_90_percent'] else 'NOT earned.'), '']
    for label,meaning in report['protocol']['rubric'].items():
        lines.append(f'- **{label}**: {meaning}')
    lines += ['', '## Reproducibility and per-language errors', '',
              'The following non-secret record includes exact configurations, run dates, runtime versions, stage timings, and error counts.', '',
              '```json', json.dumps(report,ensure_ascii=False,indent=2), '```', '']
    return '\n'.join(lines)
