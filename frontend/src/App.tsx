import { useState, useEffect } from 'react';
import { ArrowLeft, Download } from 'lucide-react';
import { SessionSetup } from './components/SessionSetup';
import { SessionList } from './components/SessionList';
import { DiscussionForum } from './components/DiscussionForum';
import { AgentGraph } from './components/AgentGraph';
import { api, Session } from './api';
import './App.css';

function App() {
    const [view, setView] = useState<'list' | 'session'>('list');
    const [listSubView, setListSubView] = useState<'sessions' | 'new'>('sessions');
    const [sessionId, setSessionId] = useState<number | null>(null);
    const [sessionData, setSessionData] = useState<Session | null>(null);

    const handleSessionCreated = (id: number) => {
        setSessionId(id);
        fetchSessionData(id);
        setView('session');
    };

    const handleSessionSelected = (id: number) => {
        setSessionId(id);
        fetchSessionData(id);
        setView('session');
    };

    const fetchSessionData = async (id: number) => {
        try {
            const data = await api.getSession(id);
            setSessionData(data);
        } catch (error) {
            console.error('Failed to fetch session:', error);
        }
    };

    const handleBackToSessions = () => {
        setSessionId(null);
        setSessionData(null);
        setView('list');
        setListSubView('sessions');
    };

    // Poll for session updates when in session view
    useEffect(() => {
        if (view === 'session' && sessionId) {
            const interval = setInterval(() => fetchSessionData(sessionId), 5000);
            return () => clearInterval(interval);
        }
    }, [view, sessionId]);

    if (view === 'list') {
        return (
            <div className="app">
                <header className="app-header">
                    <div className="header-left">
                        <h1>Multi-Agent PSUR System</h1>
                        {listSubView === 'new' && (
                            <button
                                type="button"
                                className="btn-back-inline"
                                onClick={() => setListSubView('sessions')}
                            >
                                <ArrowLeft size={16} /> Back to sessions
                            </button>
                        )}
                    </div>
                </header>
                <main className="main-container list-main">
                    {listSubView === 'sessions' ? (
                        <SessionList
                            onSessionSelected={handleSessionSelected}
                            onNewSession={() => setListSubView('new')}
                        />
                    ) : (
                        <SessionSetup
                            onSessionCreated={handleSessionCreated}
                            onCancel={() => setListSubView('sessions')}
                        />
                    )}
                </main>
            </div>
        );
    }

    // Dashboard view
    return (
        <div className="app">
            <header className="app-header">
                <div className="header-left">
                    <button className="btn-icon-back" onClick={handleBackToSessions} style={{ marginRight: '1rem', background: 'transparent', border: 'none', color: 'inherit', cursor: 'pointer' }}>
                        <ArrowLeft size={18} />
                    </button>
                    <h1>{sessionData?.device_name || 'Session Dashboard'}</h1>
                </div>
                {sessionData?.status && (
                    <div style={{
                        background: sessionData.status === 'complete' ? '#8DCC93' : '#57C7E3',
                        color: '#000',
                        padding: '4px 12px',
                        borderRadius: '12px',
                        fontSize: '0.8rem',
                        fontWeight: 700,
                        textTransform: 'uppercase'
                    }}>
                        {sessionData.status.toUpperCase()}
                    </div>
                )}
            </header>

            <main className="app-main">
                {/* Left Sidebar: Session Info */}
                <aside className="sidebar-nav">
                    <div className="nav-item">
                        <h3 className="nav-title" style={{ fontSize: '0.9rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Session Overview</h3>
                        {sessionData && (
                            <div style={{ fontSize: '0.85rem', marginTop: '1rem' }}>
                                <p style={{ margin: '0.5rem 0' }}><strong>Device:</strong> {sessionData.device_name}</p>
                                <p style={{ margin: '0.5rem 0' }}><strong>UDI-DI:</strong> {sessionData.udi_di || 'Pending Extraction'}</p>
                                <p style={{ margin: '0.5rem 0' }}><strong>Period:</strong> {new Date(sessionData.period_start).toLocaleDateString()} - {new Date(sessionData.period_end).toLocaleDateString()}</p>
                            </div>
                        )}
                    </div>
                    <div className="nav-item">
                        <h3 className="nav-title" style={{ fontSize: '0.9rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Progress</h3>
                        <div className="progress-bar" style={{ marginTop: '0.5rem', background: '#334155', height: '8px', borderRadius: '4px', overflow: 'hidden' }}>
                            <div
                                style={{
                                    width: `${(sessionData?.workflow?.sections_completed || 0) / (sessionData?.workflow?.total_sections || 13) * 100}%`,
                                    background: '#8DCC93',
                                    height: '100%',
                                    transition: 'width 0.5s'
                                }}
                            />
                        </div>
                        <p style={{ fontSize: '0.8rem', marginTop: '0.5rem', color: '#94a3b8' }}>
                            {sessionData?.workflow?.sections_completed || 0} of {sessionData?.workflow?.total_sections || 13} sections
                        </p>
                    </div>
                </aside>

                {/* Center: Discussion Forum */}
                <div className="main-content" style={{ borderRight: '1px solid #334155', height: '100%', overflow: 'hidden', position: 'relative' }}>
                    <DiscussionForum sessionId={sessionId!} />
                </div>

                {/* Right Sidebar: Agent Network Graph */}
                <aside className="sidebar-agents" style={{ padding: 0, overflow: 'hidden', background: '#0B0D11' }}>
                    <AgentGraph sessionId={sessionId!} />
                </aside>
            </main>

            <footer className="app-footer">
                <span>Multi-Agent System v2.1 • {sessionId}</span>
                {sessionData?.status === 'complete' && (
                    <a
                        href={`http://localhost:8000/api/sessions/${sessionId}/document/download`}
                        download
                        className="download-btn"
                    >
                        <Download size={16} />
                        Download PSUR
                    </a>
                )}
            </footer>
        </div>
    );
}

export default App;
