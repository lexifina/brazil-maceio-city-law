# Maceió (city): law history in git

Part of [lexifina/global-law](https://github.com/lexifina/global-law), one git history for every country's law: this is the law of Maceio, Alagoas, Brazil, which global-law reads at `brazil/alagoas/maceio/acts/`.

The municipal law of the Município de Maceió, the city of Maceió (Alagoas) (Brazil) as a git history: one file per Artigo, one paragraph per line, so `git blame`, `git log` and `git diff` work line by line. The text is Portuguese, the only official language.

It follows the shared design of [lexifina/global-law](https://github.com/lexifina/global-law).

## What this repository holds

| Folder | Act | Versions |
| --- | --- | ---: |
| `lei-organica/` | Lei Orgânica do Município de Maceió (1990), as updated by the Câmara (Emendas 01 to 43) | 1 |
| `lei-<year>-<number>/` | the municipal Leis the Câmara lists, as published in the Diário Oficial Eletrônico do Município | 1 each |

**Partial, and growing:** the Leis are added newest first, as the Câmara's PDFs are read; the history may still gain earlier commits. Each Lei is given **as enacted**, as its gazette entry printed it; later amendments by other Leis are not worked into it. The Lei Orgânica is given **only as the Câmara's updated edition**, credited to the Câmara as the oldest version available. Federal law is in [brazil-law](https://github.com/lexifina/brazil-law).

## Source

[Câmara Municipal de Maceió](https://www.maceio.al.leg.br), published by the Câmara Municipal de Maceió. Each version names the page it was taken from and that page's sha256, in `data/versions.json`.

## Dates

Each Lei is dated by the "Publicada em" date of its entry in the Diário Oficial Eletrônico do Município de Maceió (Maceió's laws almost always take effect on publication). The Lei Orgânica's one version is dated by the latest date among the amendments the edition's notes cite (Emenda nº 43, 25 June 2019). Commits are at noon in Maceió.

## How it is built

Lexifina reads the sources listed here and records each act's dated versions, and the laws that made each change, in one corpus file. `tools/build.py` writes this repository from that file, and the same corpus always gives the same commit hashes; `REPRODUCE.md` gives the details and the checks. A model (Claude) wrote Lexifina's code; it wrote no legal text, and no model runs when the history is built.

The Lei Orgânica is taken from the Câmara's PDF from its heading to "Maceió - AL, 02 de abril de 1990."; the alphabetical index before it, page numbers and download stamps, the signatures and the closing note on the update are left out, as are the notes in parentheses ("(Redação dada pela Emenda nº ...)", "(Pela Emenda nº ...)"). Each Lei is taken from the PDF printout of its gazette entry, from its heading ("LEI Nº ...") to its signatures; the printout's page header and footer and the gazette's publication block are left out. The text layers are read with PyMuPDF line by line and lines are joined into paragraphs (a new paragraph at each provision label, heading, or after a line ending in ".", ";" or ":"). One file per Art.; headings stand above the first article under them; `000-titulo.md` holds what comes before the first article.

## How it is checked

Every version is read back from git on the day it took effect (`tools/check_repo.py`) and must match the corpus; an independent letters-and-digits comparison of every version against the source page must show no difference. Results are in `REPRODUCE.md`.

## What "author" means

The author of each commit is the law that made the text, or, for a consolidated text, the publisher, with an e-mail address that cannot exist; the committer is always Lexifina.

## Limits

Not a complete history: the Lei Orgânica starts at its updated edition (the text of 2 April 1990 and the wordings its amendments replaced are not reconstructed), and the Leis are as enacted, without later amendments worked in. Copies without a text layer (scans) are left out; `data/` lists what is in. The text is not the official version: only the Diário Oficial Eletrônico do Município de Maceió is authoritative. Text after the last article (place, date, signatures, annexes) stays in the last article's file.

## Licence

See [LICENSE](LICENSE): Brazilian law texts are not protected by copyright (Lei 9.610/1998, art. 8, IV). Fonte: Câmara Municipal de Maceió, Câmara Municipal de Maceió.
