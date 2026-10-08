"""Bounded publisher observations; never infer acquisition identity from a number.

MANGA Plus protobuf fields follow Shueisha's public web client (title_detailV4
and title_list/allV2). Only explicit COMPLETED (8) is closure evidence; the
client also displays DISABLED (0) as Completed, which is deliberately rejected.
"""
from concurrent.futures import CancelledError
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
from html.parser import HTMLParser
import json
import re
import urllib.parse
import urllib.request
import uuid

from mangaanka_search_core.canonical_identity import (
    normalize_identity_text, creator_comparison_identity,
)
from mangaanka_search_core.madb_reference import trusted_titles

CONTRACT = 'publisher-publication-v1'
API = 'https://jumpg-webapi.tokyo-cdn.com/api'
MAX_BYTES = 2_000_000


class BookHTML(HTMLParser):
    """Observe official text/links, excluding executable and styling content."""
    def __init__(self, value):
        super().__init__(convert_charrefs=True)
        self.links, self.lines, self.buffer, self.ignored = [], [], [], 0
        self.feed(value); self.flush()
    def flush(self):
        value = ' '.join(''.join(self.buffer).split())
        if value: self.lines.append(value)
        self.buffer = []
    def handle_starttag(self, tag, attrs):
        if tag in ('script','style'): self.ignored += 1
        if self.ignored: return
        if tag in ('div','p','br','li','h1','h2','h3'): self.flush()
        if tag == 'a' and dict(attrs).get('href'): self.links.append(dict(attrs)['href'])
    def handle_endtag(self, tag):
        if tag in ('script','style'): self.ignored = max(0,self.ignored-1)
        if not self.ignored and tag in ('div','p','li','h1','h2','h3'): self.flush()
    def handle_data(self, data):
        if not self.ignored: self.buffer.append(data)


def supplementary_books(html, evidence):
    """Read Shueisha's typed search data, not loosely related search snippets."""
    match = re.search(r'var ssd\s*=\s*', html)
    if not match: raise ValueError('Missing publisher book search schema')
    data = json.JSONDecoder().raw_decode(html[match.end():])[0]
    trusted = {normalize_identity_text(t) for t in trusted_titles(evidence)}
    books = {}
    for series in data.get('datas') or ():
        if (normalize_identity_text(series.get('series_name_2')) not in trusted or
                series.get('item_kbn') != '1' or series.get('label_name') != 'ジャンプコミックス'):
            continue
        for item in series.get('item_datas') or ():
            if (normalize_identity_text(item.get('item_name_2')) not in trusted or
                    not re.search(r'公式(?:ガイドブック|ファンブック)', item.get('item_name_3') or '')):
                continue
            isbn = str(item.get('isbn') or '')
            if not re.fullmatch(r'978-\d-\d{2}-\d{6}-\d', isbn): continue
            books[isbn] = dict(isbn=isbn, title=item.get('item_name'),
                publisher_book_id=item.get('ssid'), publisher_series_id=series.get('series_id'),
                release_date=item.get('release_date'), creators=item.get('author_name_datas') or [],
                publication_role='supplementary_book', acquisition_binding='unresolved')
    return list(books.values())[:2]


def supplementary_contents(html, book, url):
    """TOC page positions identify book records, never chapter/volume numbers."""
    records = []
    for line in BookHTML(html).lines:
        match = re.fullmatch(r'(.+?)\s+(\d+)', line)
        if not match: continue
        heading, page = match.groups()
        role = ('pilot_or_oneshot' if '読切版' in heading or '特別読切' in heading else 'special' if
                re.search(r'描き(?:おろし|下ろし)漫画', heading) else None)
        if not role: continue
        records.append(dict(source='shueisha', source_page=url,
            source_record_id='isbn:'+book['isbn']+':toc:'+page, title=heading,
            book_page=page, kind='special', publication_role=role,
            canonical_identifier=None, acquisition_binding='unresolved'))
    return records


def wire(data):
    """Read bounded protobuf wire values without guessing nested message types."""
    if not isinstance(data, bytes) or len(data) > MAX_BYTES:
        raise ValueError('Invalid publisher payload size')
    position, result, fields = 0, {}, 0
    def varint():
        nonlocal position
        value = 0
        for shift in range(0, 70, 7):
            if position >= len(data): raise ValueError('Truncated publisher protobuf')
            byte = data[position]; position += 1
            value |= (byte & 127) << shift
            if not byte & 128: return value
        raise ValueError('Invalid publisher protobuf varint')
    while position < len(data):
        fields += 1
        if fields > 50000:
            raise ValueError('Publisher protobuf has too many fields')
        tag = varint(); field, kind = tag >> 3, tag & 7
        if not field: raise ValueError('Invalid publisher protobuf field')
        if kind == 0: value = varint()
        elif kind in (1, 2, 5):
            size = varint() if kind == 2 else 8 if kind == 1 else 4
            end = position + size
            if end > len(data): raise ValueError('Truncated publisher protobuf value')
            value = data[position:end]; position = end
        else: raise ValueError('Unsupported publisher protobuf wire type')
        result.setdefault(field, []).append(value)
    return result


def one(row, field, default=None):
    values = row.get(field, ())
    if len(values) > 1: raise ValueError('Duplicate scalar publisher field')
    return values[0] if values else default


def text(row, field):
    value = one(row, field, b'')
    if not isinstance(value, bytes): raise ValueError('Invalid publisher text field')
    return value.decode('utf-8')


def success(data, field):
    response = wire(data)
    if response.get(2): raise ValueError('Publisher returned an API error')
    payload = one(wire(one(response, 1, b'')), field)
    if not isinstance(payload, bytes): raise ValueError('Missing publisher response message')
    return wire(payload)


def title(row):
    return dict(id=one(row, 1), title=text(row, 2), creator=text(row, 3), language=one(row, 7, 0))


def catalog(data):
    result = []
    for group in success(data, 25).get(1, ()):
        result.extend(title(wire(raw)) for raw in wire(group).get(2, ()))
    return result


def detail(data):
    row = success(data, 8)
    result = title(wire(one(row, 1, b'')))
    result['release_schedule'] = one(wire(one(row, 32, b'')), 1)
    # Typed TitleLanguages messages, not recommendation or chapter links.
    result['language_links'] = [dict(id=one(wire(raw), 1), language=one(wire(raw), 2, 0))
                                for raw in row.get(27, ())]
    records = list(row.get(9, ())) + list(row.get(10, ())) + list(row.get(38, ()))
    # Current web client ChapterContent contains either one chapter or a
    # nested MiddleChapters list. Do not decode unrelated recommendations.
    for raw in row.get(47, ()):
        content = wire(raw); records.extend(content.get(1, ()))
        for middle in content.get(2, ()): records.extend(wire(middle).get(1, ()))
    chapters = {}
    for raw in records:
        chapter = wire(raw)
        label = text(chapter, 3)
        match = re.fullmatch(r'#(\d+(?:\.\d+)?)', label)
        if not match: continue
        key = format(Decimal(match[1]).normalize(), 'f')
        record = dict(key=key, publisher_record_id=one(chapter, 2),
                      title=text(chapter, 4), published_at=one(chapter, 6), label=label)
        if one(chapter, 1) != result['id'] or not record['publisher_record_id']:
            raise ValueError('Publisher chapter belongs to a different work')
        if key in chapters and chapters[key] != record:
            raise ValueError('Ambiguous publisher chapter identity')
        chapters[key] = record
    result['chapters'] = sorted(chapters.values(), key=lambda r: Decimal(r['key']))
    return result


def creators_match(actual, evidence):
    # Preserve explicitly written Hepburn macrons without broad fuzzy names.
    expanded = str(actual).translate(str.maketrans({'ā':'aa','ī':'ii','ū':'uu','ē':'ee','ō':'ou'}))
    trusted = {creator_comparison_identity(c) for c in
               (*evidence.get('creators', ()), *evidence.get('creator_aliases', ())) if c}
    return bool(trusted & {creator_comparison_identity(actual), creator_comparison_identity(expanded)})


def terminal_chapter(chapters):
    """Identify an explicitly labeled final chapter, never the last free preview.

    The public API's first/last/available chapter lists describe availability.
    COMPLETED alone does not make their numeric maximum a terminal identity.
    Multiple final labels remain ambiguous, including stored observations.
    """
    candidates = [row for row in chapters if isinstance(row, dict) and
                  re.fullmatch(r'final\s+(?:chapter|page|episode)(?:\s*[:.!\-]\s*.+)?',
                               str(row.get('title') or '').strip(), re.IGNORECASE)]
    return candidates[0] if len(candidates) == 1 else None


def compatible(row, evidence):
    return (row.get('language') == 0 and row.get('id') and
            normalize_identity_text(row.get('title')) in
            {normalize_identity_text(t) for t in trusted_titles(evidence)} and
            creators_match(row.get('creator'), evidence))


def title_matches(row, evidence):
    return (row.get('id') and normalize_identity_text(row.get('title')) in
            {normalize_identity_text(t) for t in trusted_titles(evidence)})


def macron_equivalent(primary, secondary, evidence):
    """Use an explicitly printed macron as authority, never guess long vowels."""
    creator = str(secondary.get('creator') or '')
    plain = creator.translate(str.maketrans({'ā':'a','ī':'i','ū':'u','ē':'e','ō':'o'}))
    return (plain != creator and creators_match(creator, evidence) and
            creator_comparison_identity(plain) == creator_comparison_identity(primary.get('creator')))


def creator_equivalence_valid(proof, primary, evidence):
    """Revalidate the scoped reciprocal publisher proof at both boundaries."""
    if not isinstance(proof, dict): return False
    first, second = proof.get('primary'), proof.get('secondary')
    if not isinstance(first, dict) or not isinstance(second, dict): return False
    if any(first.get(k) != primary.get(k) for k in ('id','title','creator','language')): return False
    if (first.get('language') != 0 or type(second.get('language')) is not int or
            not 1 <= second['language'] <= 9 or not title_matches(first, evidence) or
            not title_matches(second, evidence) or not macron_equivalent(first, second, evidence)):
        return False
    for row in (first, second):
        if type(row.get('id')) is not int or row['id'] <= 0: return False
        if (row.get('url') != 'https://mangaplus.shueisha.co.jp/titles/'+str(row['id']) or
                not re.fullmatch(r'[0-9a-f]{64}', str(row.get('payload_sha256') or ''))): return False
        links = row.get('language_links')
        if not isinstance(links, list) or not all(isinstance(r, dict) for r in links): return False
        # A title ID cannot simultaneously identify different languages.
        for target in (first, second):
            matches = [r for r in links if r.get('id') == target['id']]
            if len(matches) != 1 or matches[0].get('language') != target['language']: return False
    return first['id'] != second['id']


class PublisherReferenceAdapter:
    def __init__(self, request_bytes=None, now=None):
        self.request_bytes = request_bytes or self._request
        self.now = now or (lambda: datetime.now(timezone.utc))
        self.session_token = str(uuid.uuid4())  # Anonymous public web-client session, not a login.

    def _request(self, url):
        headers = {'User-Agent':'MangaAnka-DDK-Publication-Audit/0.3'}
        if urllib.parse.urlsplit(url).hostname == 'jumpg-webapi.tokyo-cdn.com':
            headers['SESSION-TOKEN'] = self.session_token
        request = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(request, timeout=12) as response:
            data = response.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES: raise ValueError('Publisher response exceeds limit')
        return data

    def supplements(self, evidence, check):
        aliases = [t for t in trusted_titles(evidence) if re.search('[\u3040-\u30ff]', t)]
        if not aliases: return []
        search = 'https://www.shueisha.co.jp/books/search/search.html?'+urllib.parse.urlencode(
            dict(titleauthor=aliases[0]))
        check(); books = supplementary_books(self.request_bytes(search).decode('utf-8'), evidence)
        result = []
        for book in books:
            check()
            url = 'https://www.shueisha.co.jp/books/items/contents.html?'+urllib.parse.urlencode(
                dict(isbn=book['isbn']))
            html = self.request_bytes(url).decode('utf-8')
            digital = []
            for link in BookHTML(html).links:
                target = urllib.parse.urljoin(url, link); parsed = urllib.parse.urlsplit(target)
                jdcn = urllib.parse.parse_qs(parsed.query).get('jdcn', [])
                if (parsed.scheme == 'https' and parsed.hostname in ('www.shueisha.co.jp','www.s-manga.net')
                        and parsed.path in ('/books/items/contents.html','/items/contents.html')
                        and len(jdcn) == 1 and re.fullmatch(r'[0-9A-Z]{15,24}',jdcn[0])):
                    digital.append(target)
            if len(set(digital)) == 1:
                check(); url = digital[0]; html = self.request_bytes(url).decode('utf-8')
            records = supplementary_contents(html, book, url)
            parsed = urllib.parse.urlsplit(url)
            jdcn = urllib.parse.parse_qs(parsed.query).get('jdcn', [])
            result.append(dict(book, source_page=url, records=records, status='observed_unbound',
                               canonical_work_id=evidence.get('canonical_work_id'),
                               edition=evidence.get('edition_profile'), language='ja',
                               captured_at=self.now().isoformat(), evidence_type='official_toc',
                               publication_id='jdcn:'+jdcn[0] if len(jdcn)==1 else 'isbn:'+book['isbn'],
                               payload_sha256=hashlib.sha256(html.encode('utf-8')).hexdigest()))
        return result

    def lookup(self, evidence, should_cancel=None):
        cancel = should_cancel or (lambda: False)
        def check():
            if cancel(): raise CancelledError()
        result = dict(contract=CONTRACT, status='unavailable', source='mangaplus',
                      canonical_work_id=evidence.get('canonical_work_id'), edition='standard',
                      language='en', chapters=[], supplementary_publications=[])
        if (not evidence.get('canonical_work_id') or evidence.get('identity_confidence') != 'high'
                or evidence.get('edition_profile') != 'standard'
                or evidence.get('requested_language') != 'en'):
            result['status'] = 'incompatible_identity'; return result
        try:
            check(); listing = catalog(self.request_bytes(API+'/title_list/allV2'))
            candidates = [r for r in listing if compatible(r, evidence)]
            partner = None
            if not candidates:
                english = [r for r in listing if r.get('language') == 0 and title_matches(r, evidence)]
                if len(english) == 1:
                    partners = [r for r in listing if type(r.get('language')) is int and
                        1 <= r['language'] <= 9 and title_matches(r, evidence) and
                        macron_equivalent(english[0], r, evidence)]
                    if len(partners) == 1: candidates, partner = english, partners[0]
            ids = {r['id'] for r in candidates}
            if len(ids) != 1:
                result['status'] = 'ambiguous' if ids else 'unmatched'; return result
            ident = next(iter(ids)); check()
            raw = self.request_bytes(API+'/title_detailV4?'+urllib.parse.urlencode(
                dict(title_id=ident, clang='eng')))
            publisher = detail(raw)
            proof = None
            if partner is not None:
                check(); other_raw = self.request_bytes(API+'/title_detailV4?'+urllib.parse.urlencode(
                    dict(title_id=partner['id'], clang='eng')))
                other = detail(other_raw)
                if any(other.get(k) != partner.get(k) or publisher.get(k) != candidates[0].get(k)
                       for k in ('id','title','creator','language')):
                    result['status'] = 'incompatible_detail'; return result
                def observation(row, data):
                    return {**{k:row[k] for k in ('id','title','creator','language','language_links')},
                        'url':'https://mangaplus.shueisha.co.jp/titles/'+str(row['id']),
                        'payload_sha256':hashlib.sha256(data).hexdigest()}
                proof = dict(primary=observation(publisher, raw), secondary=observation(other, other_raw))
                if not creator_equivalence_valid(proof, publisher, evidence):
                    result['status'] = 'incompatible_detail'; return result
            if publisher['id'] != ident or not (compatible(publisher, evidence) or proof):
                result['status'] = 'incompatible_detail'; return result
            check(); stamp = self.now()
            if stamp.tzinfo is None: raise ValueError('Publisher clock must include timezone')
            result.update(status='current', checked_at=stamp.isoformat(), publication_id=str(ident),
                url='https://mangaplus.shueisha.co.jp/titles/'+str(ident),
                payload_sha256=hashlib.sha256(raw).hexdigest(), title=publisher['title'],
                creator=publisher['creator'], release_schedule=publisher['release_schedule'],
                completed=publisher['release_schedule'] == 8,
                chapters=publisher['chapters'])
            if proof is not None: result['creator_equivalence'] = proof
            # Availability and completion status cannot identify a final chapter.
            if result['completed'] and result['chapters']:
                final = terminal_chapter(result['chapters'])
                if final is not None: result['final_chapter'] = final
            # Supplementary books are independent publication observations;
            # an ongoing/open main series may also have an official guidebook.
            try: result['supplementary_publications'] = self.supplements(evidence, check)
            except CancelledError: raise
            except Exception as exc: result['supplementary_error'] = str(exc)
            return result
        except CancelledError: raise
        except Exception as exc:
            result.update(status='unavailable', error=str(exc)); return result


def current_evidence(value, identity, as_of=None, context=None):
    """Revalidate stored/fake-network observations at the consumer boundary."""
    if (not identity.get('trusted') or value.get('contract') != CONTRACT or
            value.get('status') != 'current' or value.get('source') != 'mangaplus' or
            value.get('canonical_work_id') != identity.get('canonical_work_id') or
            value.get('edition') != identity.get('edition') or value.get('language') != identity.get('language') or
            not re.fullmatch(r'\d+',str(value.get('publication_id') or '')) or
            not re.fullmatch(r'[0-9a-f]{64}',str(value.get('payload_sha256') or '')) or
            value.get('url') != 'https://mangaplus.shueisha.co.jp/titles/'+str(value.get('publication_id'))):
        return False
    if context is not None:
        scope = dict(canonical_title=context.get('canonical_title'),
            canonical_aliases=context.get('canonical_aliases') or (),
            creators=context.get('canonical_creators') or (),
            creator_aliases=context.get('canonical_creator_aliases') or ())
        primary = dict(id=int(value['publication_id']),title=value.get('title'),
                       creator=value.get('creator'),language=0)
        if not compatible(primary, scope):
            proof = value.get('creator_equivalence')
            if (not creator_equivalence_valid(proof, primary, scope) or
                    proof['primary']['payload_sha256'] != value['payload_sha256']): return False
    try:
        checked = datetime.fromisoformat(value['checked_at'])
        cutoff = datetime.fromisoformat(str(as_of).replace('Z','+00:00')) if as_of else datetime.now(timezone.utc)
        if cutoff.tzinfo is None: cutoff = cutoff.replace(tzinfo=timezone.utc)
        # Date-only historical replays refer to the entire named day.
        if as_of and len(str(as_of)) == 10: cutoff = cutoff.replace(hour=23,minute=59,second=59)
        age = (cutoff-checked).total_seconds()
        return checked.tzinfo is not None and 0 <= age <= 86400
    except (KeyError, ValueError, TypeError): return False


def membership_evidence(value, identity, publication_records, as_of=None, context=None):
    """A fresh publisher final identity can close a corroborated positive model.

    An open/stale reference never supplies negative membership evidence. A
    newer independently established identity contradicts closure, rather than
    being discarded. No chapter identities are created by range expansion.
    """
    result = dict(status='unavailable', main_records=[], closed_main_keys=[], conflicts=[])
    if not isinstance(value, dict): return result
    if not current_evidence(value or {}, identity, as_of, context): return result
    result['status'] = 'open'
    for row in value.get('chapters') or ():
        if not isinstance(row,dict): continue
        key = row.get('key')
        if not re.fullmatch(r'\d+(?:\.\d+)?', str(key)) or not row.get('publisher_record_id'): continue
        try:
            if not isinstance(row.get('published_at'), int) or datetime.fromtimestamp(row['published_at'],timezone.utc) > datetime.fromisoformat(value['checked_at']): continue
        except (ValueError, OverflowError, OSError): continue
        result['main_records'].append(dict(row,kind='chapter', source='mangaplus',confidence='explicit',
            source_page=value['url'], source_record_id=str(row['publisher_record_id']),
            canonical_work_id=identity['canonical_work_id']))
    special_keys = {str(r['key']) for r in publication_records if r.get('kind') not in ('chapter','uncollected')}
    contradictions = sorted({r['key'] for r in result['main_records']} & special_keys,key=Decimal)
    if contradictions:
        result.update(status='conflict', conflicts=contradictions,
            main_records=[r for r in result['main_records'] if r['key'] not in special_keys])
        return result
    if value.get('completed') is not True or value.get('release_schedule') != 8: return result
    final = value.get('final_chapter') or {}
    if (not isinstance(final,dict) or not final or
            final != terminal_chapter(value.get('chapters') or ()) or not any(
            all(r.get(k)==v for k,v in final.items()) for r in result['main_records'])): return result
    final_key = final['key']
    established = {str(r['key']) for r in publication_records if r.get('kind') in ('chapter','uncollected')}
    if final_key not in established: return result
    newer = sorted({k for k in established if Decimal(k) > Decimal(final_key)}, key=Decimal)
    if newer:
        result.update(status='conflict', conflicts=newer); return result
    # Require an explicitly present contiguous integer backbone through the
    # publisher's final identity. This verifies the observed set; it never
    # invents chapters or fills gaps. Noncontiguous works remain conservative.
    if Decimal(final_key) != Decimal(final_key).to_integral_value() or Decimal(final_key) > 100000:
        return result
    if not all(str(n) in established for n in range(1, int(final_key)+1)): return result
    result.update(status='closed', closed_main_keys=sorted(established,key=Decimal),
                  final_chapter=final, source_page=value['url'], checked_at=value['checked_at'])
    return result


def publisher_fingerprint(value):
    """Semantic publisher provenance, without volatile refresh timestamps."""
    facts = {key:value.get(key) for key in ('contract','status','source','canonical_work_id',
        'edition','language','publication_id','url','title','creator','release_schedule',
        'completed','chapters','final_chapter','supplementary_publications')}
    if value.get('creator_equivalence') is not None:
        facts['creator_equivalence'] = value['creator_equivalence']
    if any('captured_at' in r for r in facts.get('supplementary_publications') or () if isinstance(r,dict)):
        facts['supplementary_publications'] = [{k:v for k,v in r.items() if k!='captured_at'}
                                             for r in facts['supplementary_publications']]
    return hashlib.sha256(json.dumps(facts,sort_keys=True,ensure_ascii=False).encode('utf-8')).hexdigest()
