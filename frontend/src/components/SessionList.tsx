import { useEffect, useState } from 'react';
import { FileText, Download, Eye, Plus, Calendar, Clock, Trash2 } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { api } from '../api';
import './SessionList.css';

interface Session {
    id: number;
    device_name: string;
    udi_di: string;
    status: string;
    period_start: string;
    period_end: string;
    created_at: string;
    updated_at: string;
    workflow?: {
        sections_completed: number;
        total_sections: number;
    };
}

interface SessionListProps {
    onSessionSelected: (sessionId: number) => void;
    onNewSession: () => void;
}

export const SessionList: React.FC<SessionListProps> = ({ onSessionSelected, onNewSession }) => {
    const [sessions, setSessions] = useState<Session[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        loadSessions();
        const interval = setInterval(loadSessions, 5000);
        return () => clearInterval(interval);
    }, []);

    const loadSessions = async () => {
        try {
            const data = await api.getSessions();
            setSessions(data);
            setLoading(false);
        } catch (error) {
            console.error('Failed to load sessions:', error);
            setLoading(false);
        }
    };

    const handleDeleteSession = async (e: React.MouseEvent, sessionId: number) => {
        e.stopPropagation();
        if (confirm('Are you sure you want to delete this session? This cannot be undone.')) {
            try {
                await api.deleteSession(sessionId);
                loadSessions(); // Refresh list
            } catch (error) {
                console.error('Failed to delete session:', error);
                alert('Failed to delete session');
            }
        }
    };

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'complete': return '#10b981';
            case 'running': return '#3b82f6';
            case 'error': return '#ef4444';
            default: return '#6b7280';
        }
    };

    const getStatusIcon = (status: string) => {
        return status === 'complete' ? '✅' : status === 'running' ? '🔄' : '⏸️';
    };

    if (loading) {
        return (
            <div className="session-list-container">
                <div className="loading-spinner">Loading sessions...</div>
            </div>
        );
    }

    return (
        <div className="session-list-container">
            <div className="session-list-header">
                <div>
                    <h1>📊 PSUR Sessions</h1>
                    <p>View and manage your Periodic Safety Update Reports</p>
                </div>
                <button className="btn-new-session" onClick={onNewSession}>
                    <Plus size={20} />
                    New Session
                </button>
            </div>

            <div className="sessions-grid">
                {sessions.length === 0 ? (
                    <div className="empty-state">
                        <FileText size={64} opacity={0.3} />
                        <h3>No sessions yet</h3>
                        <p>Create your first PSUR session to get started</p>
                        <button className="btn-primary" onClick={onNewSession}>
                            <Plus size={20} />
                            Create First Session
                        </button>
                    </div>
                ) : (
                    sessions.map(session => (
                        <div key={session.id} className="session-card">
                            <div className="session-card-header">
                                <div className="session-icon">
                                    <FileText size={24} />
                                </div>
                                <div
                                    className="session-status"
                                    style={{ background: getStatusColor(session.status) }}
                                >
                                    {getStatusIcon(session.status)} {session.status}
                                </div>
                            </div>

                            <div className="session-card-body">
                                <h3>{session.device_name}</h3>
                                <p className="session-udi">UDI-DI: {session.udi_di}</p>

                                <div className="session-meta">
                                    <div className="meta-item">
                                        <Calendar size={14} />
                                        <span>{new Date(session.period_start).toLocaleDateString()} - {new Date(session.period_end).toLocaleDateString()}</span>
                                    </div>
                                    <div className="meta-item">
                                        <Clock size={14} />
                                        <span>Created {formatDistanceToNow(new Date(session.created_at))} ago</span>
                                    </div>
                                </div>

                                {session.workflow && (
                                    <div className="progress-bar">
                                        <div
                                            className="progress-fill"
                                            style={{
                                                width: `${(session.workflow.sections_completed / session.workflow.total_sections) * 100}%`
                                            }}
                                        />
                                        <span className="progress-text">
                                            {session.workflow.sections_completed}/{session.workflow.total_sections} sections
                                        </span>
                                    </div>
                                )}
                            </div>

                            <div className="session-card-footer">
                                <button
                                    className="btn-secondary"
                                    onClick={() => onSessionSelected(session.id)}
                                >
                                    <Eye size={16} />
                                    View Dashboard
                                </button>

                                {session.status === 'complete' && (
                                    <a
                                        href={`http://localhost:8000/api/sessions/${session.id}/document/download`}
                                        download
                                        className="btn-download"
                                        title="Download PSUR"
                                    >
                                        <Download size={16} />
                                    </a>
                                )}

                                <button
                                    className="btn-delete"
                                    onClick={(e) => handleDeleteSession(e, session.id)}
                                    title="Delete Session"
                                >
                                    <Trash2 size={16} />
                                </button>
                            </div>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
};
