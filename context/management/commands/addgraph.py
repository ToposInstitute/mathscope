import argparse
import csv
import requests
import sys
import traceback

from django.core.management.base import BaseCommand, CommandError
from neo4j import GraphDatabase

class Command(BaseCommand):
    help = "Load MathGloss + Wikidata graph into Neo4j."

    def add_arguments(self, parser):

        parser.add_argument(
            'filename', 
            type=argparse.FileType('r', encoding="utf-8-sig"),
            metavar="FILE",
        )
        parser.add_argument(
            '-u',
            '--uri', 
            default="neo4j://localhost:7687",
        )
        parser.add_argument(
            '-p',
            '--password',
            default="mathoscope",
        )

    def handle(self, *args, **kwargs):


        try:
            uri = kwargs['uri']
            auth = ("neo4j", kwargs['password'])
            reader = csv.DictReader(kwargs['filename'])
            with GraphDatabase.driver(uri, auth=auth) as driver:
                driver.verify_connectivity()

                for row in reader:
                    node = MathglossNode(row)

                    add_mathgloss_node(driver, node)
                    expand_node(driver, node.wikidata_id)
        except Exception as e:
            print(f"An unexpected error occurred: {e}", file=sys.stderr)
            sys.exit(1)

class MathglossNode:

    def __init__(self, row):

        self.wikidata_id = row['Wikidata ID']
        self.wikidata_label = row['Wikidata Label']
        self.bct_name = row['BCT Name']
        self.bct_link = row['BCT Link']
        self.chicago_name = row['Chicago Name']
        self.chicago_link = row['Chicago Link']
        self.clowder_name = row['Clowder Name']
        self.clowder_link = row['Clowder Link']
        self.context_name = row['Context Name']
        self.context_link = row['Context Link']
        self.mathlib_name = row['Mathlib Name']
        self.mathlib_link = row['Mathlib Link']
        self.nlab_name = row['nLab Name']
        self.nlab_link = row['nLab Link']
        self.planet_name = row['PlanetMath Name']
        self.planet_link = row['PlanetMath Link']

def add_mathgloss_node(driver, node):

    query = """
    MERGE (t:Term {wikidata_id: $wikidata_id})
    ON CREATE SET
        t.wikidata_label = $wikidata_label,
        t.bct = $bct_name,
        t.chicago = $chicago_name,
        t.clowder = $clowder_name,
        t.context = $context_name,
        t.mathlib = $mathlib_name,
        t.nlab = $nlab_name,
        t.planetmath = $planet_name,
        t.is_base = true
    RETURN t
    """

    try:
        with driver.session() as session:
            result = session.execute_write(
                lambda tx: tx.run(
                    query,
                    wikidata_id=node.wikidata_id,
                    wikidata_label=node.wikidata_label,
                    bct_name=node.bct_name,
                    chicago_name=node.chicago_name,
                    clowder_name=node.clowder_name,
                    context_name=node.context_name,
                    mathlib_name=node.mathlib_name,
                    nlab_name=node.nlab_name,
                    planet_name=node.planet_name,
                ).single()
            )

            if result:
                print(f"Successfully added node '{node.wikidata_label}'")
            else:
                print("Failed to create node '{node.wikidata_label}'")
    except Exception as e:
        print(f"Database error for {node.wikidata_label}: {e}")

def expand_node(driver, node_id):

    query = """
    SELECT DISTINCT ?propertyID ?propertyLabel ?relatedElementID ?relatedElementLabel WHERE {
      wd:%s ?directProperty ?relatedElement .
      
      ?property wikibase:directClaim ?directProperty .
      
      ?relatedElement (wdt:P31|wdt:P279) / 
                      (wdt:P31|wdt:P279)? / 
                      (wdt:P31|wdt:P279)? / 
                      (wdt:P31|wdt:P279)? / 
                      (wdt:P31|wdt:P279)? wd:Q24034552 .

      BIND(REPLACE(STR(?property), "^.*/", "") AS ?propertyID)
      BIND(REPLACE(STR(?relatedElement), "^.*/", "") AS ?relatedElementID)
      
      SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
    }
    """

    ENDPOINT = "https://query.wikidata.org/sparql"
    HEADERS = {
        'User-Agent': 'mathoscope/0.1',
    }

    try:
        while True:
            result = requests.post(
                ENDPOINT,
                data={'query': query % node_id, 'format': 'json'},
                headers=HEADERS,
            )
            if result.status_code != 200:
                print(result)
                print("Too many requests. Retrying.")
                time.sleep(result.headers['retry-after'])
                continue
            break

        json = result.json()
        for item in json['results']['bindings']:
            relation_id = item['relatedElementID']['value']
            property_id = item['propertyID']['value']
            related_name = item['relatedElementLabel']['value']
            property_name = item['propertyLabel']['value']

            query = """
            MERGE (t:Term {wikidata_id: $related_id})
            ON CREATE SET
                t.wikidata_label = $related_label,
                t.is_base = false
            WITH t
            MERGE (e:Term {wikidata_id: $source_id})
            WITH t, e
            MERGE (e)-[r:RELATED_TO { rel_id: $rel_id }]->(t)
            ON CREATE SET
                r.label = $related_name
            """

            with driver.session() as session:
                session.execute_write(
                    lambda tx: tx.run(
                        query,
                        related_id=property_id,
                        related_label=related_name,
                        source_id=node_id,
                        rel_id=relation_id,
                        related_name=related_name,
                    )
                )

    except Exception as e:
        print(traceback.format_exc())
        #print(f"A '{type(e)}' error occurred: {e}.")
