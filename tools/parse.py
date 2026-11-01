"""Builds corpus.d parts for the Município de Maceió from the Câmara Municipal de Maceió's PDFs (no network).

    python -X utf8 parse.py --today YYYY-MM-DD [--part-size 50] [--lom-only]

10-lei-organica: the Câmara's updated edition of the Lei Orgânica ("Atualizada pelas Emendas de nºs 01 a 43", a PDF
with a text layer). Pages 1-12 are an alphabetical index; the Lei Orgânica runs from the heading "LEI ORGÂNICA DO
MUNICÍPIO DE MACEIÓ" before "A CÂMARA MUNICIPAL DE MACEIÓ, ... promulga esta:" to "Maceió - AL, 02 de abril de
1990."; the signatures and the closing note on the update are left out. Each page's last two lines (the page number
and the "Baixado Em: <date>" stamp of the download) are left out. Lines are joined into paragraphs (a new paragraph at
a provision label, a heading line, or after a line ending in ".", ";" or ":"). The notes in parentheses "(Redação dada
pela(s) Emenda(s) ...)" and "(Pela Emenda ...)" are left out of the text; the latest date they cite dates the version.

30-lei-<year>-NN: each law the Câmara lists (/leisx), as published in the Diário Oficial Eletrônico do Município de
Maceió: the PDF printout of the gazette entry. The text runs from the law's heading line ("LEI Nº ...") to the line
before "Publicado por:"; page furniture of the printout (its "Baixado Em: ... -- Diário Oficial ..." header, the
print date and time, the entry's address with "n/m") is left out. Each law is given as enacted, credited to itself and
dated by the "Publicada em" date of its gazette entry. PDFs with no text layer are left out.
"""
import argparse, json, re, sys
from pathlib import Path

import pymupdf

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from br_lib import units_of, write_part, sha, norm  # noqa: E402

BASE = 'https://www.maceio.al.leg.br'
LOM_URL = BASE + '/documentos/docs/doc.php?filepath=publicacoes&id=1'
LOM_PAGE = BASE + '/publicacoesx'
RAW = HERE / '.cache' / 'www' / 'raw'
NOTE = re.compile(r'\(\s*(?:Reda[çc][ãa]o\s+dada\s+pel|Pela\s+Emenda)[^()]*\)', re.I)
STARTS = re.compile(r'^(?:Art\.|Art\s+\d|§|Par[áa]grafo|[IVXLC]+\s*[-–]|[a-z]\)|T[ÍI]TULO|CAP[ÍI]TULO|Se[c]?[çc][ãa]o|'
                    r'SE[C]?[ÇC][ÃA]O|Subse[c]?[çc][ãa]o|SUBSE[C]?[ÇC][ÃA]O)')
HEADING = re.compile(r'^(?:T[ÍI]TULO|CAP[ÍI]TULO|SE[C]?[ÇC][ÃA]O|Se[c]?[çc][ãa]o|Subse[c]?[çc][ãa]o|SUBSE[C]?[ÇC][ÃA]O)'
                     r'\s+(?:[IVXLC]+|[ÚU]NIC[OA])\b')
DMY = re.compile(r'\b(\d{1,2})\.(\d{1,2})\.(\d{2}|\d{4})\b')
LOM_END = 'Maceió - AL, 02 de abril de 1990.'


def caps(l):
    return l == l.upper() and re.search(r'[A-ZÀ-Ý]{3}', l)


def paragraphs(lines, caps_break=True):
    """[(is_heading, text)] from PDF lines. caps_break: an upper-case line is a paragraph of its own (the Lei
    Orgânica's headings); laws print their ementa and enacting clause in upper case over several lines."""
    paras = []
    for l in lines:
        head = bool(HEADING.match(l)) or (caps_break and caps(l) and bool(paras) and paras[-1][0])
        prev = paras[-1] if paras else None
        if prev is not None and re.fullmatch(r'Art\.?', prev[1]):
            prev[1] += ' ' + l  # "Art." at a line end, its number on the next line
            continue
        if (prev is None or STARTS.match(l) or head or (caps_break and (caps(l) or caps(prev[1])))
                or re.search(r'[.;:]["”]?$', prev[1])):
            paras.append([head, l])
        elif prev[1].endswith('-') and not prev[1].endswith(' -'):
            prev[1] += l
        else:
            prev[1] += ' ' + l
    return paras


def strip_notes(paras):
    s = '\n'.join(('\x01' if h else '') + t for h, t in paras)
    notes = []
    while NOTE.search(s):
        notes += [re.sub(r'\s+', ' ', n) for n in NOTE.findall(s)]
        s = NOTE.sub(' ', s)
    out = []
    for l in s.split('\n'):
        h = l.startswith('\x01')
        l = norm(l.lstrip('\x01'))
        if l and re.search(r'\w', l):
            out.append(('h2' if h else 'p', l))
    return out, notes


def lom_lines(pdf):
    raw = []
    for p in pymupdf.open(pdf):
        ls = [norm(l) for l in p.get_text().split('\n')]
        ls = [l for l in ls if l]
        if len(ls) >= 2 and ls[-1].startswith('Baixado Em:') and re.fullmatch(r'\d{1,3}', ls[-2]):
            ls = ls[:-2]
        raw += ls
    start = next(i for i, l in enumerate(raw) if l == 'LEI ORGÂNICA DO MUNICÍPIO DE MACEIÓ'
                 and raw[i + 1].startswith('A CÂMARA MUNICIPAL DE MACEIÓ'))
    end = raw.index(LOM_END, start)
    return raw[start:end + 1]


def dmy(s):
    out = []
    for d, m, y in DMY.findall(s):
        y = int(y) if len(y) == 4 else (1900 + int(y) if int(y) >= 50 else 2000 + int(y))
        if 1 <= int(m) <= 12 and 1 <= int(d) <= 31:
            out.append(f'{y:04d}-{int(m):02d}-{int(d):02d}')
    return out


COUNTRY = {
    'code': 'BR-AL-MACEIO', 'name': 'Maceió', 'slug': 'brazil-maceio-city', 'lang': 'pt', 'tz': 'America/Maceio',
    'future_branch': 'futuro',
    'publisher': {'name': 'Câmara Municipal de Maceió', 'email': 'leis@maceio.al.leg.br.invalid'},
    'default_in_force_rule': {
        'text': 'Decreto-Lei 4.657/1942 (LINDB) art. 1: unless it says otherwise, a law takes effect 45 days after its '
                'official publication. Maceió municipal laws almost always say "Esta Lei entra em vigor na data de sua '
                'publicação"; this record dates each law by its publication in the Diário Oficial Eletrônico do '
                'Município de Maceió, and the Lei Orgânica by the latest amendment its updated edition cites.',
        'source': 'https://www.planalto.gov.br/ccivil_03/decreto-lei/del4657compilado.htm'},
    'licence_note': 'Texts: Câmara Municipal de Maceió, www.maceio.al.leg.br (the Lei Orgânica\'s updated edition and '
                    'the printouts of the laws\' entries in the Diário Oficial Eletrônico do Município de Maceió). Lei '
                    '9.610/1998 art. 8 IV: the texts of laws and other official acts are not protected by copyright. '
                    'Non-official copies: only the official gazette is authoritative.',
}
DECISIONS = [
    'The Lei Orgânica is given only as the Câmara\'s updated edition ("Atualizada pelas Emendas de nºs 01 a 43", '
    '2019), credited to the Câmara as the oldest version available and dated by the latest date among the amendments '
    'its notes cite. The text as promulgated on 2 April 1990 and the wordings the amendments replaced are not '
    'reconstructed. The alphabetical index before it, page numbers and download stamps, the signatures after it, '
    'the closing note on the update and the notes in parentheses ("(Redação dada pela Emenda nº ...)", "(Pela Emenda '
    'nº ...)") are left out.',
    'Each law is given as enacted, from the printout of its entry in the Diário Oficial Eletrônico do Município de '
    'Maceió that the Câmara lists, credited to the law itself and dated by the entry\'s "Publicada em" date. Later '
    'amendments by other laws are not worked into earlier laws: each law is its own file set as published. The text '
    'runs from the law\'s heading to its signatures; the printout\'s page header and footer and the gazette\'s '
    'publication block are left out. Copies without a text layer (scans) are left out.',
    'Lines are joined into paragraphs: a new paragraph starts at a provision label, a heading line, or after a line '
    'ending in ".", ";" or ":". One file per Art.; headings of the Títulos, Capítulos and Seções stand above the '
    'first article under them; "000-titulo" holds what comes before the first article. Text after the last article '
    '(place, date, signatures) stays with the last article.',
]
AI = ["Claude Code (claude-opus-5-5) wrote Lexifina's code and chose the sources. No model output is used as legal "
      "text or dates: every word comes from the Câmara Municipal de Maceió's PDFs."]


def lom(today):
    pdf = RAW / sha(LOM_URL.encode())
    lines, notes = strip_notes(paragraphs(lom_lines(pdf)))
    ds = sorted(d for n in notes for d in dmy(n) if d <= today)
    units = units_of(lines, title_label='Preâmbulo', adt=False)
    key = 'lei-organica-1990'
    laws = {key: {'label': 'Lei Orgânica do Município de Maceió, de 2 de abril de 1990',
                  'title': 'Lei Orgânica do Município de Maceió', 'kind': 'law', 'enacted': '1990-04-02',
                  'published': None, 'url': LOM_PAGE, 'temporary_until': None, 'restores': None, 'note': None}}
    v = {'from': ds[-1], 'source_url': LOM_URL, 'sha256': sha(pdf.read_bytes()), 'units': units,
         'note': f'Text in force as updated by the Câmara Municipal de Maceió (Emendas 01 to 43); its notes cite '
                 f'amendments of {len(set(ds))} dates, the latest {ds[-1]}.'}
    act = {'slug': 'lei-organica', 'short': 'LOM-Maceió', 'title': 'Lei Orgânica do Município de Maceió',
           'url': LOM_PAGE, 'first_law': None, 'earlier_laws': [key], 'versions': [v]}
    c = {'country': COUNTRY,
         'sources': [{'name': 'Câmara Municipal de Maceió: Lei Orgânica do Município, texto atualizado (PDF)',
                      'url': LOM_PAGE, 'retrieved': today, 'licence': COUNTRY['licence_note'], 'notes': '1 act.'}],
         'laws': laws, 'acts': [act], 'applies': [], 'decisions': DECISIONS, 'ai_use': AI}
    print(write_part(HERE / 'corpus.d', '10-lei-organica', c), len(units), ds[-1], len(notes))


FURNITURE = re.compile(r'^(?:Baixado Em:.*|\d+/\d+|https?://\S+|\d{2}/\d{2}/\d{4},? \d{2}:\d{2}|'
                       r'.* [—-] Di[áa]rio Oficial Eletr[ôo]nico do Munic[íi]pio de Macei[óo]|Prefeitura Municipal de Macei[óo])$')
PUBDAY = re.compile(r'publicada no Di[áa]rio Oficial Eletr[ôo]nico do Munic[íi]pio de Macei[óo] no dia (\d{2})/(\d{2})/(\d{4})')
PUBDATE = re.compile(r'^Publicada em$')


def law_lines(pdf):
    """The law's lines and its gazette publication date, or (None, reason)."""
    raw = []
    for p in pymupdf.open(pdf):
        ls = [norm(l) for l in p.get_text().split('\n')]
        ls = [l for l in ls if l]
        while ls and FURNITURE.match(ls[-1]):
            ls.pop()
        raw += ls
    if not raw:
        return None, 'no text layer'
    try:
        start = next(i for i, l in enumerate(raw) if re.match(r'LEI\s+N', l))
        end = next(i for i, l in enumerate(raw) if i > start and (l.startswith('Publicado por:') or PUBDATE.match(l)
                                                                   or l.startswith('Matéria publicada no Diário')))
    except (StopIteration, ValueError):
        return None, 'not a gazette printout'
    pub = [raw[i + 1] for i, l in enumerate(raw) if PUBDATE.match(l) and i + 1 < len(raw)]
    m = re.fullmatch(r'(\d{2})/(\d{2})/(\d{4})', pub[0]) if pub else PUBDAY.search(' '.join(raw[end:]))
    if not m:
        return None, 'no publication date'
    return (raw[start:end], f'{m.group(3)}-{m.group(2)}-{m.group(1)}'), 'ok'


def law_act(e, today):
    url = e['url']
    pdf = RAW / sha(url.encode())
    if not pdf.exists():
        return None, {}, 'document unavailable on the site' if Path(str(pdf) + '.500').exists() else 'not fetched'
    if not e.get('number') or not e.get('date'):
        return None, {}, 'odd list heading'
    try:
        got, why = law_lines(pdf)
    except Exception as ex:  # a damaged PDF
        return None, {}, f'unreadable ({type(ex).__name__})'
    if got is None:
        return None, {}, why
    lines, published = got
    enacted, n = e['date'], int(e['number'])
    if published < enacted or published > today or int(published[:4]) - int(enacted[:4]) > 1:
        return None, {}, 'publication date out of range of the listed date'
    paras = [('h2' if h else 'p', norm(t)) for h, t in paragraphs(lines, caps_break=False)]
    units = units_of(paras, adt=False)
    if not any(k.startswith('art-') for k in units):
        return None, {}, 'no article'
    y = enacted[:4]
    key = slug = f'lei-{y}-{n:05d}'
    label = f'Lei nº {n:,}'.replace(',', '.') + f', de {enacted[8:10]}/{enacted[5:7]}/{y}'
    ementa = norm(e.get('ementa') or '')
    ementa = ementa[:1].upper() + ementa[1:].lower() if ementa.isupper() else ementa
    laws = {key: {'label': label, 'title': ementa or label, 'kind': 'law', 'enacted': enacted, 'published': published,
                  'url': url, 'temporary_until': None, 'restores': None, 'note': None}}
    v = {'from': published, 'source_url': url, 'sha256': sha(pdf.read_bytes()), 'units': units}
    act = {'slug': slug, 'short': f'Lei {n}/{y}',
           'title': label + (f' ({ementa})' if ementa and len(ementa) < 160 else ''),
           'url': url, 'first_law': key, 'earlier_laws': [], 'versions': [v]}
    return act, laws, 'ok'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--today', required=True)
    ap.add_argument('--part-size', type=int, default=50)
    ap.add_argument('--only-year', type=int, help='parse only this year (the others stay as they are)')
    ap.add_argument('--lom-only', action='store_true')
    a = ap.parse_args()
    if not (HERE / 'corpus.d' / '10-lei-organica.PUBLISH').exists():
        lom(a.today)
    if a.lom_only:
        return
    idx_p = HERE / '.cache' / 'index.json'
    idx = json.loads(idx_p.read_text(encoding='utf-8')) if idx_p.exists() else {}
    by_year = {}
    for e in idx.values():
        if e.get('date'):
            by_year.setdefault(e['date'][:4], []).append(e)
    why, left = {}, {}
    # Laws whose text the independent second reader (check_letters.py, pdftotext) reads differently (tables and
    # multi-column layouts in another order, words placed elsewhere) are left out rather than published unchecked.
    xp = HERE / 'letters-excluded.json'
    excluded = set(json.loads(xp.read_text(encoding='utf-8'))) if xp.exists() else set()
    for y in sorted(by_year, reverse=True):
        if a.only_year and int(y) != a.only_year:
            continue
        es = by_year[y]
        # a year is parsed only when every listed law of it has been fetched (or found unavailable)
        if any(not any(Path(str(RAW / sha(e['url'].encode())) + x).exists() for x in ('', '.404', '.500')) for e in es):
            continue
        acts = {}
        for e in sorted(es, key=lambda e: e['id']):
            act, l, w = law_act(e, a.today)
            why[w] = why.get(w, 0) + 1
            if w == 'ok' and act['slug'] in excluded:
                w = 'the second PDF reader reads it differently'
                why[w] = why.get(w, 0) + 1
            if w != 'ok':
                left[str(e['id'])] = f'{e.get("heading")}: {w}'
                continue
            if act['slug'] in acts:
                why['duplicate'] = why.get('duplicate', 0) + 1
                left[str(e['id'])] = f'{e.get("heading")}: duplicate of an earlier listing'
                continue
            acts[act['slug']] = (act, l)
        # Parts already PUBLISHed stay as they are (main only grows): their laws are kept out of new parts, which
        # are numbered after them.
        done, n0 = set(), 0
        for q in sorted((HERE / 'corpus.d').glob(f'30-lei-{y}-*.json')):
            if q.with_suffix('.PUBLISH').exists():
                done |= {x['slug'] for x in json.loads(q.read_text(encoding='utf-8'))['acts']}
                n0 = max(n0, int(q.stem.rsplit('-', 1)[1]))
        order = sorted((x for x in acts.values() if x[0]['slug'] not in done), key=lambda x: x[0]['slug'])
        for i in range(0, len(order), a.part_size):
            name = f'30-lei-{y}-{n0 + i // a.part_size + 1:02d}'
            chunk = order[i:i + a.part_size]
            laws = {}
            for _, l in chunk:
                laws.update(l)
            c = {'country': COUNTRY,
                 'sources': [{'name': f'Câmara Municipal de Maceió: Leis of {y}, as published in the Diário Oficial '
                                      f'Eletrônico do Município de Maceió (PDF printouts of the gazette entries)',
                              'url': BASE + '/leisx', 'retrieved': a.today, 'licence': COUNTRY['licence_note'],
                              'notes': f'{len(chunk)} acts in this part.'}],
                 'laws': laws, 'acts': [x[0] for x in chunk], 'applies': [], 'decisions': DECISIONS, 'ai_use': AI}
            print(write_part(HERE / 'corpus.d', name, c), len(chunk))
    lp = HERE / 'left-out.json'
    if a.only_year and lp.exists():
        left = {**{k: v for k, v in json.loads(lp.read_text(encoding='utf-8')).items() if k not in left}, **left}
    lp.write_text(json.dumps(left, indent=0, ensure_ascii=False), encoding='utf-8')
    print(why)


if __name__ == '__main__':
    main()
