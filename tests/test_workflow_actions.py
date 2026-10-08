"""Authoritative action presentation; disposable v7 catalogs, no provider calls."""
import unittest
from ddk_review import review_packet, detailed_csv
from qt_app.workflow_presentation import next_action
import test_workflow as fixtures


class ActionPresentation(unittest.TestCase):
    def label(self, actions, **kwargs):
        return next_action(dict(processing_status='REVIEW',work_id=1),'OPEN',
                           problems=[dict(next_action=a) for a in actions],**kwargs)

    def test_research_only(self):self.assertEqual('Research required',self.label(['RESEARCH_REQUIRED']))
    def test_code_only(self):self.assertEqual('Code review',self.label(['CODE_REVIEW_REQUIRED']))
    def test_research_outweighs_acquisition(self):self.assertEqual('Research required',self.label(['ACQUISITION_ONLY','RESEARCH_REQUIRED']))
    def test_code_outweighs_research_regardless_order(self):
        for actions in (['CODE_REVIEW_REQUIRED','RESEARCH_REQUIRED'],['RESEARCH_REQUIRED','CODE_REVIEW_REQUIRED']):
            self.assertEqual('Code review',self.label(actions))
    def test_acquisition_only(self):self.assertEqual('Acquisition only',self.label(['ACQUISITION_ONLY']))
    def test_class_cannot_override_action(self):
        for cls in ('IDENTITY','UNKNOWN','CODE'):
            self.assertEqual('Research required',next_action(dict(processing_status='REVIEW',work_id=1),'OPEN',
                problems=[dict(code='PROVIDER_FRACTIONAL_CANDIDATE',**{'class':cls},next_action='RESEARCH_REQUIRED')]))
    def test_artifact_counts_do_not_imply_code(self):
        self.assertEqual('Inspect evidence',next_action(dict(processing_status='REVIEW',work_id=1),'OPEN',
            problems=[dict(code='PROVIDER_FRACTIONAL_CANDIDATE',affected_count=100)]))
    def test_eligible_without_blocker(self):self.assertEqual('Accept eligible title',self.label([],evaluation=dict(eligible=True)))
    def test_eligible_advisory_uses_evaluator(self):self.assertEqual('Accept eligible title',self.label(['ACQUISITION_ONLY'],evaluation=dict(eligible=True)))
    def test_runtime_outranks_review(self):self.assertEqual('Auditing…',self.label(['CODE_REVIEW_REQUIRED'],running=True))
    def test_identity_block_outranks_code(self):self.assertEqual('Identity review',self.label(['CODE_REVIEW_REQUIRED','BLOCKED_IDENTITY']))


class ActionPages(unittest.TestCase):
    setUp=fixtures.Workflow.setUp
    cleanup=fixtures.Workflow.cleanup
    wait_idle=fixtures.Workflow.wait_idle

    def observed(self,title,codes,action=None):
        self.db.working_sets.add_requests(self.sid,[title])
        item=next(i for i in self.db.working_sets.items(self.sid) if i['original_query']==title)
        holes=[dict(code=code,severity='warning',message='Offline identity-review fixture',
                    details=dict(chapters=['26.5'])) for code in codes]
        if action:
            for hole in holes:hole.update(next_action=action,problem_class='IDENTITY')
        self.db.working_sets.observe_unresolved(item['working_set_item_uuid'],dict(query=title),holes)
        self.w.refresh_all()
        row=next(r for r in self.page.table.records.records if r['query']==title)
        problems=[r for r in self.w.problems.table.records.records if r['title']==title]
        return row,problems

    def assert_research_observation(self,title,codes):
        row,problems=self.observed(title,codes)
        self.assertIsNone(row['_work_id']);self.assertEqual(len(codes),len(problems))
        self.assertEqual({'RESEARCH_REQUIRED'},{r['action'] for r in problems})
        self.assertEqual('Research required',row['next_action'])
        self.assertEqual({'RESEARCH_REQUIRED'},{r['next_action'] for r in row['_problems']})

    def test_dr_stone_like_intake(self):
        self.assert_research_observation('Dr. STONE',['REFERENCE_CONFLICT','UNMAPPED_CHAPTERS','PROVIDER_FRACTIONAL_CANDIDATE','UNCLASSIFIED_ACQUISITION'])
    def test_sakamoto_like_intake(self):
        self.assert_research_observation('Sakamoto Days',['UNMAPPED_CHAPTERS','PROVIDER_FRACTIONAL_CANDIDATE','PROVIDER_SPLIT_CANDIDATE','UNCLASSIFIED_ACQUISITION'])
    def test_promised_neverland_like_intake(self):
        self.assert_research_observation('The Promised Neverland',['UNMAPPED_CHAPTERS','PROVIDER_FRACTIONAL_CANDIDATE','UNCLASSIFIED_ACQUISITION'])
    def test_explicit_observation_action_is_preserved(self):
        row,problems=self.observed('Explicit fixture',['PROVIDER_FRACTIONAL_CANDIDATE'],'CODE_REVIEW_REQUIRED')
        self.assertEqual('Code review',row['next_action'])
        self.assertEqual({'CODE_REVIEW_REQUIRED'},{r['action'] for r in problems})

    def linked(self,action='RESEARCH_REQUIRED',cls='IDENTITY'):
        aid=self.db.save_audit(1,dict(query='Monster',publication=fixtures.publication('Monster')),
            [dict(code='PROVIDER_FRACTIONAL_CANDIDATE',severity='warning',message='Persisted fixture',details=dict(chapters=['303']))])
        with self.db.con() as c:c.execute('UPDATE audit_holes SET problem_class=?,next_action=? WHERE audit_id=?',(cls,action,aid))
        self.db.working_sets.pin(self.items[0]['working_set_item_uuid'],1,aid)
        return aid

    def test_saved_research_survives_every_read_projection(self):
        aid=self.linked();before=self.db.path.read_bytes();self.w.refresh_all()
        row=next(r for r in self.page.table.records.records if r['_work_id']==1)
        self.assertEqual('Research required',row['next_action'])
        problem=next(r for r in self.w.problems.table.records.records if r.get('_hole') and r['_hole']['audit_id']==aid)
        self.assertEqual(('IDENTITY','RESEARCH_REQUIRED'),(problem['class'],problem['action']))
        context,_=self.session.context(1,'active',self.db.working_sets.item(self.items[0]['working_set_item_uuid']))
        self.assertEqual('RESEARCH_REQUIRED',context['problems'][0]['next_action'])
        packet=review_packet(self.db,work_ids=[1],audit_by_work={1:aid})
        issue=packet['works'][0]['issues'][0]
        self.assertEqual(('IDENTITY','RESEARCH_REQUIRED'),(issue['problem_class'],issue['next_action']))
        path=self.root/'actions.csv';detailed_csv(packet,path)
        import csv
        with path.open(encoding='utf-8-sig',newline='') as inp:rows=list(csv.DictReader(inp))
        self.assertEqual({'RESEARCH_REQUIRED'},{r['next_action'] for r in rows})
        self.assertFalse(self.db.acceptance.evaluate(1,self.items[0]['working_set_item_uuid'])['eligible'])
        self.assertEqual(before,self.db.path.read_bytes())

    def test_saved_code_control(self):
        self.linked('CODE_REVIEW_REQUIRED','CODE');self.w.refresh_all()
        self.assertEqual('Code review',next(r for r in self.page.table.records.records if r['_work_id']==1)['next_action'])

    def test_pin_uses_saved_action_not_newest_global_audit(self):
        aid=self.linked()
        self.db.save_audit(1,dict(query='Monster',publication=fixtures.publication('Monster')),
            [dict(code='PROVIDER_FRACTIONAL_CANDIDATE',severity='warning',message='Newer code fixture')])
        self.w.refresh_all()
        row=next(r for r in self.page.table.records.records if r['_work_id']==1)
        self.assertEqual(aid,row['_item']['pinned_audit_id'])
        self.assertEqual({'RESEARCH_REQUIRED'},{p['next_action'] for p in row['_problems']})
        self.assertEqual('Run Working Set',row['next_action'])  # Existing freshness priority.

    def test_legacy_null_fields_keep_existing_policy_fallback(self):
        self.linked(None,None);self.w.refresh_all()
        self.assertEqual('Code review',next(r for r in self.page.table.records.records if r['_work_id']==1)['next_action'])

    def test_ignored_problem_not_in_workflow_actions(self):
        aid=self.db.save_audit(1,dict(query='Monster',publication=fixtures.publication('Monster')),
            [dict(code='UNCLASSIFIED_ACQUISITION',severity='warning',message='Verified fixture')])
        self.db.dispose_problem(self.db.holes('UNCLASSIFIED_ACQUISITION')[0]['id'],'Verified provider extra','VERIFIED')
        self.db.working_sets.pin(self.items[0]['working_set_item_uuid'],1,aid)
        self.w.refresh_all()
        row=next(r for r in self.page.table.records.records if r['_work_id']==1)
        self.assertEqual([],row['_problems']);self.assertEqual('Accept eligible title',row['next_action'])


if __name__=='__main__':unittest.main()
