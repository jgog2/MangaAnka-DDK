import unittest
from ddk_commands import parse, parse_batch, scoped_rows, title_scope
import test_catalog as fixtures


class ParserTests(unittest.TestCase):
    def test_bounded_grammar(self):
        for command in ('select chapter 222','select chapters 222-232','select volume 24',
                        'select unmapped','select conflicts','select modified','select missing-title','select all','clear selection',
                        'set volume 24','set volume 24 selected','set volume 24 chapters 222-232','clear volume selected',
                        'clear volume chapters 222-232','reset volume selected',
                        'set type chapter selected','set type bonus selected','set type extra selected',
                        'set type omake selected','set type special selected','set title "Exact title here" chapter 222',
                        'set source-note "Official TOC" selected','show chapter 222','show volume 24','show unmapped',
                        'show conflicts','show modified','show automatic','show curated','validate','save','audit','undo','redo',
                        'on "Example" set volume 24 chapters 222-232'):
            with self.subTest(command=command): self.assertIn('action',parse(command))

    def test_invalid_grammar(self):
        for command in ('','please fix everything','select chapters 232-222',
                        'select chapters 2-x','set volume 24 all','on "Example','audit everything',
                        'set volume 24 selected; audit'):
            with self.subTest(command=command),self.assertRaises(ValueError): parse(command)

    def test_extended_exact_grammar_and_batch(self):
        examples=('select chapters 1,3,5,10.5,12-16','set verification verified selected',
                  'set work verification reviewed','reset type selected','reset title chapter 10',
                  'add chapter 206','add chapters 206-207','remove curated chapter 206',
                  'renumber chapter 10.5 to 10.6','set work edition standard',
                  'add alias "Exact Alias"','remove alias "Exact Alias"',
                  'set id anilist 12345','reset id kitsu','set expected chapters 207',
                  'reset expected volumes','add volume 24','remove curated volume 24',
                  'set volume-title 24 "Title"','show effective chapter 222',
                  'show provenance work','explain chapter 222')
        for example in examples:
            with self.subTest(example=example): self.assertIn('action',parse(example))
        batch=parse_batch('set volume 1 chapters 1-7\nset volume 2 chapters 8-16\n')
        self.assertEqual(2,len(batch))
        self.assertTrue(all(c['action']=='edit' for c in batch))

    def test_mixed_set_requires_every_identity(self):
        rows=[{'iid':str(n),'effective':{'chapter':str(n),'volume':None},'missing':False,
               'conflict':False,'curated':{}} for n in range(1,17)]
        rows.append({'iid':'10.5','effective':{'chapter':'10.5','volume':None},
                     'missing':False,'conflict':False,'curated':{}})
        self.assertEqual(9,len(scoped_rows(rows,['chapters','1,3,5,10.5,12-16'])))
        with self.assertRaises(ValueError): scoped_rows(rows,['chapters','1,3,20-21'])


class ScopeTests(unittest.TestCase):
    setUp=fixtures.CatalogCase.setUp
    resolve=fixtures.CatalogCase.resolve
    refresh=fixtures.CatalogCase.refresh
    def test_scopes_and_preview(self):
        self.db.add_titles(['Other'],'standard','en')
        command=parse('on "Example" set volume 24 chapters 222-232')
        wid=title_scope(self.db,2,command['title'])
        self.assertEqual(1,wid)
        rows=scoped_rows(self.store.rows(wid),command['target'])
        self.assertEqual(11,len(rows))
        preview=self.store.preview(wid,[{'entity':'chapter','key':r['key'],'field':'volume','value':'24'} for r in rows])
        self.assertEqual([],self.store.state(wid)['fields'])
        self.store.apply(preview)
        self.assertEqual([],self.store.state(2)['fields'])

    def test_invalid_title_and_range(self):
        with self.assertRaises(ValueError): title_scope(self.db,1,'Unknown')
        with self.assertRaises(ValueError): scoped_rows(self.store.rows(1),['chapters','222-999'])

    def test_selected_scope_ctrl_equivalent(self):
        rows=self.store.rows(1)
        picked={rows[0]['iid'],rows[3]['iid']}
        self.assertEqual(['222','225'],[r['key'] for r in scoped_rows(rows,['selected'],picked)])

    def test_shift_range_equivalent_with_decimals(self):
        rows=self.store.rows(1)
        rows.append(dict(rows[0],iid='decimal',key='222.5',effective=dict(rows[0]['effective'],chapter='222.5')))
        self.assertEqual(12,len(scoped_rows(rows,['chapters','222-232'])))


if __name__=='__main__': unittest.main()
