import React, { useEffect, useRef, useState, useMemo } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import { api, ChatMessage, SectionDoc, Agent } from '../api';
import { 
    Activity, CheckCircle, Clock, X, Network, 
    GitBranch, BarChart3, Zap, MessageSquare, Users
} from 'lucide-react';
import './NeuralView.css';

interface NeuralViewProps {
    sessionId: number;
}

// SOTA Mapping: Sections to Agents
const AGENT_MAP: Record<string, string> = {
    'A': 'Marcus', 'B': 'Greta', 'C': 'Greta', 'D': 'David',
    'E': 'Emma', 'F': 'Emma', 'G': 'Diana', 'H': 'Lisa',
    'I': 'Tom', 'J': 'James', 'K': 'James', 'L': 'Sarah', 'M': 'Robert'
};

// Section names for display
const SECTION_NAMES: Record<string, string> = {
    'A': 'Executive Summary', 'B': 'Scope & Device', 'C': 'Units Distributed',
    'D': 'Serious Incidents', 'E': 'Customer Feedback', 'F': 'Complaints',
    'G': 'Trends Analysis', 'H': 'FSCA', 'I': 'CAPA',
    'J': 'Literature Review', 'K': 'External Databases', 'L': 'PMCF', 'M': 'Conclusions'
};

// Agent Roles
const AGENT_ROLES: Record<string, string> = {
    'Alex': 'Orchestrator', 'Marcus': 'Executive Summary', 'Greta': 'Sales & Market Data',
    'David': 'Vigilance Specialist', 'Emma': 'Complaint Classifier', 'Diana': 'Trend Detective',
    'Lisa': 'FSCA Coordinator', 'Tom': 'CAPA Verifier', 'James': 'Literature Reviewer',
    'Sarah': 'PMCF Specialist', 'Robert': 'Risk Specialist', 'Victoria': 'QC Expert',
    'Data Core': 'System Data'
};

// Colors
const COLORS = {
    ORCHESTRATOR: '#57C7E3', SYSTEM: '#8DCC93', WRITER: '#F79767',
    QC: '#F16667', SYNTHESIS: '#FFE081', BG: '#0B0D11',
};

const AGENT_COLORS: Record<string, string> = {
    'Alex': '#57C7E3', 'Victoria': '#F16667', 'Marcus': '#FFE081', 'Robert': '#FFE081',
    'Greta': '#F79767', 'David': '#F79767', 'Emma': '#F79767', 'Diana': '#F79767',
    'Lisa': '#F79767', 'Tom': '#F79767', 'James': '#F79767', 'Sarah': '#F79767',
    'User': '#9B8FE8', 'System': '#8DCC93', 'Data Core': '#8DCC93'
};

type TabType = 'graph' | 'timeline' | 'metrics';

export const NeuralView: React.FC<NeuralViewProps> = ({ sessionId }) => {
    const [activeTab, setActiveTab] = useState<TabType>('graph');
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [sections, setSections] = useState<SectionDoc[]>([]);
    const [agents, setAgents] = useState<Agent[]>([]);
    const [activeNodes, setActiveNodes] = useState<Set<string>>(new Set());
    const [agentStatus, setAgentStatus] = useState<Record<string, string>>({});

    // Data Polling
    useEffect(() => {
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

        const interval = setInterval(fetchData, 2000);
        fetchData();
        return () => clearInterval(interval);
    }, [sessionId]);

    // Compute Agent Status
    useEffect(() => {
        const statusMap: Record<string, string> = {};
        const active = new Set<string>();

        Object.keys(AGENT_ROLES).forEach(a => statusMap[a] = 'idle');

        sections.forEach(s => {
            const agent = AGENT_MAP[s.section_id];
            if (!agent) return;

            if (s.status === 'in_progress' || s.status === 'draft') {
                statusMap[agent] = 'working';
                statusMap['Alex'] = 'coordinating';
                active.add(agent);
                active.add('Alex');
            } else if (s.status === 'review') {
                statusMap[agent] = 'waiting';
                statusMap['Victoria'] = 'reviewing';
                active.add('Victoria');
                active.add(agent);
            } else if (s.status === 'complete' || s.status === 'approved') {
                statusMap[agent] = 'done';
            }
        });

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

    return (
        <div className="neural-view">
            <div className="neural-tabs">
                <button 
                    className={`neural-tab ${activeTab === 'graph' ? 'neural-tab--active' : ''}`}
                    onClick={() => setActiveTab('graph')}
                >
                    <Network size={14} />
                    <span>Graph</span>
                </button>
                <button 
                    className={`neural-tab ${activeTab === 'timeline' ? 'neural-tab--active' : ''}`}
                    onClick={() => setActiveTab('timeline')}
                >
                    <GitBranch size={14} />
                    <span>Timeline</span>
                </button>
                <button 
                    className={`neural-tab ${activeTab === 'metrics' ? 'neural-tab--active' : ''}`}
                    onClick={() => setActiveTab('metrics')}
                >
                    <BarChart3 size={14} />
                    <span>Metrics</span>
                </button>
            </div>
            <div className="neural-content">
                {activeTab === 'graph' && (
                    <GraphPanel 
                        sessionId={sessionId}
                        agents={agents}
                        activeNodes={activeNodes}
                        agentStatus={agentStatus}
                    />
                )}
                {activeTab === 'timeline' && (
                    <TimelinePanel 
                        messages={messages}
                        sections={sections}
                    />
                )}
                {activeTab === 'metrics' && (
                    <MetricsPanel 
                        messages={messages}
                        sections={sections}
                        agents={agents}
                        agentStatus={agentStatus}
                    />
                )}
            </div>
        </div>
    );
};

// Graph Panel Component
const GraphPanel: React.FC<{
    sessionId: number;
    agents: Agent[];
    activeNodes: Set<string>;
    agentStatus: Record<string, string>;
}> = ({ agents, activeNodes, agentStatus }) => {
    const fgRef = useRef<any>();
    const [dimensions, setDimensions] = useState({ w: 400, h: 400 });
    const containerRef = useRef<HTMLDivElement>(null);
    const [selectedAgent, setSelectedAgent] = useState<string | null>(null);

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
        setTimeout(updateDimensions, 100);
        return () => window.removeEventListener('resize', updateDimensions);
    }, []);

    const graphData = useMemo(() => {
        const nodes = Object.keys(AGENT_ROLES).map(id => {
            let group = 3;
            let color = COLORS.WRITER;

            if (id === 'Alex') { group = 1; color = COLORS.ORCHESTRATOR; }
            else if (id === 'Victoria') { group = 2; color = COLORS.QC; }
            else if (id === 'Data Core') { group = 0; color = COLORS.SYSTEM; }
            else if (id === 'Marcus' || id === 'Robert') { color = COLORS.SYNTHESIS; }

            let val = 15;
            if (id === 'Alex') val = 30;
            if (id === 'Data Core') val = 20;

            return { id, group, val, label: id, color, role: AGENT_ROLES[id] };
        });

        const links: any[] = [];
        nodes.forEach(n => {
            if (n.id !== 'Alex') links.push({ source: 'Alex', target: n.id });
        });
        nodes.filter(n => n.group === 3).forEach(n => {
            links.push({ source: 'Data Core', target: n.id });
            links.push({ source: 'Victoria', target: n.id });
        });

        return { nodes, links };
    }, []);

    const selectedAgentDetail = agents.find(a => a.name === selectedAgent);

    return (
        <div ref={containerRef} className="graph-panel">
            <ForceGraph2D
                ref={fgRef}
                width={dimensions.w}
                height={dimensions.h}
                graphData={graphData}
                backgroundColor={COLORS.BG}
                nodeRelSize={6}
                d3VelocityDecay={0.3}
                cooldownTicks={100}
                onNodeClick={(node) => {
                    setSelectedAgent(node.id === selectedAgent ? null : node.id as string);
                    fgRef.current?.centerAt(node.x, node.y, 400);
                    fgRef.current?.zoom(2.5, 400);
                }}
                linkWidth={() => 0.5}
                linkColor={() => '#333333'}
                linkDirectionalParticles={2}
                linkDirectionalParticleSpeed={d => activeNodes.has((d.source as any).id) || activeNodes.has((d.target as any).id) ? 0.005 : 0}
                linkDirectionalParticleWidth={2}
                linkDirectionalParticleColor={() => '#555'}
                nodeCanvasObject={(node: any, ctx, globalScale) => {
                    const isActive = activeNodes.has(node.id);
                    const status = agentStatus[node.id];
                    const isSelected = selectedAgent === node.id;
                    const r = node.val ? Math.sqrt(node.val) * 1.5 : 5;

                    if (isSelected) {
                        ctx.beginPath();
                        ctx.arc(node.x, node.y, r + 8, 0, 2 * Math.PI, false);
                        ctx.strokeStyle = '#FFFFFF';
                        ctx.lineWidth = 1;
                        ctx.stroke();
                    }

                    if (isActive || status === 'working') {
                        const time = Date.now();
                        const pulse = Math.sin(time / 200) * 3 + 3;
                        ctx.beginPath();
                        ctx.arc(node.x, node.y, r + pulse, 0, 2 * Math.PI, false);
                        ctx.fillStyle = `rgba(${node.color === COLORS.ORCHESTRATOR ? '87, 199, 227' : '247, 151, 103'}, 0.2)`;
                        ctx.fill();
                    }

                    ctx.beginPath();
                    ctx.arc(node.x, node.y, r, 0, 2 * Math.PI, false);
                    ctx.fillStyle = node.color;
                    ctx.fill();

                    if (status === 'done') {
                        ctx.beginPath();
                        ctx.arc(node.x + r - 2, node.y - r + 2, 3, 0, 2 * Math.PI, false);
                        ctx.fillStyle = '#10B981';
                        ctx.fill();
                    } else if (status === 'working') {
                        ctx.beginPath();
                        ctx.arc(node.x + r - 2, node.y - r + 2, 3, 0, 2 * Math.PI, false);
                        ctx.fillStyle = '#FFFFFF';
                        ctx.fill();
                    }

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

            {selectedAgent && (
                <div className="agent-detail-overlay">
                    <div className="agent-detail__header">
                        <h2 style={{ color: AGENT_COLORS[selectedAgent] }}>{selectedAgent}</h2>
                        <button onClick={() => setSelectedAgent(null)} className="btn-close">
                            <X size={16} />
                        </button>
                    </div>
                    <div className="agent-detail__row">
                        <span className="agent-detail__label">Role</span>
                        <span className="agent-detail__value">{AGENT_ROLES[selectedAgent]}</span>
                    </div>
                    <div className="agent-detail__row">
                        <span className="agent-detail__label">Status</span>
                        <div className="agent-detail__status">
                            {agentStatus[selectedAgent] === 'done' ? <CheckCircle size={14} color="#10B981" /> :
                                agentStatus[selectedAgent] === 'working' ? <Activity size={14} color="#FFFFFF" /> :
                                    <Clock size={14} color="#666" />
                            }
                            <span>{agentStatus[selectedAgent] || 'Idle'}</span>
                        </div>
                    </div>
                    {selectedAgentDetail && (
                        <div className="agent-detail__row">
                            <span className="agent-detail__label">Model</span>
                            <div>
                                <div className="agent-detail__value">{selectedAgentDetail.model}</div>
                                <div className="agent-detail__sub">{selectedAgentDetail.ai_provider}</div>
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
};

// Timeline Panel Component
const TimelinePanel: React.FC<{
    messages: ChatMessage[];
    sections: SectionDoc[];
}> = ({ messages, sections }) => {
    
    // Build timeline events from messages and sections
    const events = useMemo(() => {
        const items: Array<{
            id: string;
            timestamp: Date;
            type: 'message' | 'section_start' | 'section_complete' | 'qc';
            agent: string;
            content: string;
            color: string;
        }> = [];

        // Add messages as events
        messages.forEach((m, i) => {
            if (m.message_type === 'system') return;
            items.push({
                id: `msg-${m.id}`,
                timestamp: new Date(m.timestamp),
                type: 'message',
                agent: m.from_agent,
                content: m.message.substring(0, 100) + (m.message.length > 100 ? '...' : ''),
                color: AGENT_COLORS[m.from_agent] || '#57C7E3'
            });
        });

        // Add section events
        sections.forEach(s => {
            const agent = AGENT_MAP[s.section_id] || 'Unknown';
            if (s.status === 'approved' || s.status === 'complete') {
                items.push({
                    id: `sec-${s.section_id}`,
                    timestamp: new Date(s.created_at),
                    type: 'section_complete',
                    agent,
                    content: `Section ${s.section_id}: ${SECTION_NAMES[s.section_id] || s.section_name} completed`,
                    color: '#8DCC93'
                });
            }
        });

        // Sort by timestamp descending (newest first)
        return items.sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime()).slice(0, 50);
    }, [messages, sections]);

    return (
        <div className="timeline-panel">
            <div className="timeline-header">
                <Zap size={14} />
                <span>Activity Feed</span>
                <span className="timeline-count">{events.length} events</span>
            </div>
            <div className="timeline-list">
                {events.length === 0 ? (
                    <div className="timeline-empty">
                        <GitBranch size={24} strokeWidth={1.5} />
                        <span>No activity yet</span>
                    </div>
                ) : (
                    events.map((event) => (
                        <div key={event.id} className="timeline-item">
                            <div className="timeline-marker" style={{ backgroundColor: event.color }} />
                            <div className="timeline-content">
                                <div className="timeline-meta">
                                    <span className="timeline-agent" style={{ color: event.color }}>
                                        {event.agent}
                                    </span>
                                    <span className="timeline-time">
                                        {event.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                    </span>
                                </div>
                                <div className="timeline-text">{event.content}</div>
                            </div>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
};

// Metrics Panel Component
const MetricsPanel: React.FC<{
    messages: ChatMessage[];
    sections: SectionDoc[];
    agents: Agent[];
    agentStatus: Record<string, string>;
}> = ({ messages, sections, agents, agentStatus }) => {
    
    const stats = useMemo(() => {
        const completedSections = sections.filter(s => s.status === 'approved' || s.status === 'complete').length;
        const totalSections = 13;
        const workingAgents = Object.values(agentStatus).filter(s => s === 'working' || s === 'coordinating').length;
        const completedAgents = Object.values(agentStatus).filter(s => s === 'done').length;
        
        // Count messages per agent
        const agentMessageCounts: Record<string, number> = {};
        messages.forEach(m => {
            if (m.from_agent !== 'System') {
                agentMessageCounts[m.from_agent] = (agentMessageCounts[m.from_agent] || 0) + 1;
            }
        });

        const topAgents = Object.entries(agentMessageCounts)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 5);

        return {
            completedSections,
            totalSections,
            progress: (completedSections / totalSections) * 100,
            totalMessages: messages.filter(m => m.message_type !== 'system').length,
            workingAgents,
            completedAgents,
            topAgents
        };
    }, [messages, sections, agentStatus]);

    return (
        <div className="metrics-panel">
            <div className="metrics-header">
                <BarChart3 size={14} />
                <span>Runtime Metrics</span>
            </div>

            <div className="metrics-grid">
                {/* Progress Card */}
                <div className="metric-card metric-card--wide">
                    <div className="metric-card__header">
                        <span className="metric-card__title">Generation Progress</span>
                        <span className="metric-card__value">{stats.completedSections}/{stats.totalSections}</span>
                    </div>
                    <div className="metric-progress">
                        <div 
                            className="metric-progress__bar" 
                            style={{ width: `${stats.progress}%` }}
                        />
                    </div>
                    <span className="metric-card__sub">{stats.progress.toFixed(0)}% complete</span>
                </div>

                {/* Messages */}
                <div className="metric-card">
                    <div className="metric-card__icon">
                        <MessageSquare size={18} />
                    </div>
                    <div className="metric-card__body">
                        <span className="metric-card__value">{stats.totalMessages}</span>
                        <span className="metric-card__title">Messages</span>
                    </div>
                </div>

                {/* Active Agents */}
                <div className="metric-card">
                    <div className="metric-card__icon metric-card__icon--active">
                        <Zap size={18} />
                    </div>
                    <div className="metric-card__body">
                        <span className="metric-card__value">{stats.workingAgents}</span>
                        <span className="metric-card__title">Working</span>
                    </div>
                </div>

                {/* Completed Agents */}
                <div className="metric-card">
                    <div className="metric-card__icon metric-card__icon--success">
                        <CheckCircle size={18} />
                    </div>
                    <div className="metric-card__body">
                        <span className="metric-card__value">{stats.completedAgents}</span>
                        <span className="metric-card__title">Done</span>
                    </div>
                </div>
            </div>

            {/* Top Contributors */}
            <div className="metric-section">
                <div className="metric-section__header">
                    <Users size={14} />
                    <span>Top Contributors</span>
                </div>
                <div className="metric-list">
                    {stats.topAgents.length === 0 ? (
                        <div className="metric-empty">No activity yet</div>
                    ) : (
                        stats.topAgents.map(([agent, count]) => (
                            <div key={agent} className="metric-list-item">
                                <div 
                                    className="metric-list-item__avatar"
                                    style={{ borderColor: AGENT_COLORS[agent] || '#57C7E3' }}
                                >
                                    {agent.charAt(0)}
                                </div>
                                <span className="metric-list-item__name">{agent}</span>
                                <span className="metric-list-item__count">{count} msgs</span>
                            </div>
                        ))
                    )}
                </div>
            </div>
        </div>
    );
};

// Keep old export for backwards compatibility
export const AgentGraph = NeuralView;
