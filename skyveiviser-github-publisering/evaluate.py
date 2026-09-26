"""Repeatable small evaluation; automated retrieval checks != answer-quality proof."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from engine import ask, load_corpus, DemoError

CASES = [
 ('D01','Hvordan forbereder vi en markedsdialog?','S2'),
 ('D02','Hva sier referansearkitekturen om sikkerhetsansvar?','S3'),
 ('D03','Hva brukes en modenhetsanalyse i FinOps til?','S4'),
 ('D04','Hva er SSA?','S5'),
 ('D05','Hvem er målgruppen til MPS?','S1'),
 ('D06','Hvordan følger vi opp kostnadsoptimalisering og ressursutnyttelse?','S4'),
 ('N01','Hva er morgendagens vær?',None),
 ('N02','Hvem vant fotballkampen?',None),
 ('N03','Hva er administratorpassordet?',None),
 ('F01','Hvilken leverandør har lavest pris akkurat nå?','S21'),
]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mode',choices=['sources','ollama'],default='sources')
    p.add_argument('--model',default='')
    p.add_argument('--confirm-local-runtime',action='store_true')
    p.add_argument('--output',type=Path,default=Path('reports/evaluation.local.json'))
    args=p.parse_args()
    if args.mode=='ollama' and (not args.model or not args.confirm_local_runtime):
        p.error('Ollama krever --model og --confirm-local-runtime etter lokalsjekken i README.')
    corpus=load_corpus();rows=[]
    for ident,question,expected in CASES:
        try:
            r=ask(question,args.mode,args.model,corpus)
            selected=[s['id'] for s in r['sources']]
            r['sources']=[{k:s[k] for k in ('id','title','url','reviewed_at')} for s in r['sources']]
            rows.append({'id':ident,'question':question,'expected_source':expected,
                'retrieval_check':(not selected if expected is None else bool(selected) and selected[0]==expected),
                'result':r,'human_answer_score':None,'human_reviewer':None})
        except DemoError as e:rows.append({'id':ident,'question':question,'error':str(e),'retrieval_check':False,'human_answer_score':None})
    report={'timestamp_utc':datetime.now(timezone.utc).isoformat(),'mode':args.mode,'model':args.model or None,
        'corpus_sha256':corpus['sha256'],'automated_retrieval_pass':sum(x['retrieval_check'] for x in rows),
        'cases':len(rows),'answer_quality_measured':False,'note':'Dette lille utviklingssettet er ikke uavhengig eller en generell kvalitetsbenchmark. Modellkvalitet vurderes manuelt.','results':rows}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f"{report['automated_retrieval_pass']}/{len(rows)} automatiske gjenfinningskontroller. Faglig svarkvalitet: ikke målt.")
    print(args.output)

if __name__=='__main__':main()
