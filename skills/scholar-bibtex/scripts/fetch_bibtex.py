#!/usr/bin/env python3
"""
Fetch bibtex from Crossref, arXiv, and Semantic Scholar.
Usage: python fetch_bibtex.py "<query>"
"""

import sys
import requests
import json
import urllib.parse
import re

CROSSREF_API = "https://api.crossref.org/works"
ARXIV_API = "http://export.arxiv.org/api/query"
SEMANTIC_SCHOLAR_API = "https://api.semanticscholar.org/graph/v1/paper/search"
SEMANTIC_SCHOLAR_PAPER_API = "https://api.semanticscholar.org/graph/v1/paper"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}


def search_by_doi(doi):
    """Fetch paper by DOI directly."""
    try:
        doi = doi.strip()
        if doi.startswith("https://doi.org/"):
            doi = doi.replace("https://doi.org/", "")
        
        url = f"{SEMANTIC_SCHOLAR_PAPER_API}/DOI:{doi}?fields=title,authors,year,venue,citationCount,externalIds"
        response = requests.get(url, headers=HEADERS, timeout=30)
        if response.status_code == 200:
            paper = response.json()
            paper['source'] = 'semantic'
            return [paper]
    except Exception as e:
        print(f"DOI lookup error: {e}", file=sys.stderr)
    return []


def search_semantic_scholar(query, limit=5):
    """Search for papers via Semantic Scholar."""
    params = {
        "query": query,
        "limit": limit,
        "fields": "title,authors,year,venue,abstract,citationCount,paperId,externalIds"
    }
    
    try:
        response = requests.get(SEMANTIC_SCHOLAR_API, params=params, headers=HEADERS, timeout=30)
        if response.status_code == 200:
            data = response.json()
            papers = []
            for item in data.get("data", []):
                item['source'] = 'semantic'
                papers.append(item)
            return papers
    except Exception as e:
        print(f"Semantic Scholar error: {e}", file=sys.stderr)
    return []


def search_crossref(query, limit=5):
    """Search for papers via Crossref."""
    params = {
        "query": query,
        "rows": limit
    }
    
    try:
        response = requests.get(CROSSREF_API, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        items = data.get("message", {}).get("items", [])
        for item in items:
            item['source'] = 'crossref'
        return items
    except Exception as e:
        print(f"Crossref error: {e}", file=sys.stderr)
    return []


def search_arxiv(query, limit=5):
    """Search for papers via arXiv."""
    params = {
        "search_query": f"all:{query}",
        "max_results": limit,
        "sortBy": "relevance",
        "sortOrder": "descending"
    }
    
    response = requests.get(ARXIV_API, params=params, timeout=30)
    content = response.text
    
    papers = []
    entries = re.findall(r'<entry>(.*?)</entry>', content, re.DOTALL)
    
    for entry in entries:
        paper = {}
        
        title_match = re.search(r'<title>(.*?)</title>', entry, re.DOTALL)
        if title_match:
            paper['title'] = title_match.group(1).replace('\n', ' ').strip()
        
        authors = re.findall(r'<name>(.*?)</name>', entry)
        paper['authors'] = [{'name': a.strip()} for a in authors]
        
        published_match = re.search(r'<published>(.*?)</published>', entry)
        if published_match:
            paper['year'] = published_match.group(1)[:4]
        
        abstract_match = re.search(r'<summary>(.*?)</summary>', entry, re.DOTALL)
        if abstract_match:
            paper['abstract'] = abstract_match.group(1).strip()
        
        id_match = re.search(r'<id>(.*?)</id>', entry)
        if id_match:
            paper['arxiv_id'] = id_match.group(1).split('/')[-1]
        
        categories = re.findall(r'<category term="(.*?)"', entry)
        paper['categories'] = categories
        
        paper['source'] = 'arxiv'
        papers.append(paper)
    
    return papers


def generate_bibtex_crossref(paper):
    """Generate bibtex entry from Crossref paper data."""
    # Extract all fields
    title = paper.get("title", [""])[0] if paper.get("title") else ""
    
    authors = paper.get("author", [])
    author_parts = []
    for a in authors:
        given = a.get("given", "")
        family = a.get("family", "")
        if given and family:
            author_parts.append(f"{family}, {given}")
        elif family:
            author_parts.append(family)
    author_str = " and ".join(author_parts)
    
    # Get year from multiple possible fields
    year = ""
    for date_field in ["published-print", "published-online", "published"]:
        published = paper.get(date_field, {})
        date_parts = published.get("date-parts", [[]])
        if date_parts and date_parts[0]:
            year = str(date_parts[0][0])
            break
    
    if not year:
        # Try 'created' field
        created = paper.get("created", {})
        date_parts = created.get("date-parts", [[]])
        if date_parts and date_parts[0]:
            year = str(date_parts[0][0])
    
    journal = paper.get("container-title", [""])[0] if paper.get("container-title") else ""
    volume = paper.get("volume", "")
    issue = paper.get("issue", "")
    pages = paper.get("page", "")
    doi = paper.get("DOI", "")
    
    # Generate citation key
    first_author = authors[0].get("family", "unknown").lower() if authors else "unknown"
    first_author = re.sub(r'[^a-z]', '', first_author)
    citation_key = f"{first_author}{year}" if year else f"{first_author}unknown"
    
    # Build bibtex
    bibtex = f"@article{{{citation_key},\n"
    bibtex += f"  title = {{{title}}},\n"
    bibtex += f"  author = {{{author_str}}},\n"
    
    if journal:
        bibtex += f"  journal = {{{journal}}},\n"
    if year:
        bibtex += f"  year = {{{year}}},\n"
    if volume:
        bibtex += f"  volume = {{{volume}}},\n"
    if issue:
        bibtex += f"  number = {{{issue}}},\n"
    if pages:
        bibtex += f"  pages = {{{pages}}},\n"
    if doi:
        bibtex += f"  doi = {{{doi}}},\n"
    
    # Remove trailing comma and newline, close bracket
    bibtex = bibtex.rstrip(",\n") + "\n}"
    
    return bibtex


def generate_bibtex_arxiv(paper):
    """Generate bibtex entry from arXiv paper data."""
    title = paper.get("title", "")
    authors = paper.get("authors", [])
    year = paper.get("year", "")
    arxiv_id = paper.get("arxiv_id", "")
    categories = paper.get("categories", [])
    
    author_str = " and ".join([a["name"] for a in authors])
    
    first_author = authors[0]["name"].split()[-1].lower() if authors else "unknown"
    first_author = re.sub(r'[^a-z]', '', first_author)
    citation_key = f"{first_author}{year}" if year else f"{first_author}unknown"
    
    journal = f"arXiv preprint arXiv:{arxiv_id}"
    
    bibtex = f"@article{{{citation_key},\n"
    bibtex += f"  title = {{{title}}},\n"
    bibtex += f"  author = {{{author_str}}},\n"
    bibtex += f"  journal = {{{journal}}},\n"
    bibtex += f"  year = {{{year}}},\n"
    bibtex += f"  eprint = {{{arxiv_id}}},\n"
    bibtex += f"  archivePrefix = {{arXiv}},\n"
    if categories:
        bibtex += f"  primaryClass = {{{categories[0]}}},\n"
    bibtex = bibtex.rstrip(",\n") + "\n}"
    
    return bibtex


def get_original_arxiv_bibtex(arxiv_id):
    """Fetch original bibtex from arXiv."""
    try:
        url = f"https://arxiv.org/bibtex/{arxiv_id}"
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            return response.text
    except:
        pass
    return None


def generate_bibtex_semantic(paper):
    """Generate bibtex entry from Semantic Scholar paper data."""
    title = paper.get("title", "")
    authors = paper.get("authors", [])
    year = paper.get("year", "")
    venue = paper.get("venue", "")
    citation_count = paper.get("citationCount", 0)
    external_ids = paper.get("externalIds", {})
    
    doi = external_ids.get("DOI", "")
    arxiv_id = external_ids.get("ArXiv", "")
    
    author_str = " and ".join([a.get("name", "") for a in authors])
    
    first_author = authors[0].get("name", "unknown").split()[-1].lower() if authors else "unknown"
    first_author = re.sub(r'[^a-z]', '', first_author)
    citation_key = f"{first_author}{year}" if year else f"{first_author}unknown"
    
    if arxiv_id:
        journal = f"arXiv preprint arXiv:{arxiv_id}"
    elif venue:
        journal = venue
    else:
        journal = ""
    
    bibtex = f"@article{{{citation_key},\n"
    bibtex += f"  title = {{{title}}},\n"
    bibtex += f"  author = {{{author_str}}},\n"
    if journal:
        bibtex += f"  journal = {{{journal}}},\n"
    if year:
        bibtex += f"  year = {{{year}}},\n"
    if doi:
        bibtex += f"  doi = {{{doi}}},\n"
    if arxiv_id:
        bibtex += f"  eprint = {{{arxiv_id}}},\n"
        bibtex += f"  archivePrefix = {{arXiv}},\n"
    bibtex += f"  note = {{Citation count: {citation_count}}}\n"
    bibtex = bibtex.rstrip(",\n") + "\n}"
    
    return bibtex


def main():
    if len(sys.argv) < 2:
        print("Usage: python fetch_bibtex.py \"<query>\"", file=sys.stderr)
        sys.exit(1)
    
    query = sys.argv[1]
    print(f"Searching for: {query}", file=sys.stderr)
    
    # Check if query is a DOI
    is_doi = "doi.org" in query.lower() or query.startswith("10.") or "/doi/" in query.lower()
    
    all_papers = []
    seen_dois = set()  # Track by DOI to avoid duplicates
    
    try:
        # If it's a DOI, fetch directly
        if is_doi:
            print("\n=== Fetching by DOI ===", file=sys.stderr)
            semantic_papers = search_by_doi(query)
            for p in semantic_papers:
                p['source'] = 'semantic'
                all_papers.append(p)
                # Add to seen_dois
                doi = p.get('externalIds', {}).get('DOI', '')
                if doi:
                    seen_dois.add(doi.lower())
        else:
            # Search all sources in parallel priority order:
            # 1. Crossref (best for journal papers - Nature, Science, etc.)
            # 2. Semantic Scholar
            # 3. arXiv (for CS/ML preprints)
            
            print("\n=== Searching Crossref ===", file=sys.stderr)
            crossref_papers = search_crossref(query, limit=10)
            for p in crossref_papers:
                doi = p.get("DOI", "").lower()
                if doi and doi in seen_dois:
                    continue
                all_papers.append(p)
                if doi:
                    seen_dois.add(doi)
            
            print("=== Searching Semantic Scholar ===", file=sys.stderr)
            semantic_papers = search_semantic_scholar(query, limit=5)
            for p in semantic_papers:
                doi = p.get("externalIds", {}).get("DOI", "").lower()
                if doi and doi in seen_dois:
                    continue
                p['source'] = 'semantic'
                all_papers.append(p)
                if doi:
                    seen_dois.add(doi)
            
            print("=== Searching arXiv ===", file=sys.stderr)
            arxiv_papers = search_arxiv(query, limit=3)
            for p in arxiv_papers:
                arxiv_id = p.get("arxiv_id", "").lower()
                if arxiv_id and arxiv_id in seen_dois:
                    continue
                all_papers.append(p)
                if arxiv_id:
                    seen_dois.add(arxiv_id)
        
        if not all_papers:
            print("No papers found.")
            sys.exit(1)
        
        print(f"\nFound {len(all_papers)} papers total:", file=sys.stderr)
        
        # Deduplicate by title for display
        displayed_titles = set()
        for i, paper in enumerate(all_papers):
            # Handle title as either string or list
            title_raw = paper.get("title")
            if isinstance(title_raw, list):
                title = title_raw[0] if title_raw else "Unknown"
            else:
                title = title_raw or "Unknown"
            
            if title.lower() in displayed_titles:
                continue
            displayed_titles.add(title.lower())
            
            year = paper.get("year", "N/A")
            source = paper.get("source", "")
            
            if source == 'crossref':
                authors = paper.get("author", [])
                author_names = ", ".join([f"{a.get('given', '')} {a.get('family', '')}".strip() for a in authors]) if authors else "Unknown"
            elif source == 'arxiv':
                authors = paper.get("authors", [])
                author_names = ", ".join([a["name"] for a in authors]) if authors else "Unknown"
            elif source == 'semantic':
                authors = paper.get("authors", [])
                author_names = ", ".join([a.get("name", "") for a in authors]) if authors else "Unknown"
            else:
                author_names = "Unknown"
            
            print(f"  {i+1}. [{source}] {title} ({year}) - {author_names[:80]}...", file=sys.stderr)
        
        print("\n" + "="*60 + "\n", file=sys.stderr)
        
        # Output bibtex for each paper
        for i, paper in enumerate(all_papers):
            # Handle title as either string or list
            title_raw = paper.get("title")
            if isinstance(title_raw, list):
                title = title_raw[0] if title_raw else ""
            else:
                title = title_raw or ""
            
            if title.lower() not in displayed_titles:
                continue
                
            source = paper.get("source", "")
            
            if source == 'crossref':
                bibtex = generate_bibtex_crossref(paper)
            elif source == 'arxiv':
                arxiv_id = paper.get("arxiv_id", "")
                original_bibtex = get_original_arxiv_bibtex(arxiv_id)
                if original_bibtex:
                    bibtex = original_bibtex
                else:
                    bibtex = generate_bibtex_arxiv(paper)
            elif source == 'semantic':
                bibtex = generate_bibtex_semantic(paper)
            else:
                bibtex = generate_bibtex_arxiv(paper)
            
            print(f"\n--- Paper {i+1} ({source}) ---")
            print(bibtex)
            print()
            
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error parsing response: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
