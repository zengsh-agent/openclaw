---
name: scholar-bibtex
description: "Fetch academic paper bibtex from Crossref, arXiv, and Semantic Scholar. Usage: python3 scripts/fetch_bibtex.py \"<paper title>\""
metadata:
  {
    "openclaw": { "requires": { "bins": ["python3", "curl"] } }
  }
---

# Scholar Bibtex

Fetch academic paper bibtex from Crossref, arXiv, and Semantic Scholar.

## Usage

When user provides a paper title or keywords:

```bash
python3 scripts/fetch_bibtex.py "<query>"
```

For example:

```bash
python3 scripts/fetch_bibtex.py "attention is all you need"
python3 scripts/fetch_bibtex.py "10.1038/s41586-025-09529-3"
```

## Output

The script outputs:

1. Search results with paper titles, years, and authors
2. Bibtex entries for each paper

Example output:

```
Searching for: attention is all you need

=== Searching Crossref ===
=== Searching Semantic Scholar ===
=== Searching arXiv ===

Found 3 papers total:
  1. [crossref] Attention is All You Need (2017) - Vaswani, Ashish and Shazeer, Noam and Parmar, Niki and ...
  ...

============================================================

--- Paper 1 (crossref) ---
@article{vaswani2017attention,
  title = {Attention Is All You Need},
  author = {Vaswani, Ashish and Shazeer, Noam and Parmar, Niki and ...},
  journal = {Advances in Neural Information Processing Systems},
  year = {2017},
  volume = {30},
  doi = {...}
}
```

## API Sources

The script searches in this priority order:

1. **Crossref** — Best for journal papers (Nature, Science, Cell, etc.)
2. **Semantic Scholar** — Academic search engine
3. **arXiv** — Preprints in CS/ML/physics

## Features

- Deduplicates by DOI (shows both preprint and published version if different)
- Generates proper bibtex with:
  - Title, authors, year
  - Journal name, volume, issue, pages
  - DOI
  - arXiv eprint (for preprints)
- Fetches original bibtex from arXiv when available
