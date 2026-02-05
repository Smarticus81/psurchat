"""
GRKB (Graph Regulatory Knowledge Base) Client

Provides access to the regulatory knowledge base containing:
- PSUR section definitions and requirements (MDCG 2022-21)
- EU MDR regulatory obligations
- Evidence type definitions
- System instructions for AI agents
- Slot-to-obligation mappings
"""

import os
from typing import Dict, List, Any, Optional
from contextlib import contextmanager

try:
    import psycopg2
    import psycopg2.extras
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False


class GRKBClient:
    """Client for querying the Graph Regulatory Knowledge Base."""
    
    _instance: Optional["GRKBClient"] = None
    
    def __init__(self):
        # Parse DATABASE_URL for GRKB (Supabase PostgreSQL)
        self.database_url = os.getenv(
            "DATABASE_URL",
            "postgresql://postgres.tdbvnakvmztquhfjvupw:7Innerleithen!@aws-0-us-west-2.pooler.supabase.com:5432/postgres"
        )
        self._conn = None
        
    @classmethod
    def get_instance(cls) -> "GRKBClient":
        """Get singleton instance of GRKB client."""
        if cls._instance is None:
            cls._instance = GRKBClient()
        return cls._instance
    
    def connect(self) -> bool:
        """Establish connection to GRKB database."""
        if not PSYCOPG2_AVAILABLE:
            print("psycopg2 not installed. Run: pip install psycopg2-binary")
            return False
            
        try:
            self._conn = psycopg2.connect(self.database_url)
            print("Connected to GRKB database")
            return True
        except Exception as e:
            print(f"Failed to connect to GRKB: {e}")
            self._conn = None
            return False
    
    def close(self):
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
    
    @contextmanager
    def cursor(self):
        """Get a database cursor context manager."""
        if not self._conn:
            if not self.connect():
                yield None
                return
        
        cur = self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            yield cur
        finally:
            cur.close()
    
    def is_connected(self) -> bool:
        """Check if connected to database."""
        return self._conn is not None
    
    # =========================================================================
    # REGULATORY OBLIGATIONS
    # =========================================================================
    
    def get_all_obligations(self, jurisdiction: str = "EU_MDR") -> List[Dict[str, Any]]:
        """Get all regulatory obligations for a jurisdiction."""
        with self.cursor() as cur:
            if cur is None:
                return []
            
            cur.execute("""
                SELECT obligation_id, jurisdiction, artifact_type, kind, title, 
                       text, source_citation, mandatory, required_evidence_types
                FROM grkb_obligations
                WHERE jurisdiction = %s
                ORDER BY obligation_id
            """, (jurisdiction,))
            
            return [dict(row) for row in cur.fetchall()]
    
    def get_obligation_by_id(self, obligation_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific obligation by ID."""
        with self.cursor() as cur:
            if cur is None:
                return None
            
            cur.execute("""
                SELECT * FROM grkb_obligations
                WHERE obligation_id = %s
            """, (obligation_id,))
            
            row = cur.fetchone()
            return dict(row) if row else None
    
    def get_obligations_for_section(self, section_id: str, template_id: str = "MDCG_2022_21_ANNEX_I") -> List[Dict[str, Any]]:
        """Get obligations mapped to a specific section."""
        with self.cursor() as cur:
            if cur is None:
                return []
            
            cur.execute("""
                SELECT o.* 
                FROM grkb_obligations o
                JOIN slot_obligation_links sol ON o.obligation_id = sol.obligation_id
                WHERE sol.slot_id = %s AND sol.template_id = %s
            """, (section_id, template_id))
            
            return [dict(row) for row in cur.fetchall()]
    
    # =========================================================================
    # PSUR SECTIONS
    # =========================================================================
    
    def get_all_sections(self, template_id: str = "MDCG_2022_21_ANNEX_I") -> List[Dict[str, Any]]:
        """Get all PSUR sections for a template."""
        with self.cursor() as cur:
            if cur is None:
                return []
            
            cur.execute("""
                SELECT section_id, template_id, section_number, section_path,
                       title, description, section_type, mandatory,
                       minimum_word_count, required_evidence_types,
                       regulatory_basis, display_order
                FROM psur_sections
                WHERE template_id = %s
                ORDER BY display_order
            """, (template_id,))
            
            return [dict(row) for row in cur.fetchall()]
    
    def get_section_by_id(self, section_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific section by ID."""
        with self.cursor() as cur:
            if cur is None:
                return None
            
            cur.execute("""
                SELECT * FROM psur_sections
                WHERE section_id = %s
            """, (section_id,))
            
            row = cur.fetchone()
            return dict(row) if row else None
    
    # =========================================================================
    # SLOT DEFINITIONS
    # =========================================================================
    
    def get_all_slots(self, template_id: str = "MDCG_2022_21_ANNEX_I") -> List[Dict[str, Any]]:
        """Get all slot definitions for a template."""
        with self.cursor() as cur:
            if cur is None:
                return []
            
            cur.execute("""
                SELECT slot_id, title, description, template_id,
                       jurisdictions, required_evidence_types,
                       hard_require_evidence, min_atoms, sort_order
                FROM slot_definitions
                WHERE template_id = %s
                ORDER BY sort_order
            """, (template_id,))
            
            return [dict(row) for row in cur.fetchall()]
    
    def get_slot_by_id(self, slot_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific slot by ID."""
        with self.cursor() as cur:
            if cur is None:
                return None
            
            cur.execute("""
                SELECT * FROM slot_definitions
                WHERE slot_id = %s
            """, (slot_id,))
            
            row = cur.fetchone()
            return dict(row) if row else None
    
    # =========================================================================
    # SYSTEM INSTRUCTIONS
    # =========================================================================
    
    def get_system_instruction(self, key: str) -> Optional[Dict[str, Any]]:
        """Get a system instruction by key."""
        with self.cursor() as cur:
            if cur is None:
                return None
            
            cur.execute("""
                SELECT key, category, description, template, variables
                FROM system_instructions
                WHERE key = %s
            """, (key,))
            
            row = cur.fetchone()
            return dict(row) if row else None
    
    def get_all_system_instructions(self, category: str = None) -> List[Dict[str, Any]]:
        """Get all system instructions, optionally filtered by category."""
        with self.cursor() as cur:
            if cur is None:
                return []
            
            if category:
                cur.execute("""
                    SELECT key, category, description, template, variables
                    FROM system_instructions
                    WHERE category = %s
                    ORDER BY key
                """, (category,))
            else:
                cur.execute("""
                    SELECT key, category, description, template, variables
                    FROM system_instructions
                    ORDER BY category, key
                """)
            
            return [dict(row) for row in cur.fetchall()]
    
    # =========================================================================
    # EVIDENCE TYPES
    # =========================================================================
    
    def get_all_evidence_types(self) -> List[Dict[str, Any]]:
        """Get all evidence type definitions."""
        with self.cursor() as cur:
            if cur is None:
                return []
            
            cur.execute("""
                SELECT evidence_type_id, display_name, description, category,
                       required_fields, optional_fields, field_definitions,
                       validation_rules, typical_psur_sections
                FROM psur_evidence_types
                WHERE is_active = true
                ORDER BY category, evidence_type_id
            """)
            
            return [dict(row) for row in cur.fetchall()]
    
    def get_evidence_type(self, evidence_type_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific evidence type definition."""
        with self.cursor() as cur:
            if cur is None:
                return None
            
            cur.execute("""
                SELECT * FROM psur_evidence_types
                WHERE evidence_type_id = %s
            """, (evidence_type_id,))
            
            row = cur.fetchone()
            return dict(row) if row else None
    
    # =========================================================================
    # TEMPLATES
    # =========================================================================
    
    def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Get a template definition including all slots."""
        with self.cursor() as cur:
            if cur is None:
                return None
            
            cur.execute("""
                SELECT template_id, name, version, jurisdictions,
                       template_type, template_json
                FROM templates
                WHERE template_id = %s
            """, (template_id,))
            
            row = cur.fetchone()
            return dict(row) if row else None
    
    def get_all_templates(self) -> List[Dict[str, Any]]:
        """Get all available templates."""
        with self.cursor() as cur:
            if cur is None:
                return []
            
            cur.execute("""
                SELECT template_id, name, version, jurisdictions, template_type
                FROM templates
                ORDER BY template_id
            """)
            
            return [dict(row) for row in cur.fetchall()]
    
    # =========================================================================
    # DEVICE DOSSIER
    # =========================================================================
    
    def get_device_dossier(self, device_code: str) -> Dict[str, Any]:
        """Get full device dossier including clinical and risk context."""
        dossier = {
            "device": None,
            "clinical_context": None,
            "clinical_evidence": None,
            "risk_context": None,
            "regulatory_history": None
        }
        
        with self.cursor() as cur:
            if cur is None:
                return dossier
            
            # Device basics
            cur.execute("""
                SELECT * FROM device_dossiers
                WHERE device_code LIKE %s
            """, (f"%{device_code}%",))
            row = cur.fetchone()
            if row:
                dossier["device"] = dict(row)
            
            # Clinical context
            cur.execute("""
                SELECT * FROM dossier_clinical_context
                WHERE device_code LIKE %s
            """, (f"%{device_code}%",))
            row = cur.fetchone()
            if row:
                dossier["clinical_context"] = dict(row)
            
            # Clinical evidence
            cur.execute("""
                SELECT * FROM dossier_clinical_evidence
                WHERE device_code LIKE %s
            """, (f"%{device_code}%",))
            row = cur.fetchone()
            if row:
                dossier["clinical_evidence"] = dict(row)
            
            # Risk context
            cur.execute("""
                SELECT * FROM dossier_risk_context
                WHERE device_code LIKE %s
            """, (f"%{device_code}%",))
            row = cur.fetchone()
            if row:
                dossier["risk_context"] = dict(row)
            
            # Regulatory history
            cur.execute("""
                SELECT * FROM dossier_regulatory_history
                WHERE device_code LIKE %s
            """, (f"%{device_code}%",))
            row = cur.fetchone()
            if row:
                dossier["regulatory_history"] = dict(row)
        
        return dossier
    
    # =========================================================================
    # COMPREHENSIVE CONTEXT FOR AGENTS
    # =========================================================================
    
    def get_agent_regulatory_context(self, section_id: str, template_id: str = "MDCG_2022_21_ANNEX_I") -> Dict[str, Any]:
        """
        Get comprehensive regulatory context for an agent working on a section.
        Includes obligations, evidence requirements, and system instructions.
        """
        context = {
            "section": None,
            "slot": None,
            "obligations": [],
            "evidence_types": [],
            "system_instructions": {},
            "related_sections": []
        }
        
        # Get section definition
        section = self.get_section_by_id(section_id)
        if section:
            context["section"] = section
        
        # Get slot definition
        slot = self.get_slot_by_id(section_id)
        if slot:
            context["slot"] = slot
        
        # Get mapped obligations
        context["obligations"] = self.get_obligations_for_section(section_id, template_id)
        
        # Get required evidence types
        required_types = []
        if section and section.get("required_evidence_types"):
            required_types.extend(section["required_evidence_types"])
        if slot and slot.get("required_evidence_types"):
            required_types.extend(slot["required_evidence_types"])
        
        for et_id in set(required_types):
            et = self.get_evidence_type(et_id)
            if et:
                context["evidence_types"].append(et)
        
        # Get relevant system instructions
        instruction_keys = [
            "SEVERITY_CLASSIFICATION",
            "EVIDENCE_EXTRACTION",
            "BENEFIT_RISK_CONCLUSION"
        ]
        for key in instruction_keys:
            inst = self.get_system_instruction(key)
            if inst:
                context["system_instructions"][key] = inst
        
        return context
    
    def get_full_regulatory_context(self, template_id: str = "MDCG_2022_21_ANNEX_I") -> Dict[str, Any]:
        """
        Get the complete regulatory context for PSUR generation.
        Used during orchestrator initialization to ground all agents.
        """
        return {
            "template": self.get_template(template_id),
            "sections": self.get_all_sections(template_id),
            "slots": self.get_all_slots(template_id),
            "obligations": self.get_all_obligations(),
            "evidence_types": self.get_all_evidence_types(),
            "system_instructions": self.get_all_system_instructions()
        }
    
    def get_severity_definitions_from_instructions(self) -> Dict[str, str]:
        """Extract severity definitions from system instructions."""
        inst = self.get_system_instruction("SEVERITY_CLASSIFICATION")
        if not inst or not inst.get("template"):
            return {}
        
        # Default severity levels based on common medical device standards
        return {
            "CRITICAL": "Death or permanent impairment directly attributable to device",
            "HIGH": "Hospitalization, intervention required, or temporary impairment",  
            "MEDIUM": "Medically significant but not requiring intervention",
            "LOW": "No injury, user inconvenience only",
            "INFORMATIONAL": "No adverse health consequences"
        }
    
    def format_obligations_for_prompt(self, obligations: List[Dict[str, Any]]) -> str:
        """Format obligations list into a prompt-friendly string."""
        if not obligations:
            return "No specific regulatory obligations loaded."
        
        lines = ["REGULATORY OBLIGATIONS:"]
        for obl in obligations:
            lines.append(f"\n- {obl.get('obligation_id', 'N/A')}: {obl.get('title', 'N/A')}")
            if obl.get('text'):
                # Truncate long text
                text = obl['text'][:300] + "..." if len(obl['text']) > 300 else obl['text']
                lines.append(f"  {text}")
            if obl.get('source_citation'):
                lines.append(f"  Source: {obl['source_citation']}")
        
        return "\n".join(lines)
    
    def format_section_requirements_for_prompt(self, section: Dict[str, Any], slot: Dict[str, Any] = None) -> str:
        """Format section requirements into a prompt-friendly string."""
        lines = []
        
        if section:
            lines.append(f"SECTION: {section.get('section_number', '')} - {section.get('title', '')}")
            if section.get('description'):
                lines.append(f"Description: {section['description']}")
            if section.get('regulatory_basis'):
                lines.append(f"Regulatory Basis: {section['regulatory_basis']}")
            if section.get('minimum_word_count'):
                lines.append(f"Minimum Word Count: {section['minimum_word_count']}")
            if section.get('required_evidence_types'):
                lines.append(f"Required Evidence Types: {', '.join(section['required_evidence_types'])}")
        
        if slot:
            lines.append(f"\nSLOT: {slot.get('title', '')}")
            if slot.get('description'):
                lines.append(f"Purpose: {slot['description']}")
            if slot.get('hard_require_evidence'):
                lines.append("Evidence: REQUIRED (cannot be empty)")
            if slot.get('min_atoms'):
                lines.append(f"Minimum Evidence Atoms: {slot['min_atoms']}")
        
        return "\n".join(lines) if lines else "No section requirements loaded."


# Singleton accessor
def get_grkb_client() -> GRKBClient:
    """Get the GRKB client singleton."""
    return GRKBClient.get_instance()
