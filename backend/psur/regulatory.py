"""
RegulatoryKnowledgeService - Unified access to GRKB (PostgreSQL).

Loads regulatory obligations, section definitions, evidence types,
system instructions, and device dossier data. Populates PSURContext
GRKB fields for injection into agent prompts.
"""

from typing import Optional
from backend.psur.context import PSURContext


# Lazy import -- grkb_client may not be installed
GRKB_AVAILABLE = False
_GRKBClient = None

try:
    from backend.database.grkb_client import GRKBClient as _GRKBClientCls
    _GRKBClient = _GRKBClientCls
    GRKB_AVAILABLE = True
except ImportError:
    pass


class RegulatoryKnowledgeService:
    """Singleton service for regulatory knowledge base access."""

    _instance: Optional["RegulatoryKnowledgeService"] = None

    def __init__(self):
        self._client = None
        self._connected = False

    @classmethod
    def get_instance(cls) -> "RegulatoryKnowledgeService":
        if cls._instance is None:
            cls._instance = RegulatoryKnowledgeService()
        return cls._instance

    def connect(self) -> bool:
        """Attempt to connect to the GRKB database."""
        if not GRKB_AVAILABLE or _GRKBClient is None:
            return False
        try:
            self._client = _GRKBClient.get_instance()
            self._connected = self._client.connect()
            return self._connected
        except Exception as e:
            print(f"[regulatory] Connection failed: {e}")
            return False

    @property
    def available(self) -> bool:
        return self._connected and self._client is not None

    def load_into_context(self, ctx: PSURContext) -> bool:
        """
        Load all regulatory data from GRKB into a PSURContext instance.
        Returns True if data was loaded successfully.
        """
        if not self.available or self._client is None:
            return False

        try:
            grkb = self._client
            template_id = "MDCG_2022_21_ANNEX_I"

            # Load template
            template = grkb.get_template(template_id)
            if template:
                ctx.grkb_template = template

            # Load sections
            sections = grkb.get_all_sections(template_id)
            if sections:
                ctx.grkb_sections = sections

            # Load obligations
            obligations = grkb.get_all_obligations("EU_MDR")
            if obligations:
                ctx.grkb_obligations = obligations

            # Load evidence types
            evidence_types = grkb.get_all_evidence_types()
            if evidence_types:
                ctx.grkb_evidence_types = evidence_types

            # Load system instructions
            instructions = grkb.get_all_system_instructions()
            if instructions:
                ctx.grkb_system_instructions = {
                    inst["key"]: inst for inst in instructions
                }

            # Device-specific dossier
            if ctx.device_name:
                dossier = grkb.get_device_dossier(ctx.device_name)
                if dossier.get("clinical_context"):
                    cc = dossier["clinical_context"]
                    if cc.get("intended_purpose") and not ctx.intended_use:
                        ctx.intended_use = cc["intended_purpose"]
                    if cc.get("indications"):
                        ctx.data_quality_warnings.append(
                            f"Indications from GRKB: {', '.join(cc['indications'][:5])}"
                        )
                    if cc.get("contraindications"):
                        ctx.data_quality_warnings.append(
                            f"Contraindications from GRKB: {', '.join(cc['contraindications'][:5])}"
                        )

                if dossier.get("risk_context"):
                    rc = dossier["risk_context"]
                    if rc.get("principal_risks"):
                        ctx.known_residual_risks = [
                            f"{r.get('hazard', 'Unknown')}: {r.get('harm', 'Unknown')}"
                            for r in rc["principal_risks"]
                        ]
                    if rc.get("risk_thresholds", {}).get("complaintRateThreshold"):
                        ctx.data_quality_warnings.append(
                            f"Complaint rate threshold from RMF: {rc['risk_thresholds']['complaintRateThreshold']}%"
                        )

            ctx.grkb_available = True
            return True

        except Exception as e:
            print(f"[regulatory] Error loading GRKB: {e}")
            return False
