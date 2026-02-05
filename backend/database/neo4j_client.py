"""
Neo4j Graph Database Client for PSUR Regulatory Grounding

Provides access to the regulatory knowledge graph containing:
- PSUR section definitions and requirements
- MDCG 2022-21 guidance mappings
- EU MDR article references
- FormQAR-054 template structure
- Cross-section dependencies
"""

import os
from typing import Dict, List, Any, Optional
from contextlib import contextmanager

try:
    from neo4j import GraphDatabase
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False
    GraphDatabase = None


class Neo4jClient:
    """Client for querying the PSUR regulatory knowledge graph."""
    
    _instance: Optional["Neo4jClient"] = None
    _driver = None
    
    def __init__(self):
        self.uri = os.getenv("NEO4J_URI", "")
        self.username = os.getenv("NEO4J_USERNAME", "neo4j")
        self.password = os.getenv("NEO4J_PASSWORD", "")
        self.database = os.getenv("NEO4J_DATABASE", "neo4j")
        self._driver = None
        
    @classmethod
    def get_instance(cls) -> "Neo4jClient":
        """Get singleton instance of Neo4j client."""
        if cls._instance is None:
            cls._instance = Neo4jClient()
        return cls._instance
    
    def connect(self) -> bool:
        """Establish connection to Neo4j database."""
        if not NEO4J_AVAILABLE:
            print("Neo4j driver not installed. Run: pip install neo4j")
            return False
            
        if not self.uri or not self.password:
            print("Neo4j credentials not configured in environment variables.")
            return False
            
        try:
            self._driver = GraphDatabase.driver(
                self.uri,
                auth=(self.username, self.password)
            )
            # Test connection
            with self._driver.session(database=self.database) as session:
                session.run("RETURN 1")
            print(f"Connected to Neo4j at {self.uri}")
            return True
        except Exception as e:
            print(f"Failed to connect to Neo4j: {e}")
            self._driver = None
            return False
    
    def close(self):
        """Close the database connection."""
        if self._driver:
            self._driver.close()
            self._driver = None
    
    @contextmanager
    def session(self):
        """Get a database session context manager."""
        if not self._driver:
            if not self.connect():
                yield None
                return
        
        session = self._driver.session(database=self.database)
        try:
            yield session
        finally:
            session.close()
    
    def is_connected(self) -> bool:
        """Check if connected to database."""
        return self._driver is not None
    
    # =========================================================================
    # SCHEMA EXPLORATION
    # =========================================================================
    
    def get_schema(self) -> Dict[str, Any]:
        """Get the database schema (node labels and relationship types)."""
        schema = {
            "node_labels": [],
            "relationship_types": [],
            "node_properties": {},
            "relationship_properties": {}
        }
        
        with self.session() as session:
            if session is None:
                return schema
            
            # Get node labels
            result = session.run("CALL db.labels()")
            schema["node_labels"] = [record["label"] for record in result]
            
            # Get relationship types
            result = session.run("CALL db.relationshipTypes()")
            schema["relationship_types"] = [record["relationshipType"] for record in result]
            
            # Get property keys for each node label
            for label in schema["node_labels"]:
                result = session.run(f"""
                    MATCH (n:`{label}`)
                    WITH n LIMIT 1
                    RETURN keys(n) as props
                """)
                record = result.single()
                if record:
                    schema["node_properties"][label] = record["props"]
            
        return schema
    
    def get_node_counts(self) -> Dict[str, int]:
        """Get count of nodes for each label."""
        counts = {}
        with self.session() as session:
            if session is None:
                return counts
            
            result = session.run("""
                CALL db.labels() YIELD label
                CALL apoc.cypher.run('MATCH (n:`' + label + '`) RETURN count(n) as count', {}) YIELD value
                RETURN label, value.count as count
            """)
            # Fallback if APOC not available
            try:
                for record in result:
                    counts[record["label"]] = record["count"]
            except:
                # Try without APOC
                labels_result = session.run("CALL db.labels()")
                for record in labels_result:
                    label = record["label"]
                    count_result = session.run(f"MATCH (n:`{label}`) RETURN count(n) as count")
                    count_record = count_result.single()
                    if count_record:
                        counts[label] = count_record["count"]
        
        return counts
    
    def get_sample_nodes(self, label: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Get sample nodes for a given label."""
        nodes = []
        with self.session() as session:
            if session is None:
                return nodes
            
            result = session.run(f"""
                MATCH (n:`{label}`)
                RETURN n LIMIT {limit}
            """)
            for record in result:
                node = record["n"]
                nodes.append(dict(node))
        
        return nodes
    
    # =========================================================================
    # PSUR SECTION QUERIES
    # =========================================================================
    
    def get_section_requirements(self, section_id: str) -> Dict[str, Any]:
        """Get regulatory requirements for a specific PSUR section."""
        with self.session() as session:
            if session is None:
                return {}
            
            # Try different possible node structures
            queries = [
                # If sections are stored as Section nodes
                f"""
                MATCH (s:Section {{id: '{section_id}'}})
                OPTIONAL MATCH (s)-[:REQUIRES]->(r:Requirement)
                OPTIONAL MATCH (s)-[:REFERENCES]->(reg:Regulation)
                OPTIONAL MATCH (s)-[:DEPENDS_ON]->(dep:Section)
                RETURN s, collect(DISTINCT r) as requirements, 
                       collect(DISTINCT reg) as regulations,
                       collect(DISTINCT dep) as dependencies
                """,
                # If sections are stored with section_id property
                f"""
                MATCH (s) WHERE s.section_id = '{section_id}' OR s.sectionId = '{section_id}'
                OPTIONAL MATCH (s)-[r1]->(req) WHERE type(r1) IN ['REQUIRES', 'HAS_REQUIREMENT']
                OPTIONAL MATCH (s)-[r2]->(reg) WHERE type(r2) IN ['REFERENCES', 'CITES']
                RETURN s, collect(DISTINCT req) as requirements, collect(DISTINCT reg) as regulations
                """
            ]
            
            for query in queries:
                try:
                    result = session.run(query)
                    record = result.single()
                    if record and record["s"]:
                        return {
                            "section": dict(record["s"]) if record["s"] else {},
                            "requirements": [dict(r) for r in (record.get("requirements") or []) if r],
                            "regulations": [dict(r) for r in (record.get("regulations") or []) if r],
                            "dependencies": [dict(d) for d in (record.get("dependencies") or []) if d]
                        }
                except Exception:
                    continue
            
            return {}
    
    def get_all_sections(self) -> List[Dict[str, Any]]:
        """Get all PSUR sections from the graph."""
        sections = []
        with self.session() as session:
            if session is None:
                return sections
            
            # Try different query patterns
            queries = [
                "MATCH (s:Section) RETURN s ORDER BY s.id",
                "MATCH (s:PSURSection) RETURN s ORDER BY s.id",
                "MATCH (s) WHERE s.type = 'section' RETURN s ORDER BY s.id"
            ]
            
            for query in queries:
                try:
                    result = session.run(query)
                    for record in result:
                        sections.append(dict(record["s"]))
                    if sections:
                        break
                except Exception:
                    continue
        
        return sections
    
    def get_mdcg_requirements(self) -> List[Dict[str, Any]]:
        """Get MDCG 2022-21 requirements from the graph."""
        requirements = []
        with self.session() as session:
            if session is None:
                return requirements
            
            queries = [
                "MATCH (r:Requirement) WHERE r.source CONTAINS 'MDCG' RETURN r",
                "MATCH (r:MDCGRequirement) RETURN r",
                "MATCH (r) WHERE r.type = 'mdcg_requirement' RETURN r"
            ]
            
            for query in queries:
                try:
                    result = session.run(query)
                    for record in result:
                        requirements.append(dict(record["r"]))
                    if requirements:
                        break
                except Exception:
                    continue
        
        return requirements
    
    def get_severity_definitions(self) -> List[Dict[str, Any]]:
        """Get severity level definitions from the graph."""
        definitions = []
        with self.session() as session:
            if session is None:
                return definitions
            
            queries = [
                "MATCH (s:SeverityLevel) RETURN s ORDER BY s.rank",
                "MATCH (s:Severity) RETURN s",
                "MATCH (s) WHERE s.type = 'severity_level' RETURN s"
            ]
            
            for query in queries:
                try:
                    result = session.run(query)
                    for record in result:
                        definitions.append(dict(record["s"]))
                    if definitions:
                        break
                except Exception:
                    continue
        
        return definitions
    
    def get_root_cause_categories(self) -> List[Dict[str, Any]]:
        """Get root cause categories from the graph."""
        categories = []
        with self.session() as session:
            if session is None:
                return categories
            
            queries = [
                "MATCH (c:RootCauseCategory) RETURN c",
                "MATCH (c:RootCause) RETURN c",
                "MATCH (c) WHERE c.type = 'root_cause' RETURN c"
            ]
            
            for query in queries:
                try:
                    result = session.run(query)
                    for record in result:
                        categories.append(dict(record["c"]))
                    if categories:
                        break
                except Exception:
                    continue
        
        return categories
    
    # =========================================================================
    # REGULATORY CROSS-REFERENCES
    # =========================================================================
    
    def get_mdr_articles(self) -> List[Dict[str, Any]]:
        """Get EU MDR article references from the graph."""
        articles = []
        with self.session() as session:
            if session is None:
                return articles
            
            queries = [
                "MATCH (a:MDRArticle) RETURN a ORDER BY a.number",
                "MATCH (a:Article) WHERE a.regulation = 'MDR' RETURN a",
                "MATCH (a) WHERE a.type = 'mdr_article' RETURN a"
            ]
            
            for query in queries:
                try:
                    result = session.run(query)
                    for record in result:
                        articles.append(dict(record["a"]))
                    if articles:
                        break
                except Exception:
                    continue
        
        return articles
    
    def get_section_mdr_mapping(self, section_id: str) -> List[Dict[str, Any]]:
        """Get MDR articles related to a specific section."""
        mappings = []
        with self.session() as session:
            if session is None:
                return mappings
            
            result = session.run(f"""
                MATCH (s)-[r]->(a)
                WHERE (s.id = '{section_id}' OR s.section_id = '{section_id}')
                  AND (a:MDRArticle OR a:Article OR a.type = 'mdr_article')
                RETURN a, type(r) as relationship
            """)
            
            for record in result:
                mappings.append({
                    "article": dict(record["a"]),
                    "relationship": record["relationship"]
                })
        
        return mappings
    
    # =========================================================================
    # CONTEXT ENRICHMENT FOR AGENTS
    # =========================================================================
    
    def get_agent_context(self, section_id: str) -> Dict[str, Any]:
        """
        Get comprehensive regulatory context for an agent working on a section.
        Returns all relevant regulatory grounding for the section.
        """
        context = {
            "section": {},
            "requirements": [],
            "mdr_references": [],
            "mdcg_references": [],
            "dependencies": [],
            "related_sections": [],
            "definitions": {}
        }
        
        with self.session() as session:
            if session is None:
                return context
            
            # Get section info and all relationships
            result = session.run(f"""
                MATCH (s)
                WHERE s.id = '{section_id}' OR s.section_id = '{section_id}' OR s.sectionId = '{section_id}'
                OPTIONAL MATCH (s)-[r]->(related)
                RETURN s, collect({{type: type(r), node: related}}) as relationships
            """)
            
            record = result.single()
            if record and record["s"]:
                context["section"] = dict(record["s"])
                
                for rel in record["relationships"]:
                    if rel["node"]:
                        node_data = dict(rel["node"])
                        rel_type = rel["type"]
                        
                        if rel_type in ["REQUIRES", "HAS_REQUIREMENT"]:
                            context["requirements"].append(node_data)
                        elif rel_type in ["REFERENCES_MDR", "CITES_MDR"]:
                            context["mdr_references"].append(node_data)
                        elif rel_type in ["REFERENCES_MDCG", "CITES_MDCG"]:
                            context["mdcg_references"].append(node_data)
                        elif rel_type in ["DEPENDS_ON", "FOLLOWS"]:
                            context["dependencies"].append(node_data)
                        elif rel_type in ["RELATED_TO", "CROSS_REFERENCES"]:
                            context["related_sections"].append(node_data)
        
        # Get definitions
        context["definitions"]["severity_levels"] = self.get_severity_definitions()
        context["definitions"]["root_causes"] = self.get_root_cause_categories()
        
        return context
    
    def get_full_regulatory_context(self) -> Dict[str, Any]:
        """
        Get the complete regulatory context for PSUR generation.
        Used during orchestrator initialization to ground all agents.
        """
        return {
            "schema": self.get_schema(),
            "node_counts": self.get_node_counts(),
            "sections": self.get_all_sections(),
            "mdcg_requirements": self.get_mdcg_requirements(),
            "mdr_articles": self.get_mdr_articles(),
            "severity_definitions": self.get_severity_definitions(),
            "root_cause_categories": self.get_root_cause_categories()
        }
    
    # =========================================================================
    # CUSTOM CYPHER QUERIES
    # =========================================================================
    
    def run_query(self, cypher: str, params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Run a custom Cypher query and return results."""
        results = []
        with self.session() as session:
            if session is None:
                return results
            
            result = session.run(cypher, params or {})
            for record in result:
                results.append(dict(record))
        
        return results


# Singleton accessor
def get_neo4j_client() -> Neo4jClient:
    """Get the Neo4j client singleton."""
    return Neo4jClient.get_instance()
