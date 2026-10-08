"""Disposable database regressions for queue, audit history and workspace safety."""
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest

import mangaanka_database_development_kit as ddk
from ddk_commands import parse_batch
from ddk_review import review_packet
from ddk_workspace import validate_database


def publication(volume=None, canonical='fixture:1', edition='standard', language='en'):
    identity={'canonical_work_id':canonical,'edition':edition,'language':language,
              'publication_context':'','external_ids':{'fixture':'1'},'trusted':True}
    row={'id':'303','chapter':'303','title':'','type':'chapter','volume':volume,
         '_effective_volume':volume,'_acquisition_provider':'fixture'}
    automatic={'catalog_identity':identity,'projection':[row],
               'logical_chapters':1,'mapped_chapters':int(volume is not None),
               'unmapped_chapters':int(volume is None),'final_volumes':int(volume is not None)}
    return dict(automatic,automatic=automatic,edition=edition,curation_revision=0)


class DatabaseSafety(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.db=ddk.DB(Path(self.tmp.name)/'a.db',role='TEST')

    def audit(self,wid,volume=None,canonical=None):
        canonical=canonical or f'fixture:{wid}'
        return self.db.save_audit(wid,{'query':self.db.work(wid)['input_title'],
            'publication':publication(volume,canonical)},[])

    def test_subset_audit_preserves_ten_works(self):
        self.db.add_titles([f'Title {n}' for n in range(10)],'standard','en')
        for wid in (2,8):self.audit(wid)
        self.assertEqual(10,len(self.db.works()))
        with self.db.con() as c:self.assertEqual(2,c.execute('SELECT count(*) FROM search_audits').fetchone()[0])

    def test_new_title_appends(self):
        self.db.add_titles([f'Title {n}' for n in range(10)],'standard','en')
        self.db.add_titles(['Fire Force'],'standard','en');self.audit(11)
        self.assertEqual(11,len(self.db.works()))

    def test_reaudit_keeps_old_observation_and_latest(self):
        self.db.add_titles(['Example'],'standard','en')
        first=self.audit(1);second=self.audit(1,'33')
        self.assertGreater(second,first)
        self.assertEqual(second,self.db.latest_audit(1)['id'])
        with self.db.con() as c:
            self.assertEqual([1,2],[r[0] for r in c.execute(
                'SELECT audit_revision FROM search_audits WHERE work_id=1 ORDER BY id')])

    def test_curation_overrides_successive_automatic_values(self):
        self.db.add_titles(['Example'],'standard','en');self.audit(1)
        self.db.catalog.apply(self.db.catalog.preview(1,[
            {'entity':'chapter','key':'303','field':'volume','value':'34'}]))
        for auto in (None,'33','35'):
            self.audit(1,auto)
            row=self.db.catalog.rows(1)[0]
            self.assertEqual(auto,row['automatic']['volume'])
            self.assertEqual('34',row['curated']['volume']['value'])
            self.assertEqual('34',row['effective']['volume'])

    def test_unrelated_batch_keeps_curation(self):
        self.db.add_titles(['A','B','C','D'],'standard','en');self.audit(1)
        self.db.catalog.apply(self.db.catalog.preview(1,[
            {'entity':'chapter','key':'303','field':'volume','value':'34'}]))
        before=self.db.catalog.state(1)
        for wid in (2,3,4):self.audit(wid)
        self.assertEqual(before,self.db.catalog.state(1))

    def test_identity_drift_quarantines_curation(self):
        self.db.add_titles(['Example'],'standard','en');self.audit(1)
        self.db.catalog.apply(self.db.catalog.preview(1,[
            {'entity':'chapter','key':'303','field':'volume','value':'34'}]))
        self.audit(1,None,'fixture:2')
        row=self.db.catalog.rows(1)[0]
        self.assertIn('INCOMPATIBLE CURATION',row['status'])
        self.assertIsNone(row['effective']['volume'])
        self.assertEqual('34',self.db.catalog.state(1)['fields'][0]['value'])

    def test_edition_and_language_isolation(self):
        self.db.add_titles(['Example'],'standard','en');self.audit(1)
        self.db.catalog.apply(self.db.catalog.preview(1,[
            {'entity':'chapter','key':'303','field':'volume','value':'34'}]))
        identity=self.db.catalog.state(1)['identity']
        for changed in (dict(identity,edition='fan_color'),dict(identity,language='ja')):
            self.assertEqual('incompatible',self.db.catalog.lookup(changed)['status'])

    def test_uuid_guard_and_preview_reject_other_database(self):
        self.db.add_titles(['Example'],'standard','en');self.audit(1)
        packet=review_packet(self.db)
        guard=parse_batch(packet['works'][0]['guard']+'\nset volume 34 chapter 303')[0]
        other=ddk.DB(Path(self.tmp.name)/'b.db',role='SCRATCH')
        other.add_titles(['Example'],'standard','en')
        other.save_audit(1,{'query':'Example','publication':publication()},[])
        self.assertNotEqual(self.db.database_uuid,other.database_uuid)
        with self.assertRaisesRegex(ValueError,'Stale review packet'):
            other.catalog.preview(1,[{'entity':'chapter','key':'303','field':'volume','value':'34'}],guard=guard)
        preview=self.db.catalog.preview(1,[{'entity':'chapter','key':'303','field':'volume','value':'34'}])
        with self.assertRaisesRegex(ValueError,'another database'):other.catalog.apply(preview)
        with self.assertRaisesRegex(ValueError,'database_uuid'):
            parse_batch('guard audit 1 revision 1 database a1-e0-d0-w1\nset volume 34 chapter 303')

    def test_new_database_identity_role_and_empty_tables(self):
        other=ddk.DB(Path(self.tmp.name)/'new.db',role='SCRATCH')
        self.assertEqual('SCRATCH',other.role)
        self.assertNotEqual(self.db.database_uuid,other.database_uuid)
        with other.con() as c:
            self.assertEqual(8,c.execute('PRAGMA user_version').fetchone()[0])
            for table in ('works','search_audits','curated_fields'):
                self.assertEqual(0,c.execute(f'SELECT count(*) FROM {table}').fetchone()[0])

    def test_invalid_database_rejected_without_mutation(self):
        wrong=Path(self.tmp.name)/'wrong.db'
        with sqlite3.connect(wrong) as c:c.execute('CREATE TABLE unrelated(id INTEGER)')
        before=self.db.database_uuid
        with self.assertRaisesRegex(ValueError,'not a MangaAnkā'):validate_database(wrong)
        self.assertEqual(before,self.db.database_uuid)

    def test_current_database_open_is_read_only(self):
        self.db.add_titles(['Example'],'standard','en');self.audit(1)
        before=self.db.path.read_bytes()
        reopened=ddk.DB(self.db.path)
        self.assertEqual(self.db.database_uuid,reopened.database_uuid)
        self.assertEqual(before,self.db.path.read_bytes())

    def test_legacy_migration_preserves_records_and_backup(self):
        path=Path(self.tmp.name)/'legacy.db'
        with sqlite3.connect(path) as c:
            c.executescript(ddk.SCHEMA.split('CREATE TABLE IF NOT EXISTS problem_dispositions')[0])
            c.execute("INSERT INTO works(id,input_title,edition,language) VALUES(1,'Old','standard','en')")
        migrated=ddk.DB(path,migrate_schema8=True)
        self.assertEqual('Old',migrated.work(1)['input_title'])
        backups=list((path.parent/'backups').glob('legacy_before_schema_v6_*.db'))
        self.assertEqual(1,len(backups))
        with closing(sqlite3.connect(backups[0])) as original:
            self.assertEqual('Old',original.execute('SELECT input_title FROM works WHERE id=1').fetchone()[0])
            self.assertEqual(0,original.execute('PRAGMA user_version').fetchone()[0])
        self.assertTrue(migrated.database_uuid)
        with migrated.con() as c:self.assertEqual(8,c.execute('PRAGMA user_version').fetchone()[0])

    def test_v3_migration_preserves_audit_and_curation(self):
        path=Path(self.tmp.name)/'v3.db'
        old=ddk.DB(path)
        old.add_titles(['Example'],'standard','en')
        old.save_audit(1,{'query':'Example','publication':publication()},[])
        old.catalog.apply(old.catalog.preview(1,[
            {'entity':'chapter','key':'303','field':'volume','value':'34'}]))
        from test_supplementary_persistence import schema7
        schema7(old)
        with old.con() as c:
            c.execute('DROP TABLE database_events')
            c.execute('DROP TABLE database_meta')
            c.execute('PRAGMA user_version=3')
        migrated=ddk.DB(path,migrate_schema8=True)
        self.assertEqual(1,len(migrated.works()))
        self.assertEqual(1,migrated.latest_audit(1)['audit_revision'])
        self.assertEqual('34',migrated.catalog.rows(1)[0]['effective']['volume'])
        self.assertEqual(1,len(migrated.catalog.state(1)['fields']))
        with migrated.con() as c:
            self.assertEqual(8,c.execute('PRAGMA user_version').fetchone()[0])
            self.assertEqual('MIGRATION',c.execute('SELECT origin FROM database_events').fetchone()[0])


if __name__=='__main__':unittest.main()
