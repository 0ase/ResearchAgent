import xml.etree.ElementTree as ET

def parse_arxiv_response(xml_text: str) -> list[dict]:
    """Parse the XML text returned by arXiv into a list of paper dictionaries"""
    root = ET.fromstring(xml_text)
    papers = []

    ns = {"atom": "http://www.w3.org/2005/Atom"}

    for entry in root.findall("atom:entry", ns):
        title = entry.find("atom:title", ns)
        summary = entry.find("atom:summary", ns)

        authors = []
        for author in entry.findall("atom:author", ns):
            name = author.find("atom:name", ns)
            if name is not None and name.text:
                authors.append(name.text)

        # Extract the arXiv ID (obtained by extracting from the URL)
        id_url = entry.find("atom:id", ns)
        arxiv_id = ""
        if id_url is not None and id_url.text:
            # "http://arxiv.org/abs/2301.12345v1" → "2301.12345"
            arxiv_id = id_url.text.split("/abs/")[-1].split("v")[0]

        papers.append({
            "title": title.text.strip() if title is not None and title.text else "Untitled",
            "authors": authors,
            "abstract": summary.text.strip() if summary is not None and summary.text else "",
            "source": "arxiv",
            "source_id": f"arxiv:{arxiv_id}",
            "published_date": "",
            "arxiv_id": arxiv_id, 
        })
    return papers