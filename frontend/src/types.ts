// Agent configuration and types - SOTA PSUR System
export interface Agent {
    id: string;
    name: string;
    role: string;
    title?: string;
    expertise?: string;
    primary_section?: string;
    ai_provider: string;
    model: string;
    status?: 'idle' | 'working' | 'waiting' | 'complete' | 'error';
    color?: string;
}

export interface ChatMessage {
    id: number;
    from_agent: string;
    to_agent: string;
    message: string;
    message_type: 'normal' | 'system' | 'error' | 'warning' | 'success';
    timestamp: string;
    metadata?: any;
}

export interface SectionStatus {
    section_id: string;
    section_name: string;
    status: 'pending' | 'in_progress' | 'draft' | 'in_review' | 'approved' | 'rejected';
    author?: string;
    progress?: number;
    mdcg_ref?: string;
}

export interface PSURSession {
    id: number;
    session_id: string;
    device_name: string;
    status: string;
    current_section?: string;
    sections_completed: number;
    total_sections: number;
    created_at: string;
}

// SOTA Agent color mapping - Aligned with MDCG 2022-21 agent roles
export const AGENT_COLORS: Record<string, string> = {
    // Orchestrator
    Alex: '#6366f1',      // Indigo - Workflow Coordinator

    // Section Agents (SOTA spec)
    Marcus: '#6366f1',    // Indigo - Executive Summary (Section A)
    Greta: '#3b82f6',     // Blue - Sales & Market Data (Sections B, C)
    David: '#ef4444',     // Red - Vigilance Specialist (Section D)
    Emma: '#ec4899',      // Pink - Complaint Classifier (Sections E, F)
    Diana: '#8b5cf6',     // Purple - Trend Detective (Section G)
    Lisa: '#f59e0b',      // Amber - FSCA Coordinator (Section H)
    Tom: '#10b981',       // Emerald - CAPA Verifier (Section I)
    James: '#06b6d4',     // Cyan - Literature Reviewer (Sections J, K)
    Sarah: '#a855f7',     // Purple - PMCF Specialist (Section L)
    Robert: '#22c55e',    // Green - Risk Specialist (Section M)

    // QC Agent
    Victoria: '#f97316',  // Orange - QC Expert
};

// SOTA Section definitions - FormQAR-054 and MDCG 2022-21 aligned
export const SECTIONS: Array<{ id: string; name: string; agent: string; mdcg_ref: string; number: number }> = [
    { id: 'A', name: 'Executive Summary', agent: 'Marcus', mdcg_ref: '1.1', number: 1 },
    { id: 'B', name: 'Scope and Device Description', agent: 'Greta', mdcg_ref: '1.2', number: 2 },
    { id: 'C', name: 'Post-Market Data: Units Distributed', agent: 'Greta', mdcg_ref: '2.1', number: 3 },
    { id: 'D', name: 'Serious Incidents and Trends', agent: 'David', mdcg_ref: '2.2', number: 4 },
    { id: 'E', name: 'Post-Market Surveillance: Customer Feedback', agent: 'Emma', mdcg_ref: '2.3', number: 5 },
    { id: 'F', name: 'Complaints Management', agent: 'Emma', mdcg_ref: '2.4', number: 6 },
    { id: 'G', name: 'Trends and Performance Analysis', agent: 'Diana', mdcg_ref: '3', number: 7 },
    { id: 'H', name: 'Field Safety Corrective Actions (FSCA)', agent: 'Lisa', mdcg_ref: '2.5', number: 8 },
    { id: 'I', name: 'Corrective and Preventive Actions (CAPA)', agent: 'Tom', mdcg_ref: '1.4', number: 9 },
    { id: 'J', name: 'Literature Review and External Data', agent: 'James', mdcg_ref: '1.3', number: 10 },
    { id: 'K', name: 'External Adverse Event Databases', agent: 'James', mdcg_ref: '2.6', number: 11 },
    { id: 'L', name: 'Post-Market Clinical Follow-up (PMCF)', agent: 'Sarah', mdcg_ref: '1.5', number: 12 },
    { id: 'M', name: 'Overall Findings and Conclusions', agent: 'Robert', mdcg_ref: '1.6', number: 13 },
];

// Workflow order (dependency-based per SOTA spec)
export const WORKFLOW_ORDER = [
    'C',   // Phase 1: DATA FOUNDATION - Sales/Exposure (Greta)
    'D',   // Phase 2: ADVERSE EVENT ANALYSIS - Serious Incidents (David)
    'E',   // Phase 2: Customer Feedback (Emma)
    'F',   // Phase 2: Complaints Management (Emma)
    'G',   // Phase 3: ANALYTICAL - Trends & Analysis (Diana)
    'H',   // Phase 3: FSCA (Lisa)
    'I',   // Phase 3: CAPA (Tom)
    'J',   // Phase 4: EXTERNAL CONTEXT - Literature Review (James)
    'K',   // Phase 4: External Databases (James)
    'L',   // Phase 5: CLINICAL EVIDENCE - PMCF (Sarah)
    'B',   // Phase 6: CHARACTERIZATION - Scope & Description (Greta)
    'M',   // Phase 7: SYNTHESIS - Findings & Conclusions (Robert)
    'A',   // Phase 7: Executive Summary (Marcus)
];

// Agent role descriptions for tooltips and info displays
export const AGENT_ROLES: Record<string, { role: string; title: string; expertise: string; section?: string }> = {
    Alex: {
        role: 'Orchestrator',
        title: 'PSUR Workflow Coordinator',
        expertise: 'Workflow coordination, task delegation, quality oversight',
    },
    Marcus: {
        role: 'Executive Summary Specialist',
        title: 'Executive Summary Writer',
        expertise: 'Synthesizing findings, executive communication, regulatory conclusions',
        section: 'A',
    },
    Greta: {
        role: 'Sales & Market Data Analyst',
        title: 'Market Data Specialist',
        expertise: 'Sales analysis, market exposure calculations, distribution tracking',
        section: 'C',
    },
    David: {
        role: 'Vigilance Specialist',
        title: 'Serious Incidents Analyst',
        expertise: 'Adverse event classification, vigilance database analysis, causality assessment',
        section: 'D',
    },
    Emma: {
        role: 'Complaint Classifier',
        title: 'Customer Feedback Analyst',
        expertise: 'Complaint categorization, root cause analysis, investigation management',
        section: 'E',
    },
    Diana: {
        role: 'Trend Detective',
        title: 'Statistical Trend Analyst',
        expertise: 'Statistical process control, UCL/LCL analysis, signal detection',
        section: 'G',
    },
    Lisa: {
        role: 'FSCA Coordinator',
        title: 'Field Safety Actions Specialist',
        expertise: 'Field corrective actions, implementation tracking, effectiveness verification',
        section: 'H',
    },
    Tom: {
        role: 'CAPA Verifier',
        title: 'Quality Improvement Specialist',
        expertise: 'Corrective/preventive actions, root cause verification, effectiveness evidence',
        section: 'I',
    },
    James: {
        role: 'Literature Reviewer',
        title: 'External Data Specialist',
        expertise: 'Scientific literature review, external database search, competitor surveillance',
        section: 'J',
    },
    Sarah: {
        role: 'PMCF Specialist',
        title: 'Clinical Follow-up Analyst',
        expertise: 'Post-market clinical studies, performance evidence, safety monitoring',
        section: 'L',
    },
    Robert: {
        role: 'Risk Specialist',
        title: 'Benefit-Risk Assessment Expert',
        expertise: 'Risk management, benefit-risk determination, regulatory recommendations',
        section: 'M',
    },
    Victoria: {
        role: 'QC Expert',
        title: 'Quality Control Validator',
        expertise: 'Template compliance, regulatory validation, audit readiness review',
    },
};
