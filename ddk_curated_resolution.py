"""Reference-only overlay using the plugin's immutable projection contracts."""
from collections import Counter
from copy import deepcopy
from dataclasses import replace, asdict

from ddk_catalog import chapter_key
from ddk_chapter_normalization import effective_counts, unclassified_rows
from ddk_duplicate_projection import reconcile_duplicates
from mangaanka_search_core.publication_manifest import (FieldEvidence, ManifestChapter, ManifestVolume,
    build_publication_projection, PublicationProjection, PublicationManifestBuilder)
from mangaanka_search_core.unified_volume import build_unified_volume_plan


def apply_curated(automatic, acquisitions, manifest, projection, patch, primary):
    result=deepcopy(automatic)
    result['automatic']=deepcopy(automatic)
    result['curated_database']=patch
    if patch.get('status')!='matched' or not patch.get('fields'):
        return result
    fields={}
    for entry in patch['fields']:
        fields.setdefault((entry['entity'],entry['record_key']),{})[entry['field']]=entry
    multiplicity=Counter(chapter_key(r) for r in projection.rows)
    reference_rows=[]
    masks={}
    for original, projected in zip(acquisitions,projection.rows):
        key=chapter_key(projected)
        edits=fields.get(('chapter',key),{}) if multiplicity[key]==1 else {}
        reference=dict(original)
        for field,entry in edits.items():
            if field in ('chapter','title','volume','type'): reference[field]=entry['value']
        reference_rows.append(reference)
        masks[key]=edits
    # Replace only the working manifest copy; raw reference bundle remains immutable.
    chapters=[]
    for chapter in manifest.chapters:
        edits=masks.get(chapter.key,{})
        updates={}
        for field in ('title','volume'):
            if field in edits:
                updates[field]=FieldEvidence(edits[field]['value'],'curated_database','verified',
                                             str(patch['work_id']))
        if 'chapter' in edits:
            updates.update(key=edits['chapter']['value'],display_number=edits['chapter']['value'])
        if 'type' in edits: updates['kind']=edits['type']['value']
        chapters.append(replace(chapter,**updates))
    existing_keys={chapter.key for chapter in chapters}
    acquired_keys={chapter_key(r) for r in acquisitions if r.get('_unit_kind')!='volume'}
    for (entity,key),edits in fields.items():
        if entity!='chapter' or not edits.get('exists',{}).get('value') or key in existing_keys or key in acquired_keys:
            continue
        def field_evidence(name):
            item=edits.get(name)
            return (FieldEvidence(item['value'],'curated_database',item['verification'].lower(),str(patch['work_id']))
                    if item else FieldEvidence())
        chapters.append(ManifestChapter(key,key,edits.get('type',{}).get('value','chapter'),
                                        field_evidence('title'),field_evidence('volume')))
    volumes=list(manifest.volumes)
    volume_keys={volume.key for volume in volumes}
    for (entity,key),edits in fields.items():
        if entity=='volume' and edits.get('exists',{}).get('value') and key not in volume_keys:
            volumes.append(ManifestVolume(key,key,provenance=FieldEvidence(
                key,'curated_database',edits['exists']['verification'].lower(),str(patch['work_id']))))
    curated_manifest=replace(manifest,chapters=tuple(chapters),volumes=tuple(volumes),ambiguous_chapter_keys=tuple(
        key for key in manifest.ambiguous_chapter_keys if 'volume' not in masks.get(key,{})))
    builder=PublicationManifestBuilder({'canonical_identity':manifest.work.canonical_identity},
                                       manifest.edition.identity,existing=curated_manifest)
    builder._rebuild_volume_membership()
    curated_manifest=builder.build(manifest.work.language)
    effective=build_publication_projection(reference_rows,curated_manifest,primary.source_id,primary.source_id)
    effective,_=reconcile_duplicates(reference_rows,curated_manifest,effective)
    entries=[]; effective_rows=[]; applied=[]
    for original, old, projected in zip(acquisitions,projection.chapters,effective.chapters):
        key=chapter_key(old.as_row()); edits=masks.get(key,{})
        # Restore the actual acquisition record; only reference evidence changes.
        updates={'acquisition':dict(original)}
        for field,target in (('volume','effective_volume'),('title','resolved_title')):
            if field in edits:
                entry=edits[field]
                updates[target]=FieldEvidence(entry['value'],'curated_database',entry['verification'].lower(),str(patch['work_id']))
                if field=='volume': updates['mapping_state']='curated' if entry['value'] is not None else 'unmapped'
        entry=replace(projected,**updates)
        row=entry.as_row()
        automatic_row=automatic['projection'][len(effective_rows)]
        if not any(field in edits for field in ('chapter','volume','type')):
            row['_publication_state']=automatic_row.get('_publication_state','UNMAPPED')
        if result['normalization']['labels'][len(effective_rows)]=='recognized_special' and 'type' not in edits:
            row['type']=automatic_row.get('type','special')
        for field,override in edits.items():
            if field in ('chapter','title','type','volume'): row[field]=override['value']
        if 'volume' in edits:
            row['_effective_volume']=edits['volume']['value']
            row['_volume_source']='curated_database'
        if edits:
            row['_curated_fields']=list(edits)
            row['_acquisition_chapter']=original.get('chapter')
            applied.append(key)
        entries.append(entry); effective_rows.append(row)
    effective=PublicationProjection(tuple(entries),primary.source_id)
    # Native metadata is lower priority now. Feed only unoverridden native
    # memberships to the existing volume planner; acquisition URLs/IDs stay intact.
    plan_inputs=[]
    for original, old in zip(acquisitions,projection.rows):
        item=dict(original)
        if 'volume' in masks.get(chapter_key(old),{}): item['volume']=None
        plan_inputs.append(item)
    plan=build_unified_volume_plan({},plan_inputs,effective,primary.source_id,primary.source_name)
    chapter_entries=[r for r in entries if r.acquisition.get('_unit_kind')!='volume']
    unmapped=[row for row,r in zip(effective_rows,entries) if r.acquisition.get('_unit_kind')!='volume' and not r.effective_volume.present]
    result.update(projection=effective_rows,mapped_chapters=len(chapter_entries)-len(unmapped),
                  unmapped_chapters=len(unmapped),unmapped=unmapped,final_volumes=len(plan['volumes']),
                  volumes=plan['volumes'],native_volumes=plan['native_volume_count'],
                  derived_volumes=plan['derived_volume_count'],coverage=effective.coverage,
                  conflicting_chapters=[key for key in automatic['conflicting_chapters'] if key not in applied or 'volume' not in masks.get(key,{})],
                  reference_conflicts=curated_manifest.runtime_publication.get('reference_conflicts') or [],
                  effective_catalog={'work':{k:v['value'] for k,v in fields.get(('work','work'),{}).items()},
                                     'volumes':{key:{k:v['value'] for k,v in edits.items()} for (entity,key),edits in fields.items() if entity=='volume'}},
                  curated_applied_chapters=applied)
    if automatic.get('normalization'):
        for index, original in enumerate(acquisitions):
            key=chapter_key(original)
            if (result['normalization']['labels'][index]=='provisional' and
                    'volume' in masks.get(key,{})):
                result['normalization']['labels'][index]='main'
                result['normalization']['evidence'][key]='reviewed curated volume membership'
        result['normalization']['counts']=dict(Counter(result['normalization']['labels']))
        if result['normalization']['counts'].get('main'):
            result['normalization']['status']='established'
        result.update(effective_counts(effective_rows, result['normalization']))
        result['unclassified_acquisition']=unclassified_rows(effective_rows,result['normalization'])
    acquired={entry.canonical_key for entry in entries if entry.canonical_key}
    if not automatic.get('volume_only_units'):
        result['missing_reference_chapters']=sorted({c.key for c in curated_manifest.chapters
            if c.volume.present and c.volume.source in ('mangadex_structure','wikipedia') and c.key not in acquired})
    effective_manifest=asdict(curated_manifest)
    work=result['effective_catalog']['work']
    if 'canonical_title' in work: effective_manifest['work']['title']=work['canonical_title']
    if 'aliases' in work: effective_manifest['work']['aliases']=work['aliases']
    for field,target in (('canonical_work_id','canonical_identity'),('language','language')):
        if field in work: effective_manifest['work'][target]=work[field]
    if 'edition' in work: effective_manifest['edition']['identity']=work['edition']
    result['manifest']=effective_manifest
    created=[]
    for (entity,key),edits in fields.items():
        if entity!='chapter' or not edits.get('exists',{}).get('value') or key in acquired_keys:
            continue
        created.append({'chapter':key,'title':edits.get('title',{}).get('value',''),
                        'type':edits.get('type',{}).get('value','chapter'),
                        'volume':edits.get('volume',{}).get('value'),
                        'verification':edits['exists']['verification'],'acquisition_available':False})
    if created:
        result['curated_publication_records']=created
        result['logical_chapters']+=len(created)
        result['recognized_specials']+=sum(r['type'] in ('bonus','extra','omake','special','prologue','epilogue') for r in created)
        result['canonical_main_chapters']+=sum(r['type'] not in ('bonus','extra','omake','special','prologue','epilogue') for r in created)
        mapped_created=sum(r['volume'] not in (None,'') for r in created)
        result['mapped_chapters']+=mapped_created
        result['unmapped_chapters']+=len(created)-mapped_created
        result['unmapped'].extend(r for r in created if r['volume'] in (None,''))
        result['final_volumes']=len({str(r.get('_effective_volume')) for r,label in zip(effective_rows,result['normalization']['labels'])
                                     if r.get('_effective_volume') not in (None,'') and label in ('main','special','recognized_special','provisional')}
                                    | {str(r['volume']) for r in created if r['volume'] not in (None,'')}
                                    | {key for (entity,key),edits in fields.items() if entity=='volume' and edits.get('exists',{}).get('value')})
    elif any(entity=='volume' and edits.get('exists',{}).get('value') for (entity,key),edits in fields.items()):
        result['final_volumes']=len({str(r.get('_effective_volume')) for r,label in zip(effective_rows,result['normalization']['labels'])
                                     if r.get('_effective_volume') not in (None,'') and label in ('main','special','recognized_special','provisional')}
                                    | {key for (entity,key),edits in fields.items() if entity=='volume' and edits.get('exists',{}).get('value')})
    result['count_provenance']=list(result.get('count_provenance') or [])+[
        {'source':'curated_database','field':field,'value':work[field], 'catalog_work_id':patch['work_id']}
        for field in ('expected_chapters','expected_volumes') if field in work]
    return result
