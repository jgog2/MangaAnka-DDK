"""Health belongs to an audit snapshot, never to a filtered problem list."""
import json
from pathlib import Path
import tempfile
import unittest

from mangaanka_database_development_kit import DB
from ddk_exports import catalog_context, working_set_packet, working_set_rows, review_context
from ddk_review import review_packet
from test_publication_states import fixture, resolved
from ddk_publication import publication_holes


class HealthConsistency(unittest.TestCase):
    def setUp(self):
        folder=tempfile.TemporaryDirectory();self.addCleanup(folder.cleanup)
        self.db=DB(Path(folder.name)/'health.db',role='TEST')
        res,bundle=fixture();pub=resolved(res,bundle)
        self.db.add_titles(['Serialized fixture'],'standard','en')
        holes=publication_holes(pub,res.primary)
        self.db.save_audit(1,dict(query='Serialized fixture',publication=pub),holes)
        self.aid=self.db.save_audit(1,dict(query='Serialized fixture',publication=pub),holes)
        with self.db.con() as c:c.execute('UPDATE search_audits SET audit_revision=4 WHERE id=?',(self.aid,))
        self.sid=self.db.working_sets.create('Health consistency')
        self.db.working_sets.add_requests(self.sid,['Serialized fixture'])
        self.uid=self.db.working_sets.items(self.sid)[0]['working_set_item_uuid']
        self.db.working_sets.pin(self.uid,1,self.aid)

    def expected(self):
        return json.loads(self.db.audit(self.aid,1)['health_json'])

    def test_selected_problem_does_not_change_semantic_health(self):
        expected=dict(identity='PASS',publication='PASS',normalization='REVIEW',acquisition='PARTIAL')
        self.assertEqual(expected,self.expected())
        for hole in self.db.holes('All'):
            packet=review_packet(self.db,problem_ids=[hole['id']])
            entry=packet['works'][0]
            self.assertEqual((self.aid,4),(entry['audit_id'],entry['audit_revision']))
            self.assertEqual(expected,entry['health'],hole['code'])

    def test_all_contexts_read_same_persisted_health(self):
        expected=self.expected();item=self.db.working_sets.item(self.uid)
        self.assertEqual(expected,catalog_context(self.db,1,item)['health'])
        self.assertEqual(expected,review_packet(self.db,work_ids=[1],audit_by_work={1:self.aid})['works'][0]['health'])
        packet=working_set_packet(self.db,self.sid)
        self.assertEqual(expected,json.loads(packet['entries'][0]['audit']['health_json']))
        row=working_set_rows(self.db,self.sid)[0]
        self.assertEqual(expected,{k:row[k+'_health'] for k in expected})
        self.assertIn('"normalization": "REVIEW"',review_context(self.db,1,item))
        self.assertTrue(any('Normalization remains REVIEW' in w for w in self.db.acceptance.evaluate(1,self.uid)['warnings']))

    def test_problem_filter_and_include_ignored_never_change_health(self):
        expected=self.expected()
        for ignored in (False,True):
            packet=review_packet(self.db,work_ids=[1],include_ignored=ignored)
            self.assertEqual(expected,packet['works'][0]['health'])

    def test_pin_is_not_replaced_by_latest_global_health(self):
        old=self.aid
        res,bundle=fixture(extras=False);pub=resolved(res,bundle)
        newest=self.db.save_audit(1,dict(query='Serialized fixture',publication=pub),[])
        self.assertNotEqual(self.expected(),json.loads(self.db.audit(newest,1)['health_json']))
        entry=review_packet(self.db,work_ids=[1],audit_by_work={1:old})['works'][0]
        self.assertEqual((old,self.expected()),(entry['audit_id'],entry['health']))

    def test_disposition_adjusted_health_stays_authoritative_even_when_ignored_are_exported(self):
        res,bundle=fixture(extras=False);pub=resolved(res,bundle)
        hole=dict(code='UNCLASSIFIED_ACQUISITION',severity='warning',message='Unproven alternate',details=dict(chapters=['31']))
        aid=self.db.save_audit(1,dict(query='Serialized fixture',publication=pub),[hole])
        problem=self.db.holes('All')[0]
        self.db.dispose_problem(problem['id'],'Known noncanonical acquisition alternative','REVIEWED')
        expected=json.loads(self.db.audit(aid,1)['health_json'])
        self.assertEqual('PASS',expected['normalization'])
        packet=review_packet(self.db,work_ids=[1],include_ignored=True)
        self.assertEqual(expected,packet['works'][0]['health'])
        self.assertEqual('IGNORED_WITH_REASON',packet['works'][0]['issues'][0]['disposition'])

    def test_reaudit_diff_uses_same_health(self):
        after={k:v['after'] for k,v in self.db.audit_diff(1)['health'].items()}
        self.assertEqual(self.expected(),after)


if __name__=='__main__':unittest.main()
