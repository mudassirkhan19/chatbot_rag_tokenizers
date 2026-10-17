# TEI fixtures

These files are GROBID 0.9.1-crf's TEI output for two papers, some of them trimmed or rearranged by hand. They hold text from those papers, which may be shared because both papers are under CC BY 4.0: the licence the Snapshot's arXiv record gives for that Version, as `data/manifest.csv` shows. ADR 0033 says why these may be committed while the parse cache may not; `tests/test_parse_fixtures.py` checks every fixture is listed here under a licence the manifest records.

| Fixture | Paper | Authors | arXiv | Licence | Changes |
|---|---|---|---|---|---|
| `wechsel_2112.06598v2.tei.xml` | WECHSEL: Effective initialization of subword embeddings for cross-lingual transfer of monolingual language models | Benjamin Minixhofer, Fabian Paischer, Navid Rekabsaz | 2112.06598v2 | [CC BY 4.0](http://creativecommons.org/licenses/by/4.0/) | GROBID's output, with only its request time (`application/@when`) fixed |
| `wechsel-elements.tei.xml` | the same | the same | 2112.06598v2 | [CC BY 4.0](http://creativecommons.org/licenses/by/4.0/) | Trimmed to a few body Sections, one figure and one table in the body, the acknowledgements, two annex Sections with a table, and three references |
| `appendix-in-body.tei.xml` | the same | the same | 2112.06598v2 | [CC BY 4.0](http://creativecommons.org/licenses/by/4.0/) | Trimmed and rearranged, with the appendices and acknowledgements in the body; a few headings and one caption are made up for the tests (the file's opening comment lists them) |
| `near-empty.tei.xml` | Neural Machine Translation of Rare Words with Subword Units | Rico Sennrich, Barry Haddow, Alexandra Birch | 1508.07909v5 | [CC BY 4.0](http://creativecommons.org/licenses/by/4.0/) | Cut to the abstract and one paragraph of the introduction; funders and bibliography removed; request time fixed |
| `scanned.tei.xml` | the same | the same | 1508.07909v5 | [CC BY 4.0](http://creativecommons.org/licenses/by/4.0/) | Cut to the header, with no abstract and an empty body, as for a PDF with no text layer; funders removed; request time fixed |
| `missed-table.tei.xml` | the same | the same | 1508.07909v5 | [CC BY 4.0](http://creativecommons.org/licenses/by/4.0/) | Cut to the abstract and Sections 4.1 and 5.1, whose paragraphs hold the cells of tables GROBID missed; figures, funders and back matter removed; request time fixed |

The papers are at <https://arxiv.org/abs/2112.06598v2> and <https://arxiv.org/abs/1508.07909v5>. A new fixture must come from a Version the manifest records as CC BY 4.0, and gets a row here.
