"""DDK-only reconciliation of equivalent acquisition duplicates against trusted structure.

The plugin projection deliberately fails closed on every repeated numeric key.
For audit purposes, repetition alone is not a conflicting chapter-to-volume
assignment. This adapter changes only computed projection evidence; raw rows,
the manifest, and reference payloads stay untouched.
"""
from collections import defaultdict
from dataclasses import replace

from mangaanka_search_core.cross_source_fallback import (
    chapter_identity, chapter_identities_match, normalize_chapter_number,
)
from mangaanka_search_core.publication_manifest import (
    FieldEvidence, PublicationProjection, normalize_publication_number,
)


TRUSTED_STRUCTURE={'mangadex_structure','wikipedia'}


def reconcile_duplicates(acquisitions, manifest, projection):
    """Return (projection, structural-conflict keys) without modifying input rows."""
    groups=defaultdict(list)
    for index,row in enumerate(acquisitions):
        if row.get('_unit_kind')=='volume': continue
        key=normalize_chapter_number(row.get('chapter'))
        if key is not None: groups[key].append(index)
    entries=list(projection.chapters)
    structural_conflicts=set()
    for key,indexes in groups.items():
        if len(indexes)<2: continue
        chapter=manifest.chapter(key) if manifest else None
        explicit={normalize_publication_number(acquisitions[index].get('volume')) for index in indexes}
        explicit.discard(None)
        structural=(chapter.volume if chapter and key not in manifest.ambiguous_chapter_keys and
                    chapter.volume.present and (
                        chapter.volume.source in TRUSTED_STRUCTURE or
                        (len(explicit)==1 and normalize_publication_number(chapter.volume.value) in explicit))
                    else None)
        if len(explicit)>1:
            structural_conflicts.add(key)
            for index in indexes:
                entries[index]=replace(entries[index],effective_volume=FieldEvidence(),
                                       resolved_cover=None,mapping_state='unmapped')
            continue
        first=chapter_identity(acquisitions[indexes[0]])
        if not all(chapter_identities_match(first,chapter_identity(acquisitions[index])) for index in indexes[1:]):
            continue
        if not structural: continue
        for index in indexes:
            if not entries[index].effective_volume.present:
                entries[index]=replace(entries[index],effective_volume=structural,
                                       mapping_state=('reference_explicit' if structural.source in TRUSTED_STRUCTURE
                                                      else 'provider_explicit'))
    return PublicationProjection(tuple(entries),projection.selected_provider),tuple(sorted(structural_conflicts))
