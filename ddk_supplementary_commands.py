"""Grammar 4 supplementary family; opaque targets never use chapter selection."""
import json
import re
import shlex

HELP='''Grammar 4 supplementary commands (numeric Grammar 3 commands unchanged):
supplement list
supplement inspect supplement:<sha256>
supplement candidates supplement:<sha256>
supplement history [supplement:<sha256>]
guard database_uuid UUID audit N revision R database TOKEN
supplement bind supplement:<sha256> '<exact reviewed JSON object>'
supplement membership supplement:<sha256> '<independent membership JSON object>'
supplement reject ASSERTION_UUID reviewer "Name" note "Reason"
supplement withdraw ASSERTION_UUID reviewer "Name" note "Reason"
supplement undo | supplement redo

All mutations preview and require explicit Apply. Guards must be current;
the Qt review form supplies one automatically. Numeric and supplementary edits
cannot share a batch. A final validate line is permitted. Complete JSON bodies
are shown by the review form; never substitute a title/decimal/OCR match for
complete-content evidence. Reject/withdraw preserves the original decision.
Undo/redo are a separate per-work supplementary stack.
'''


def parse_supplement(tokens):
    if len(tokens)<2:raise ValueError('Expected supplement operation.')
    verb=tokens[1];rest=tokens[2:]
    result=dict(action='supplement',operation=verb)
    if verb in ('list','undo','redo') and not rest:return result
    if verb=='history' and len(rest) in (0,1):
        result['opaque_id']=rest[0] if rest else None
    elif verb in ('inspect','candidates') and len(rest)==1:result['opaque_id']=rest[0]
    elif verb in ('bind','membership') and len(rest)==2:
        def unique_pairs(pairs):
            result={}
            for key,value in pairs:
                if key in result:raise ValueError('Duplicate JSON key: '+key)
                result[key]=value
            return result
        try:payload=json.loads(rest[1],object_pairs_hook=unique_pairs)
        except ValueError:raise ValueError('Supplementary payload must be one quoted JSON object.') from None
        if not isinstance(payload,dict):raise ValueError('Supplementary payload must be an object.')
        result.update(opaque_id=rest[0],payload=payload)
    elif verb in ('reject','withdraw') and len(rest)==5 and rest[1]=='reviewer' and rest[3]=='note':
        if not re.fullmatch(r'[0-9a-fA-F-]{36}',rest[0]):raise ValueError('Expected exact assertion UUID.')
        result.update(assertion_uuid=rest[0],reviewer=rest[2],note=rest[4])
    else:raise ValueError('Unknown supplementary command or arguments. Open Command Help.')
    if result.get('opaque_id') and not re.fullmatch(r'supplement:[0-9a-f]{64}',result['opaque_id']):
        raise ValueError('Expected exact opaque supplementary identity.')
    return result


def command_text(guard,operation,opaque_id,payload):
    return guard+'\n'+'supplement '+operation+' '+opaque_id+' '+shlex.quote(json.dumps(payload,ensure_ascii=False))+'\nvalidate'
