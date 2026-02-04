import React, { useEffect, useRef, useState, useMemo } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import { api, ChatMessage, SectionDoc, Agent } from '../api';
import { Activity, CheckCircle, Clock, X } from 'lucide-react';

interface AgentGraphProps {
    sessionId: number;
}

// SOTA Mapping: Sections to Agents (FormQAR-054 and MDCG 2022-21 aligned)
const AGENT_MAP: Record<string, string> = {
    'A': 'Marcus',    // Executive Summary
    'B': 'Greta',     // Scope and Device Description
    'C': 'Greta',     // Post-Market Data: Units Distributed
    'D': 'David',     // Serious Incidents and Trends
    'E': 'Emma',      // Post-Market Surveillance: Customer Feedback
    'F': 'Emma',      // Complaints Management
    'G': 'Diana',     // Trends and Performance Analysis
    'H': 'Lisa',      // Field Safety Corrective Actions (FSCA)
    'I': 'Tom',       // Corrective and Preventive Actions (CAPA)
    'J': 'James',     // Literature Review and External Data
    'K': 'James',     // External Adverse Event Databases
    'L': 'Sarah',     // Post-Market Clinical Follow-up (PMCF)
    'M': 'Robert'     // Overall Findings and Conclusions
};

// SOTA Agent Roles (MDCG 2022-21 aligned)
const AGENT_ROLES: Record<string, string> = {
    'Alex': 'Orchestrator',
    'Marcus': 'Executive Summary',
    'Greta': 'Sales & Market Data',
    'David': 'Vigilance Specialist',
    'Emma': 'Complaint Classifier',
    'Diana': 'Trend Detective',
    'Lisa': 'FSCA Coordinator',
    'Tom': 'CAPA Verifier',
    'James': 'Literature Reviewer',
    'Sarah': 'PMCF Specialist',
    'Robert': 'Risk Specialist',
    'Victoria': 'QC Expert',
    'Data Core': 'System Data'
};

export const AgentGraph: React.FC<AgentGraphProps> = ({ sessionId }) => {
    const fgRef = useRef<any>();
    const [dimensions, setDimensions] = useState({ w: 400, h: 400 });
    const containerRef = useRef<HTMLDivElement>(null);
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [sections, setSections] = useState<SectionDoc[]>([]);
    const [agents, setAgents] = useState<Agent[]>([]);

    // UI State
    const [activeNodes, setActiveNodes] = useState<Set<string>>(new Set());
    const [selectedAgent, setSelectedAgent] = useState<string | null>(null);
    const [agentStatus, setAgentStatus] = useState<Record<string, string>>({});

    // Neo4j-inspired Palette
    const COLORS = {
        ORCHESTRATOR: '#57C7E3',
        SYSTEM: '#8DCC93',
        WRITER: '#F79767',
        QC: '#F16667',
        SYNTHESIS: '#FFE081',
        BG: '#0B0D11',
    };

    // Resize handler
    useEffect(() => {
        const updateDimensions = () => {
            if (containerRef.current) {
                setDimensions({
                    w: containerRef.current.clientWidth,
                    h: containerRef.current.clientHeight
                });
            }
        };
        window.addEventListener('resize', updateDimensions);
        setTimeout(updateDimensions, 500);
        return () => window.removeEventListener('resize', updateDimensions);
    }, []);

    // Data Polling
    useEffect(() => {
        // Clear state immediately on session change
        setMessages([]);
        setSections([]);
        setAgents([]);

        const fetchData = async () => {
            try {
                const [msgs, secs, agts] = await Promise.all([
                    api.getMessages(sessionId),
                    api.getSections(sessionId),
                    api.getAgents(sessionId)
                ]);
                setMessages(msgs);
                setSections(secs);
                setAgents(agts);
            } catch (e) {
                console.error(e);
            }
        };

        const interval = setInterval(fetchData, 2000); // 2s polling
        fetchData();
        return () => clearInterval(interval);
    }, [sessionId]);

    // Compute Agent Status from Sections
    useEffect(() => {
        const statusMap: Record<string, string> = {};
        const active = new Set<string>();

        // Default everyone to idle
        Object.keys(AGENT_ROLES).forEach(a => statusMap[a] = 'idle');

        // Check Sections
        sections.forEach(s => {
            const agent = AGENT_MAP[s.section_id];
            if (!agent) return;

            if (s.status === 'in_progress') {
                statusMap[agent] = 'working';
                statusMap['Alex'] = 'coordinating'; // Alex is always busy if someone is working
                active.add(agent);
                active.add('Alex');
            } else if (s.status === 'review') {
                statusMap[agent] = 'waiting';
                statusMap['Victoria'] = 'reviewing';
                active.add('Victoria');
                active.add(agent);
            } else if (s.status === 'complete') {
                statusMap[agent] = 'done';
            }
        });

        // Chat Activity Overlay (Flash)
        const recentTime = Date.now() - 5000;
        messages.forEach(m => {
            if (new Date(m.timestamp).getTime() > recentTime) {
                let from = m.from_agent;
                if (from === 'System') from = 'Data Core';
                active.add(from);
                if (m.to_agent && m.to_agent !== 'all') active.add(m.to_agent);
            }
        });

        setAgentStatus(statusMap);
        setActiveNodes(active);
    }, [sections, messages]);

    // Graph Data
    const graphData = useMemo(() => {
        const nodes = Object.keys(AGENT_ROLES).map(id => {
            let group = 3; // Writers
            let color = COLORS.WRITER;

            if (id === 'Alex') { group = 1; color = COLORS.ORCHESTRATOR; }
            else if (id === 'Victoria') { group = 2; color = COLORS.QC; }
            else if (id === 'Data Core') { group = 0; color = COLORS.SYSTEM; }
            else if (id === 'Marcus') { color = COLORS.SYNTHESIS; }

            // Value based on status
            let val = 15;
            if (id === 'Alex') val = 30;
            if (id === 'Data Core') val = 20;

            return { id, group, val, label: id, color, role: AGENT_ROLES[id] };
        });

        const links: any[] = [];
        nodes.forEach(n => {
            if (n.id !== 'Alex') links.push({ source: 'Alex', target: n.id });
        });

        // Data Core links
        nodes.filter(n => n.group === 3).forEach(n => {
            links.push({ source: 'Data Core', target: n.id });
        });

        // QC links
        nodes.filter(n => n.group === 3).forEach(n => {
            links.push({ source: 'Victoria', target: n.id });
        });

        return { nodes, links };
    }, []);

    // Filter messages for selected agent
    const agentMessages = useMemo(() => {
        if (!selectedAgent) return [];
        return messages.filter(m =>
            m.from_agent === selectedAgent ||
            m.to_agent === selectedAgent ||
            (selectedAgent === 'Data Core' && m.from_agent === 'System')
        ).slice().reverse().slice(0, 50); // Last 50 relevant
    }, [selectedAgent, messages]);

    // Find agent details
    const selectedAgentDetail = agents.find(a => a.name === selectedAgent);

    return (
        <div ref={containerRef} className="agent-graph-container" style={{ width: '100%', height: '100%', background: COLORS.BG, position: 'relative' }}>

            {/* Header / Legend */}
            <div style={{ position: 'absolute', top: 15, left: 15, zIndex: 10, pointerEvents: 'none' }}>
                <h3 style={{ margin: 0, color: '#E2E8F0', fontSize: '0.9rem', fontWeight: 700, letterSpacing: '0.5px' }}>
                    <Activity size={14} style={{ display: 'inline', marginRight: 6 }} />
                    NEURAL ACTIVITY
                </h3>
            </div>

            <ForceGraph2D
                ref={fgRef}
                width={dimensions.w}
                height={dimensions.h}
                graphData={graphData}
                backgroundColor={COLORS.BG}
                nodeRelSize={6}

                // Physics
                d3VelocityDecay={0.3}
                cooldownTicks={100}

                // Interaction
                onNodeClick={(node) => {
                    setSelectedAgent(node.id === selectedAgent ? null : node.id as string);
                    fgRef.current.centerAt(node.x, node.y, 400);
                    fgRef.current.zoom(2.5, 400);
                }}

                // Links
                linkWidth={() => 0.5}
                linkColor={() => '#333333'}
                linkDirectionalParticles={2}
                linkDirectionalParticleSpeed={d => activeNodes.has((d.source as any).id) || activeNodes.has((d.target as any).id) ? 0.005 : 0}
                linkDirectionalParticleWidth={2}
                linkDirectionalParticleColor={() => '#555'}

                // Nodes
                nodeCanvasObject={(node: any, ctx, globalScale) => {
                    const isActive = activeNodes.has(node.id);
                    const status = agentStatus[node.id];
                    const isSelected = selectedAgent === node.id;
                    const r = node.val ? Math.sqrt(node.val) * 1.5 : 5;

                    // Selection Halo
                    if (isSelected) {
                        ctx.beginPath();
                        ctx.arc(node.x, node.y, r + 8, 0, 2 * Math.PI, false);
                        ctx.strokeStyle = '#FFFFFF';
                        ctx.lineWidth = 1;
                        ctx.stroke();
                    }

                    // Active Glow
                    if (isActive || status === 'working') {
                        const time = Date.now();
                        const pulse = Math.sin(time / 200) * 3 + 3; // Pulsing effect
                        ctx.beginPath();
                        ctx.arc(node.x, node.y, r + pulse, 0, 2 * Math.PI, false);
                        ctx.fillStyle = `rgba(${node.color === COLORS.ORCHESTRATOR ? '87, 199, 227' : '247, 151, 103'}, 0.2)`;
                        ctx.fill();
                    }

                    // Main Circle
                    ctx.beginPath();
                    ctx.arc(node.x, node.y, r, 0, 2 * Math.PI, false);
                    ctx.fillStyle = node.color;
                    ctx.fill();

                    // Status Badge (Dot)
                    if (status === 'done') {
                        ctx.beginPath();
                        ctx.arc(node.x + r - 2, node.y - r + 2, 3, 0, 2 * Math.PI, false);
                        ctx.fillStyle = '#10B981'; // Green check
                        ctx.fill();
                    } else if (status === 'working') {
                        ctx.beginPath();
                        ctx.arc(node.x + r - 2, node.y - r + 2, 3, 0, 2 * Math.PI, false);
                        ctx.fillStyle = '#FFFFFF'; // White working dot
                        ctx.fill();
                    }

                    // Label
                    const fontSize = 12 / globalScale;
                    if (globalScale > 1.2 || isSelected || isActive) {
                        ctx.font = `600 ${fontSize}px Inter, sans-serif`;
                        ctx.textAlign = 'center';
                        ctx.textBaseline = 'middle';
                        ctx.fillStyle = isSelected ? '#FFFFFF' : '#94A3B8';
                        ctx.fillText(node.label, node.x, node.y + r + fontSize + 2);
                    }
                }}
            />

            {/* Agent Detail Overlay - Slide in from right */}
            {selectedAgent && (
                <div style={{
                    position: 'absolute',
                    top: 0,
                    right: 0,
                    width: '280px',
                    height: '100%',
                    background: 'rgba(21, 21, 21, 0.95)',
                    borderLeft: '1px solid #333',
                    backdropFilter: 'blur(10px)',
                    padding: '1.5rem',
                    boxSizing: 'border-box',
                    overflowY: 'auto',
                    transform: 'translateX(0)',
                    transition: 'transform 0.3s ease'
                }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                        <h2 style={{ margin: 0, color: COLORS.ORCHESTRATOR, fontSize: '1.1rem' }}>{selectedAgent}</h2>
                        <button onClick={() => setSelectedAgent(null)} style={{ background: 'none', border: 'none', color: '#666', cursor: 'pointer' }}>
                            <X size={18} />
                        </button>
                    </div>

                    <div style={{ marginBottom: '1.5rem' }}>
                        <span style={{ fontSize: '0.8rem', color: '#888', textTransform: 'uppercase', letterSpacing: '1px' }}>ROLE</span>
                        <p style={{ margin: '0.25rem 0 0 0', color: '#E2E8F0', fontWeight: 600 }}>{AGENT_ROLES[selectedAgent]}</p>
                    </div>

                    <div style={{ marginBottom: '1.5rem' }}>
                        <span style={{ fontSize: '0.8rem', color: '#888', textTransform: 'uppercase', letterSpacing: '1px' }}>STATUS</span>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '0.25rem' }}>
                            {agentStatus[selectedAgent] === 'done' ? <CheckCircle size={16} color="#10B981" /> :
                                agentStatus[selectedAgent] === 'working' ? <Activity size={16} color="#FFFFFF" /> :
                                    <Clock size={16} color="#666" />
                            }
                            <span style={{ color: '#E2E8F0', textTransform: 'capitalize' }}>{agentStatus[selectedAgent] || 'Idle'}</span>
                        </div>
                    </div>

                    <div style={{ marginBottom: '1.5rem' }}>
                        <span style={{ fontSize: '0.8rem', color: '#888', textTransform: 'uppercase', letterSpacing: '1px' }}>INTELLIGENCE</span>
                        {selectedAgentDetail ? (
                            <div style={{ marginTop: '0.25rem' }}>
                                <div style={{ color: '#E2E8F0', fontWeight: 600 }}>{selectedAgentDetail.model}</div>
                                <div style={{ fontSize: '0.75rem', color: '#57C7E3' }}>{selectedAgentDetail.ai_provider}</div>
                            </div>
                        ) : (
                            <div style={{ marginTop: '0.25rem', color: '#666', fontStyle: 'italic' }}>System Process</div>
                        )}
                    </div>

                    <div>
                        <span style={{ fontSize: '0.8rem', color: '#888', textTransform: 'uppercase', letterSpacing: '1px', display: 'block', marginBottom: '0.5rem' }}>RECENT LOGS</span>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                            {agentMessages.length > 0 ? agentMessages.map((m, i) => (
                                <div key={i} style={{ fontSize: '0.75rem', background: '#252525', padding: '8px', borderRadius: '4px', borderLeft: `2px solid ${m.from_agent === selectedAgent ? '#57C7E3' : '#666'}` }}>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '2px', opacity: 0.7 }}>
                                        <span>{m.from_agent}</span>
                                        <span>{new Date(m.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                                    </div>
                                    <div style={{ color: '#ccc' }}>{m.message.substring(0, 80)}...</div>
                                </div>
                            )) : (
                                <span style={{ fontSize: '0.8rem', color: '#666', fontStyle: 'italic' }}>No recent activity.</span>
                            )}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};
