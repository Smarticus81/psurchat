import { useEffect, useState } from 'react';
import { Users, Activity, CheckCircle, Clock, Loader } from 'lucide-react';
import { Agent, AGENT_COLORS } from '../types';
import { api } from '../api';
import { useWebSocket } from '../hooks/useWebSocket';
import './AgentRoster.css';

interface AgentRosterProps {
    sessionId?: number;
}

export const AgentRoster: React.FC<AgentRosterProps> = ({ sessionId = 1 }) => {
    const [agents, setAgents] = useState<Agent[]>([]);
    const [loading, setLoading] = useState(true);
    const { messages: wsMessages } = useWebSocket(sessionId);

    useEffect(() => {
        loadAgents();
        // Poll every 2 seconds for faster updates
        const interval = setInterval(loadAgents, 2000);
        return () => clearInterval(interval);
    }, [sessionId]);

    useEffect(() => {
        // Handle WebSocket status updates
        wsMessages.forEach((wsMsg) => {
            if (wsMsg.type === 'agent_status_update') {
                setAgents(prev => prev.map(a =>
                    a.id === wsMsg.agent_id
                        ? { ...a, status: wsMsg.status }
                        : a
                ));
            }
        });
    }, [wsMessages]);

    const loadAgents = async () => {
        try {
            console.log(`👥 Fetching agents for session ${sessionId}...`);
            const data = await api.getAgents(sessionId);
            console.log(`✅ Got ${data.length} agents`);
            setAgents(data);
            setLoading(false);
        } catch (error) {
            console.error('Failed to load agents:', error);
            setLoading(false);
        }
    };

    const getStatusIcon = (status?: string) => {
        switch (status) {
            case 'working':
                return <Loader className="status-icon animate-spin" size={14} />;
            case 'complete':
                return <CheckCircle className="status-icon" size={14} />;
            case 'waiting':
                return <Clock className="status-icon" size={14} />;
            default:
                return <Activity className="status-icon" size={14} />;
        }
    };

    const getStatusLabel = (status?: string): string => {
        switch (status) {
            case 'working': return 'Working';
            case 'complete': return 'Complete';
            case 'waiting': return 'Waiting';
            default: return 'Idle';
        }
    };

    const getProviderBadge = (provider: string): string => {
        const badges: Record<string, string> = {
            openai: 'OpenAI',
            anthropic: 'Anthropic',
            google: 'Google',
            perplexity: 'Perplexity',
        };
        return badges[provider] || provider;
    };

    return (
        <div className="agent-roster">
            <div className="roster-header">
                <div className="header-title">
                    <Users size={20} />
                    <h3>Agent Team</h3>
                </div>

                <div className="agent-stats">
                    <div className="stat">
                        <div className="stat-value">{agents.length}</div>
                        <div className="stat-label">Total</div>
                    </div>
                    <div className="stat">
                        <div className="stat-value" style={{ color: 'var(--accent-primary)' }}>
                            {agents.filter(a => a.status === 'working').length}
                        </div>
                        <div className="stat-label">Active</div>
                    </div>
                    <div className="stat">
                        <div className="stat-value" style={{ color: 'var(--accent-success)' }}>
                            {agents.filter(a => a.status === 'complete').length}
                        </div>
                        <div className="stat-label">Done</div>
                    </div>
                </div>
            </div>

            <div className="agents-list">
                {loading ? (
                    <div className="loading-state">
                        <div className="spinner"></div>
                        <p>Loading agents...</p>
                    </div>
                ) : agents.length === 0 ? (
                    <div className="loading-state">
                        <p>No agents found. Create a session to initialize agents.</p>
                    </div>
                ) : (
                    agents.map((agent) => (
                        <div
                            key={agent.id}
                            className={`agent-card ${agent.status === 'working' ? 'working' : ''} ${agent.status === 'complete' ? 'complete' : ''}`}
                        >
                            <div className="agent-card-header">
                                <div
                                    className="agent-avatar-small"
                                    style={{ backgroundColor: AGENT_COLORS[agent.name] || '#6366f1' }}
                                >
                                    {agent.name.charAt(0)}
                                </div>
                                <div className="agent-info-compact">
                                    <div className="agent-name-small">{agent.name}</div>
                                    <div className="agent-role-small">{agent.role}</div>
                                </div>
                            </div>

                            <div className="agent-metadata">
                                <span className="provider-badge">{getProviderBadge(agent.ai_provider)}</span>
                                <span className={`status-badge status-${agent.status}`}>
                                    {getStatusIcon(agent.status)}
                                    {getStatusLabel(agent.status)}
                                </span>
                            </div>

                            <div className="model-info">{agent.model}</div>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
};
