"""Sanity gate for the checked-in synthetic fixture only; not a research benchmark."""
import argparse
import json
from pathlib import Path


def main():
    p=argparse.ArgumentParser();p.add_argument('--report',required=True);a=p.parse_args()
    path=Path(a.report);r=json.loads(path.read_text(encoding='utf-8'))
    if r['course']['data_kind']!='synthetic' or {c['id'] for c in r['comments']}!={f'c{i:06d}' for i in range(1,16)}:
        raise ValueError('仅适用于本仓库15条有效合成用例')
    question_ids={f'c{i:06d}' for i in (1,2,5,6,8,10,11,13,14)}
    positive_ids={f'c{i:06d}' for i in (3,9,15)}
    predicted={q['comment_id'] for q in r['questions']}
    positive=set(r['positive_comment_ids'])
    errors={'question_false_positive':sorted(predicted-question_ids),'question_missed':sorted(question_ids-predicted),
            'positive_missed':sorted(positive_ids-positive),'positive_false_positive':sorted(positive-positive_ids)}
    result={'scope':'开发者预设合成用例检查，不是独立标注集准确率',
            'expected_question_comments':len(question_ids),'predicted_question_comments':len(predicted),
            'errors':errors,'passed':not any(errors.values())}
    r['synthetic_semantic_check']=result
    path.write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
    (path.parent/'semantic_check.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    template=(Path(__file__).resolve().parents[1]/'web/report.html').read_text(encoding='utf-8')
    encoded=json.dumps(r,ensure_ascii=False).replace('&','\\u0026').replace('<','\\u003c').replace('>','\\u003e')
    (path.parent/'index.html').write_text(template.replace('__REPORT_DATA__',encoded),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False));return 0 if result['passed'] else 2


if __name__=='__main__':raise SystemExit(main())
