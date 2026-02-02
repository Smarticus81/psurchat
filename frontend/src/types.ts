// Agent configuration and types
export interface Agent {
    id: string;
    name: string;
    role: string;
    ai_provider: string;
    model: string;
    status?: 'idle' | 'working' | 'waiting' | 'complete';
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
    status: 'pending' | 'in_progress' | 'in_review' | 'approved' | 'rejected';
    author?: string;
    progress?: number;
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

// Agent color mapping for UI
export const AGENT_COLORS: Record<string, string> = {
    Alex: '#6366f1',      // Indigo - Orchestrator
    Diana: '#3b82f6',     // Blue
    Sam: '#06b6d4',       // Cyan
    Raj: '#10b981',       // Emerald
    Vera: '#8b5cf6',      // Purple
    Carla: '#ec4899',     // Pink
    Tara: '#f59e0b',      // Amber
    Frank: '#ef4444',     // Red
    Cameron: '#14b8a6',   // Teal
    Rita: '#a855f7',      // Purple
    Brianna: '#f97316',   // Orange
    Eddie: '#84cc16',     // Lime
    Clara: '#22c55e',     // Green
    Marcus: '#6366f1',    // Indigo
    Statler: '#0ea5e9',   // Sky
    Charley: '#8b5cf6',   // Violet
    Quincy: '#06b6d4',    // Cyan
    Victoria: '#ec4899',  // Pink
};

// Section definitions
export const SECTIONS: Array<{ id: string; name: string }> = [
    { id: 'A', name: 'Device Identification' },
    { id: 'B', name: 'Scope & Documentation' },
    { id: 'C', name: 'Sales Volume' },
    { id: 'D', name: 'Vigilance - Serious Incidents' },
    { id: 'E&F', name: 'Customer Feedback & Complaints' },
    { id: 'G', name: 'Trending Analysis' },
    { id: 'H', name: 'FSCA & Risk Management' },
    { id: 'I', name: 'CAPA Implementation' },
    { id: 'J', name: 'Benefit-Risk Assessment' },
    { id: 'K', name: 'External Database Review' },
    { id: 'L', name: 'PMCF Activities' },
    { id: 'M', name: 'Conclusions & Recommendations' },
];
