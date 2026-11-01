"""Independent letters-and-digits check of every version against its PDF, read with a second PDF reader (poppler's
pdftotext, not the builder's PyMuPDF) and none of the builder's code.

    python -X utf8 check_letters.py [part.json ...]

Lei Orgânica: the pdftotext text from "LEI ORGÂNICA DO MUNICÍPIO DE MACEIÓ" followed by "A CÂMARA MUNICIPAL DE
MACEIÓ" to "Maceió – AL, 02 de abril de 1990.", with the "Baixado Em: <date>" stamps, each page's number (the last word before its
page break) and every note in parentheses starting "Redação dada pel" or "Pela Emenda" removed.

Laws: with the printout's page header ("Baixado Em: ...", the print date and time, "<title> — Diário Oficial
Eletrônico do Município de Maceió" or "Prefeitura Municipal de Maceió") and footer (the entry's address, "n/m") removed, the pdftotext text from the first
"LEI N" to the first "Publicado por:", "Publicada em" or "Matéria publicada" (the gazette's publication
block).

Either text, reduced to letters and digits, must equal the version's unit files reduced the same way, each unit found
at its place in document order.
"""
import hashlib, json, re, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW = HERE / '.cache' / 'www' / 'raw'
OPENERS = ('redação dada pel', 'redacao dada pel', 'pela emenda')


def ld(s):
    return ''.join(ch for ch in s if ch.isalnum())


def strip_notes(t):
    out, changed = t, True
    while changed:
        changed = False
        for m in list(re.finditer(r'\(([^()]*)\)', out))[::-1]:
            inner = re.sub(r'\s+', ' ', m.group(1)).strip().lower()
            if inner.startswith(OPENERS):
                out = out[:m.start()] + ' ' + out[m.end():]
                changed = True
    return out


def pdftotext(path):
    return subprocess.run(['pdftotext', '-enc', 'UTF-8', str(path), '-'], capture_output=True,
                          check=True).stdout.decode('utf-8')


def lom_text(path):
    t = re.sub(r'(?<=\s)\d{1,3}\s*\f', '\n', pdftotext(path))  # each page's number: its last word
    t = re.sub(r'(?m)^\s*Baixado Em:\s*\d{2}/\d{2}/\d{4}\s*$', ' ', t.replace('\f', '\n'))
    a = re.search(r'LEI ORGÂNICA DO MUNICÍPIO DE MACEIÓ\s+A CÂMARA MUNICIPAL DE MACEIÓ', t).start()
    end = 'Maceió – AL, 02 de abril de 1990.'
    b = t.index(end, a) + len(end)
    return strip_notes(t[a:b])


def law_text(path):
    t = pdftotext(path).replace('\f', '\n').replace('\r', '')
    t = re.sub(r'(?m)^(\s*Baixado Em:.*\n\s*)Prefeitura Municipal de Maceió[ \t]*', r'\1', t)  # header at page top
    t = re.sub(r'(?m)^\s*Baixado Em:.*$', ' ', t)
    t = re.sub(r'(?m)^.*\S\s+[—–-]+\s+Diário Oficial Eletrônico do Município de Maceió\s*$', ' ', t)
    t = re.sub(r'(?m)^\s*\d{2}/\d{2}/\d{4},? \d{2}:\d{2}\s*$', ' ', t)
    t = re.sub(r'(?m)^\s*Prefeitura Municipal de Maceió\s*$', ' ', t)
    t = re.sub(r'(?m)^\s*https?://\S+(?:\s+\d+/\d+)?\s*$', ' ', t)
    t = re.sub(r'(?m)^\s*\d+/\d+\s*$', ' ', t)
    a = re.search(r'LEI\s+N', t).start()
    b = min(i for i in (t.find('Publicado por:', a), t.find('Publicada em', a), t.find('Matéria publicada', a)) if i > 0)
    return t[a:b]


def main(paths):
    bad = total = 0
    for p in paths:
        for a in json.load(open(p, encoding='utf-8'))['acts']:
            for v in a['versions']:
                path = RAW / hashlib.sha256(v['source_url'].encode()).hexdigest()
                assert hashlib.sha256(path.read_bytes()).hexdigest() == v['sha256'], (a['slug'], 'sha256')
                src = ld(lom_text(path) if a['slug'] == 'lei-organica' else law_text(path))
                rest = {k: ld(re.sub(r'(?m)^#+ ', '', u['text'])) for k, u in v['units'].items()}
                pos = 0
                while rest:
                    hit = None
                    for k, t in rest.items():
                        if t and src.startswith(t, pos) and (hit is None or len(t) > len(rest[hit])):
                            hit = k
                    if hit is None:
                        break
                    pos += len(rest.pop(hit))
                total += 1
                if rest or pos != len(src):
                    bad += 1
                    print(f'MISMATCH {a["slug"]} {v["from"]}: matched {pos}/{len(src)}; next source: '
                          f'{src[pos:pos + 80]!r}; unplaced: {list(rest)[:5]}')
    print(f'{total} versions checked, {bad} mismatches')
    return bad


if __name__ == '__main__':
    sys.exit(1 if main(sys.argv[1:] or sorted(str(p) for p in (HERE / 'corpus.d').glob('*.json'))) else 0)
