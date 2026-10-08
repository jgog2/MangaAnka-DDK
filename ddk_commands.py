"""Bounded deterministic console grammar. Parsing never writes to the database."""
from decimal import Decimal
import re
import shlex

HELP = '''Commands apply to the open title. Edits PREVIEW; click Apply to commit.
Paste multiple edit lines and click Preview Command for one atomic transaction.
guard database_uuid 123e4567-e89b-12d3-a456-426614174000 audit 42 revision 3 database a42-e7-d0-w25
select chapter 222 | select chapters 1,3,5,10.5,12-16 | select volume 24
select unmapped | conflicts | modified | missing-title | all
clear selection
set volume 24 (uses selected rows) | set volume 24 selected | set volume 24 chapters 222-232
clear volume selected | clear volume chapters 222-232
reset volume selected  (remove override and restore automatic value)
reset type selected | reset title chapter 10 | reset source-note selected
set type chapter|bonus|extra|omake|special selected
set title "Exact title here" chapter 222
set source-note "Verified against official TOC" selected
set verification reviewed|verified selected | set work verification reviewed|verified
add evidence source "Publisher" url "https://example.org/toc" selected
add evidence source "Second source" note "Volume contents" chapter 275
add chapter 206 | add chapters 206-207 | remove curated chapter 206
renumber chapter 10.5 to 10.6
add volume 24 | remove curated volume 24
set volume-title 24 "Exact title" | set volume-source-note 24 "Verified TOC"
set work edition standard | set work language en | set work canonical-title "Exact title"
add alias "Exact alias" | remove alias "Exact alias"
set id anilist 12345 | clear id anilist | reset id anilist
set expected chapters 207 | set expected volumes 23 | reset expected chapters
show aliases | show ids | show expected | show effective chapter 222
show provenance chapter 222 | explain chapter 222 | explain volume 24 | explain work
show chapter 222 | show volume 24 | show unmapped | show conflicts
show modified | show automatic | show curated
validate | save | audit | undo | redo
on "Exact title" set volume 24 chapters 222-232
on "Exact title" select chapter 222 | on "Exact title" set volume 24 selected

Ranges include existing numeric rows between both endpoints, including decimals.
Endpoints must exist; a range never creates chapters. No fuzzy title matching.
Explicit titles must identify exactly one edition/language row; otherwise open it first.
clear volume stores an explicit empty mapping. reset volume removes the override.
UNVERIFIED changes are drafts. REVIEWED / VERIFIED changes affect resolution.
Undo/redo are per-title and previewed. Apply saves immediately; save validates saved data.
Curated chapter/volume creation never fabricates downloadable acquisition.
In a multiline batch, select and edit lines share one in-memory selection; validate may be last.
Any invalid line blocks the entire preview. Apply writes all previewed edits in one transaction.
Ctrl+Enter runs the multiline console; Preview Command also works.
'''


def parse(command):
    try: tokens=shlex.split(command,posix=True)
    except ValueError as exc: raise ValueError('Invalid quoting: '+str(exc)) from exc
    if not tokens: raise ValueError('Enter a command.')
    title=None
    if tokens[0]=='on':
        if len(tokens)<3: raise ValueError('Expected on "Exact title" command.')
        title=tokens[1];tokens=tokens[2:]
    verb=tokens[0]
    if verb=='supplement':
        from ddk_supplementary_commands import parse_supplement
        result=parse_supplement(tokens)
    elif (len(tokens)==9 and tokens[0]=='guard' and tokens[1]=='database_uuid' and
        re.fullmatch(r'[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}',tokens[2]) and
        tokens[3]=='audit' and tokens[4].isdigit() and tokens[5]=='revision' and
        tokens[6].isdigit() and tokens[7]=='database' and
        re.fullmatch(r'a\d+-e\d+-d\d+-w\d+(?:-s\d+)?',tokens[8])):
        result={'action':'guard','database_uuid':tokens[2].lower(),'audit_id':int(tokens[4]),
                'audit_revision':int(tokens[6]),'database_revision':tokens[8]}
    elif verb=='guard':
        raise ValueError('Guard must include database_uuid, audit, revision, and database revision; export a fresh packet.')
    elif tokens[:3]==['add','evidence','source']:
        if len(tokens)<5 or not tokens[3].strip():raise ValueError('Evidence needs an exact source name and chapter scope.')
        data={'source_name':tokens[3],'source_url':'','note':'','accessed_at':''}
        rest=tokens[4:]
        while len(rest)>=2 and rest[0] in ('url','note','accessed'):
            field={'url':'source_url','note':'note','accessed':'accessed_at'}[rest[0]]
            if data[field]:raise ValueError('Duplicate evidence attribute.')
            data[field]=rest[1];rest=rest[2:]
        scope=target(rest)
        if scope[0] not in ('selected','chapter','chapters'):
            raise ValueError('Evidence scope must be selected chapters or exact chapter identifiers.')
        result={'action':'evidence','target':scope,**data}
    elif tokens==['clear','selection']: result={'action':'select','target':['none']}
    elif verb in ('validate','save','audit','undo','redo') and len(tokens)==1: result={'action':verb}
    elif tokens[:2] in (['add','chapter'],['add','chapters'],['add','volume'],
                         ['remove','alias'],['add','alias']):
        if len(tokens)!=3: raise ValueError('Expected one exact record or alias.')
        result={'action':'record' if tokens[1]!='alias' else 'alias',
                'operation':verb,'kind':tokens[1],'value':tokens[2]}
    elif len(tokens)==4 and tokens[:2]==['remove','curated'] and tokens[2] in ('chapter','chapters','volume'):
        result={'action':'record','operation':'remove','kind':tokens[2],'value':tokens[3]}
    elif len(tokens)==5 and tokens[:2]==['renumber','chapter'] and tokens[3]=='to':
        result={'action':'renumber','old':tokens[2],'new':tokens[4]}
    elif len(tokens)==4 and tokens[:2]==['set','verification']:
        result={'action':'verify','value':tokens[2].upper(),'target':target(tokens[3:])}
    elif len(tokens)==4 and tokens[:3]==['set','work','verification']:
        result={'action':'verify_work','value':tokens[3].upper()}
    elif len(tokens)==4 and tokens[:2]==['set','work'] and tokens[2] in ('edition','language','canonical-title','canonical-work-id','publication-context'):
        result={'action':'work_edit','field':tokens[2].replace('-','_'),'value':tokens[3]}
    elif len(tokens)==4 and tokens[:2]==['set','expected'] and tokens[2] in ('chapters','volumes'):
        result={'action':'work_edit','field':'expected_'+tokens[2],'value':tokens[3]}
    elif len(tokens)==3 and tokens[:2]==['reset','expected'] and tokens[2] in ('chapters','volumes'):
        result={'action':'work_edit','field':'expected_'+tokens[2],'reset':True}
    elif len(tokens)==4 and tokens[:2]==['set','id']:
        result={'action':'id_edit','operation':'set','source':tokens[2],'value':tokens[3]}
    elif len(tokens)==3 and tokens[:2] in (['clear','id'],['reset','id']):
        result={'action':'id_edit','operation':verb,'source':tokens[2]}
    elif len(tokens)==4 and tokens[:2] in (['set','volume-title'],['set','volume-source-note']):
        result={'action':'volume_edit','field':tokens[1][7:].replace('-','_'),'key':tokens[2],'value':tokens[3]}
    elif verb=='explain' and len(tokens) in (2,3):
        result={'action':'inspect','view':'explain','target':tokens[1:]}
    elif verb=='show' and len(tokens)>=2 and tokens[1] in ('aliases','ids','expected','effective','provenance'):
        result={'action':'inspect','view':tokens[1],'target':tokens[2:]}
    elif verb in ('select','show'):
        result={'action':verb,'target':target(tokens[1:])}
    elif verb in ('set','clear','reset'):
        if len(tokens)<3: raise ValueError('Incomplete edit command.')
        field={'source-note':'source_note'}.get(tokens[1],tokens[1])
        if field not in ('volume','title','type','source_note'): raise ValueError('Unsupported console field.')
        if verb=='clear' and field=='type': raise ValueError('Type cannot be cleared; use reset.')
        value=tokens[2] if verb=='set' else None
        scope_tokens=tokens[3:] if verb=='set' else tokens[2:]
        scope=target(scope_tokens or ['selected'])
        if scope[0] not in ('selected','chapter','chapters'): raise ValueError('Edit scope must be selected or an exact chapter/range.')
        result={'action':'edit','field':field,'value':value,'reset':verb=='reset','target':scope}
    else: raise ValueError('Unknown command. Open Command Help for the exact grammar.')
    result['title']=title
    return result


def parse_batch(source):
    lines=[line.strip() for line in source.splitlines() if line.strip()]
    if not lines: raise ValueError('Enter a command.')
    parsed=[parse(line) for line in lines]
    if any(c['action']=='guard' for c in parsed[1:]):
        raise ValueError('A revision guard must be the first line.')
    if parsed[0]['action']=='guard' and len(parsed)==1:
        raise ValueError('A revision guard needs an edit command.')
    return parsed


def target(tokens):
    if len(tokens)==1 and tokens[0] in ('selected','all','unmapped','conflicts','modified','missing-title','automatic','curated'):
        return tokens
    if len(tokens)==2 and tokens[0] in ('chapter','chapters','volume'):
        if tokens[0]=='chapters':
            for part in tokens[1].split(','):
                match=re.fullmatch(r'(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)',part)
                if match:
                    if Decimal(match[1])>Decimal(match[2]): raise ValueError('Invalid ascending chapter range.')
                elif not re.fullmatch(r'\d+(?:\.\d+)?',part):
                    raise ValueError('Invalid chapter set/range.')
        elif not re.fullmatch(r'\d+(?:\.\d+)?',tokens[1]): raise ValueError('Expected exact numeric chapter/volume.')
        return tokens
    raise ValueError('Unknown selection or navigation scope.')


def matches(row, scope):
    kind=scope[0]; value=row['effective']
    if kind=='all': return True
    if kind=='none': return False
    if kind=='unmapped': return not row['missing'] and value.get('volume') in (None,'')
    if kind=='conflicts': return row['conflict']
    if kind in ('modified','curated'): return bool(row['curated'])
    if kind=='automatic': return not row['curated']
    if kind=='missing-title': return not value.get('title')
    if kind=='missing': return row['missing']
    text=str(value.get('volume') if kind=='volume' else value.get('chapter'))
    try: number=Decimal(text)
    except Exception: return False
    if not number.is_finite(): return False
    if kind=='chapters':
        for part in scope[1].split(','):
            if '-' in part:
                low,high=map(Decimal,part.split('-'))
                if low<=number<=high: return True
            elif number==Decimal(part): return True
        return False
    try: return number==Decimal(scope[1])
    except Exception: return False


def scoped_rows(rows, scope, selected=()):
    if scope[0]=='selected': result=[r for r in rows if r['iid'] in selected]
    else: result=[r for r in rows if matches(r,scope)]
    if scope[0]=='chapters':
        for part in scope[1].split(','):
            endpoints=part.split('-')
            if any(not any(matches(r,['chapter',end]) for r in rows) for end in endpoints):
                raise ValueError('Every chapter or range endpoint must exist in the current title.')
    return result


def title_scope(db, current, explicit):
    if explicit is None:
        if current is None: raise ValueError('Open a title first.')
        return current
    found=[r['id'] for r in db.works() if explicit in (r['input_title'],r['canonical_title'],r['match_title'])]
    if len(found)!=1: raise ValueError('Explicit title must match exactly one title/edition/language record.')
    return found[0]
