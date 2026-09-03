import time
import requests
from neo4j import GraphDatabase

# Neo4j and API Configuration
NEO4J_URI = "bolt://localhost:7687"
NEO4J_AUTH = ("neo4j", "mathoscope")

# Wikipedia API policy requires a custom User-Agent header
HEADERS = {"User-Agent": "Neo4jWikidataEnricher/1.0 (jacob@jacobcollard.com)"}


def get_wikipedia_title(wikidata_id):
    """Fetches the English Wikipedia article title corresponding to a Wikidata ID."""
    url = "https://www.wikidata.org/w/api.php"
    params = {
        "action": "wbgetentities",
        "ids": wikidata_id,
        "props": "sitelinks",
        "sitefilter": "enwiki",
        "format": "json"
    }
    try:
        response = requests.get(url, params=params, headers=HEADERS)
        data = response.json()
        return data["entities"][wikidata_id]["sitelinks"]["enwiki"]["title"]
    except (KeyError, requests.RequestException):
        return None


def get_first_two_paragraphs(wiki_title):
    """Extracts the first two plain-text paragraphs from a Wikipedia article intro."""
    url = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "prop": "extracts",
        "exintro": True,
        "explaintext": True,
        "titles": wiki_title,
        "format": "json"
    }
    try:
        response = requests.get(url, params=params, headers=HEADERS)
        data = response.json()
        pages = data["query"]["pages"]
        for _, page_info in pages.items():
            extract = page_info.get("extract", "")
            # Split text by line breaks and capture non-empty paragraphs
            paragraphs = [p.strip() for p in extract.split("\n") if p.strip()]
            return "\n\n".join(paragraphs[:2]) if paragraphs else None
    except requests.RequestException:
        return None


def enrich_neo4j_nodes():
    driver = GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)
    
    with driver.session() as session:
        # Fetch all nodes with a wikidata_id property
        query = "MATCH (n) WHERE n.wikidata_id IS NOT NULL RETURN elementId(n) AS node_id, n.wikidata_id AS wikidata_id"
        result = session.run(query)
        nodes = [(record["node_id"], record["wikidata_id"]) for record in result]
        
        print(f"Found {len(nodes)} nodes with 'wikidata_id'. Starting enrichment...")
        
        for node_id, wikidata_id in nodes:
            # Step 1: Get Wikipedia Article Title
            wiki_title = get_wikipedia_title(wikidata_id)
            if not wiki_title:
                continue
            
            # Step 2: Extract Summary Paragraphs
            summary = get_first_two_paragraphs(wiki_title)
            if not summary:
                continue
            
            # Step 3: Write back to Neo4j
            update_query = """
            MATCH (n) 
            WHERE elementId(n) = $node_id 
            SET n.wikipedia_summary = $summary
            """
            session.run(update_query, node_id=node_id, summary=summary)
            print(f"Updated node {node_id} with text from '{wiki_title}'")
            
            # Politeness delay for API rate limits
            time.sleep(0.1)

    driver.close()


if __name__ == "__main__":
    enrich_neo4j_nodes()
