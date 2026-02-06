import { useState, useEffect } from 'react';
import { ArrowLeft, Download, Shield } from 'lucide-react';
import { SessionSetup } from './components/SessionSetup';
import { SessionList } from './components/SessionList';
import { DiscussionForum } from './components/DiscussionForum';
import { NeuralView } from './components/NeuralView';
import { api, Session } from './api';
import './App.css';

const API_ROOT = import.meta.env.VITE_API_URL || 'http://localhost:8000';

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

    useEffect(() => {
        if (view === 'session' && sessionId) {
            const interval = setInterval(() => fetchSessionData(sessionId), 5000);
            return () => clearInterval(interval);
        }
    }, [view, sessionId]);

    const progressPct = sessionData?.workflow
        ? (sessionData.workflow.sections_completed / (sessionData.workflow.total_sections || 13)) * 100
        : 0;

    // ---------- List / Setup view ----------
    if (view === 'list') {
        return (
            <div className="app">
                <header className="app-header">
                    <div className="header-left">
                        <Shield size={20} className="header-logo-icon" />
                        <h1>PSUR<span className="header-accent">.ai</span></h1>
                        {listSubView === 'new' && (
                            <button
                                type="button"
                                className="btn-back-inline"
                                onClick={() => setListSubView('sessions')}
                            >
                                <ArrowLeft size={16} /> Back
                            </button>
                        )}
                    </div>
                    <span className="header-tagline">Collaborative AI-Powered Safety Reporting</span>
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

    // ---------- Dashboard view ----------
    return (
        <div className="app">
            <header className="app-header">
                <div className="header-left">
                    <button className="btn-icon-back" onClick={handleBackToSessions}>
                        <ArrowLeft size={18} />
                    </button>
                    <h1>{sessionData?.device_name || 'Session Dashboard'}</h1>
                </div>
                <div className="header-right">
                    {sessionData?.status && (
                        <div className={`status-badge status-badge--${sessionData.status}`}>
                            <span className="status-badge__dot" />
                            {sessionData.status}
                        </div>
                    )}
                </div>
            </header>

            <main className="app-main">
                {/* Left Sidebar */}
                <aside className="sidebar-nav">
                    <div className="nav-item">
                        <h3 className="nav-title">Session Overview</h3>
                        {sessionData && (
                            <div className="sidebar-info">
                                <p className="sidebar-info-item">
                                    <span className="sidebar-info-label">Device</span>
                                    <span className="sidebar-info-value">{sessionData.device_name}</span>
                                </p>
                                <p className="sidebar-info-item">
                                    <span className="sidebar-info-label">UDI-DI</span>
                                    <span className="sidebar-info-value sidebar-info-value--mono">{sessionData.udi_di || 'Pending'}</span>
                                </p>
                                <p className="sidebar-info-item">
                                    <span className="sidebar-info-label">Period</span>
                                    <span className="sidebar-info-value">
                                        {new Date(sessionData.period_start).toLocaleDateString()} &ndash; {new Date(sessionData.period_end).toLocaleDateString()}
                                    </span>
                                </p>
                            </div>
                        )}
                    </div>
                    <div className="nav-item">
                        <h3 className="nav-title">Progress</h3>
                        <div className="sidebar-progress">
                            <div className="sidebar-progress__track">
                                <div
                                    className="sidebar-progress__fill"
                                    style={{ width: `${progressPct}%` }}
                                />
                            </div>
                            <span className="sidebar-progress__label">
                                {sessionData?.workflow?.sections_completed || 0} / {sessionData?.workflow?.total_sections || 13} sections
                            </span>
                        </div>
                    </div>
                </aside>

                {/* Center: Chat */}
                <div className="main-content">
                    {sessionId != null ? <DiscussionForum sessionId={sessionId} /> : null}
                </div>

                {/* Right: Neural View */}
                <aside className="sidebar-agents">
                    <NeuralView sessionId={sessionId!} />
                </aside>
            </main>

            <footer className="app-footer">
                <span className="footer-brand">PSUR.ai</span>
                {sessionData?.status === 'complete' && (
                    <a
                        href={`${API_ROOT}/api/sessions/${sessionId}/document/download`}
                        download
                        className="download-btn"
                    >
                        <Download size={14} />
                        Download PSUR
                    </a>
                )}
            </footer>
        </div>
    );
}

export default App;
