"""Formatting over persisted state/evaluator results, never lifecycle policy."""
from collections import Counter

ACTION_LABELS = {'CODE_REVIEW_REQUIRED':'Code review', 'RESEARCH_REQUIRED':'Research required',
    'CURATION_READY':'Open Curate', 'AUTO_RESOLVABLE':'Run audit', 'ACQUISITION_ONLY':'Acquisition only',
    'BLOCKED_IDENTITY':'Identity review', 'UNKNOWN':'Inspect evidence'}

def intake_problems(observation):
    """Present unresolved intake exactly as Problems does, without code inference.

    These observations have no trusted linked work/audit. Existing intake review
    uses identity research; explicit saved actions take precedence when present.
    """
    return [dict(h, **{'class':h.get('problem_class') or 'IDENTITY',
                       'next_action':h.get('next_action') or 'RESEARCH_REQUIRED'})
            for h in (observation or {}).get('holes') or []]



def health_label(health):
    values = set(health.values()) - {''}
    if not values: return 'Unknown'
    if 'ERROR' in values: return 'Error'
    if values == {'PASS'}: return 'Good'
    return 'Review'


def next_action(item, set_status, evaluation=None, problems=(), running=False):
    state = item['processing_status']; evaluation = evaluation or {}
    if running or state == 'AUDITING': return 'Auditing…'
    if state == 'QUEUED': return 'Re-Audit queued'
    if set_status not in ('OPEN', 'REVIEW'): return 'Reopen Working Set'
    if state in ('ACCEPTED','REJECTED') and (state == 'REJECTED' or evaluation.get('needs_reaudit')):
        return 'Reopen selected for review'
    if state == 'ERROR': return 'Retry error'
    if state == 'DUPLICATE': return 'Duplicate intake'
    if state == 'PENDING' or evaluation.get('needs_reaudit'): return 'Run Working Set'
    if evaluation.get('eligible') and state != 'ACCEPTED': return 'Accept eligible title'
    if state == 'REVIEW':
        actions = {p.get('next_action') for p in problems}
        for action in ('BLOCKED_IDENTITY','CODE_REVIEW_REQUIRED','RESEARCH_REQUIRED','CURATION_READY',
                       'AUTO_RESOLVABLE','ACQUISITION_ONLY','UNKNOWN'):
            if action in actions: return ACTION_LABELS[action]
        return 'Inspect intake' if not item.get('work_id') else 'Inspect evidence'
    if state == 'ACCEPTED': return 'In Catalog'
    if not item.get('work_id'): return 'Inspect intake'
    return 'Inspect evidence'


def summary(items, candidates):
    counts = Counter(i['processing_status'] for i in items)
    return dict(total=len(items), eligible=len(candidates), counts=dict(counts),
                unlinked=sum(not i.get('work_id') for i in items))
