"""Explicit local request corpus import, grouped holdouts and honest evidence labels."""
import json
from .request import validate_request,_unique
from .registry import digest


def import_requests(text,*,source='player'):
    if source not in ('player','developer','synthetic'):raise ValueError('Unknown request source')
    if not isinstance(text,str) or len(text.encode())>1<<20:raise ValueError('Request import capped at1MiB')
    rows=json.loads(text,object_pairs_hook=_unique,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('Nonfinite JSON')))
    if not isinstance(rows,list) or not 1<=len(rows)<=1000:raise ValueError('Expected1..1000 annotated requests')
    result=[];seen=set()
    for row in rows:
        if not isinstance(row,dict) or set(row)-{'participant','request','annotation','source'} or not {'participant','request'}<=set(row):
            raise ValueError('Expected participant and request; optional annotation/source')
        participant=row['participant'];annotation=row.get('annotation','')
        if not isinstance(participant,str) or not 1<=len(participant)<=80:raise ValueError('Participant requires a bounded pseudonym')
        if not isinstance(annotation,str) or len(annotation)>2000:raise ValueError('Annotation capped at2000 characters')
        if row.get('source',source)!=source:raise ValueError('Mixed request provenance')
        request=validate_request(row['request']);key=digest([participant,request])
        if key in seen:continue
        seen.add(key);result.append(dict(participant=participant,request=request,annotation=annotation,source=source,request_id=key))
    return dict(revision='catalog-usefulness-v1',source=source,cases=result,sha256=digest(result),
                note='User-supplied requests; source declaration is provenance, not independent participant authentication')


def split_groups(corpus,*,salt='catalog-player-holdout-v1'):
    if corpus['sha256']!=digest(corpus['cases']):raise ValueError('Corpus checksum mismatch')
    groups=sorted({r['participant'] for r in corpus['cases']},key=lambda p:digest([salt,p]))
    if corpus['source']!='player' or len(groups)<5:
        return dict(status='not_evaluated',reason='Need at least5 independently supplied participant groups; developer/synthetic cases do not establish player demand',
                    participants=len(groups),train=[],heldout=[])
    heldout=set(groups[:max(1,len(groups)//5)])
    return dict(status='split_ready_not_demand_validated',participants=len(groups),
        train=[r['request_id'] for r in corpus['cases'] if r['participant'] not in heldout],
        heldout=[r['request_id'] for r in corpus['cases'] if r['participant'] in heldout],
        note='Participant groups kept disjoint. Evaluation must also account for overlapping world groups; no automatic fitting or promotion.')
