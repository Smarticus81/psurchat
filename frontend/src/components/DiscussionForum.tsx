import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import { MessageSquare, ChevronDown, ChevronUp, Pause, Play, Loader2, Send, Eye, X } from 'lucide-react';
import { api, ChatMessage } from '../api';
import './DiscussionForum.css';

const COLLAPSED_MAX_LENGTH = 400;
const COLLAPSED_LINES = 6;

// 18-Agent Discussion Panel Architecture
const AGENT_NAMES = [
    // Orchestrator
    'Alex',
    // Section Agents (13)
    'Diana', 'Sam', 'Raj', 'Vera', 'Carla', 'Tara',
    'Frank', 'Cameron', 'Rita', 'Brianna', 'Eddie', 'Clara', 'Marcus',
    // Analytical Support (3)
    'Statler', 'Charley', 'Quincy',
    // QC
    'Victoria',
];

// Agent color mapping for avatars (18 agents + User + System)
const AGENT_COLORS: Record<string, string> = {
    // Orchestrator
    'Alex': '#6366f1',
    // Section Agents
    'Diana': '#FFE081',
    'Sam': '#D9C8AE',
    'Raj': '#F79767',
    'Vera': '#F16667',
    'Carla': '#DA7194',
    'Tara': '#C990C0',
    'Frank': '#8DCC93',
    'Cameron': '#57C7E3',
    'Rita': '#569480',
    'Brianna': '#4C8EDA',
    'Eddie': '#9b59b6',
    'Clara': '#1abc9c',
    'Marcus': '#e67e22',
    // Analytical Support
    'Statler': '#e74c3c',
    'Charley': '#3498db',
    'Quincy': '#2ecc71',
    // QC
    'Victoria': '#FFC454',
    // Special
    'User': '#9B8FE8',
    'System': '#8DCC93',
};

// Agent Avatar Component
const AgentAvatar: React.FC<{ name: string; size?: number }> = ({ name, size = 36 }) => {
    const color = AGENT_COLORS[name] || '#57C7E3';
    const initial = name === 'User' ? 'Y' : name.charAt(0).toUpperCase();
    const displayName = name === 'User' ? 'You' : name;
    
    return (
        <div 
            className="agent-avatar" 
            style={{ 
                width: size, 
                height: size, 
                borderColor: color,
                fontSize: size * 0.4
            }}
            title={displayName}
        >
            {initial}
        </div>
    );
};

interface WorkflowStatus {
    paused: boolean;
    current_agent: string | null;
    status: string;
    sections_completed: number;
    total_sections: number;
}

interface DiscussionForumProps {
    sessionId: number;
}

export const DiscussionForum: React.FC<DiscussionForumProps> = ({ sessionId }) => {
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [inputText, setInputText] = useState('');
    const [isAutoScroll, setIsAutoScroll] = useState(true);
    const [expandedIds, setExpandedIds] = useState<Set<number>>(new Set());
    const [workflowStatus, setWorkflowStatus] = useState<WorkflowStatus | null>(null);
    const [isPausing, setIsPausing] = useState(false);
    const [isAsking, setIsAsking] = useState(false);
    const [showMentionDropdown, setShowMentionDropdown] = useState(false);
    const [mentionFilter, setMentionFilter] = useState('');
    const [mentionIndex, setMentionIndex] = useState(0);
    const [previewHtml, setPreviewHtml] = useState<string | null>(null);
    const [previewTitle, setPreviewTitle] = useState('');
    const [previewLoading, setPreviewLoading] = useState(false);
    const scrollRef = useRef<HTMLDivElement>(null);
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const inputRef = useRef<HTMLInputElement>(null);

    const handlePreviewSection = async (sectionId: string) => {
        setPreviewLoading(true);
        try {
            const data = await api.getSectionPreview(sessionId, sectionId);
            setPreviewTitle(data.title || `Section ${sectionId}`);
            setPreviewHtml(data.html || '<p>No content available</p>');
        } catch (err) {
            setPreviewHtml('<p>Preview not available yet.</p>');
            setPreviewTitle(`Section ${sectionId}`);
        } finally {
            setPreviewLoading(false);
        }
    };

    const fetchMessages = useCallback(async () => {
        try {
            const data = await api.getMessages(sessionId);
            const list = Array.isArray(data) ? data : [];
            // API returns messages in chronological order already (oldest first)
            setMessages(list);
        } catch (error) {
            console.error('Failed to fetch messages:', error);
        }
    }, [sessionId]);

    const fetchWorkflowStatus = useCallback(async () => {
        try {
            const status = await api.getWorkflowStatus(sessionId);
            if (status?.workflow_state) {
                setWorkflowStatus(status.workflow_state);
            }
        } catch (error) {
            // Workflow might not be started yet
        }
    }, [sessionId]);

    // Parse @mentions from input
    const parseMention = (text: string): { agent: string; question: string } | null => {
        const mentionMatch = text.match(/^@(\w+)\s+(.+)$/);
        if (mentionMatch) {
            const agentName = mentionMatch[1];
            const question = mentionMatch[2];
            const agent = AGENT_NAMES.find(a => a.toLowerCase() === agentName.toLowerCase());
            if (agent) {
                return { agent, question };
            }
        }
        return null;
    };

    const handleSendMessage = async () => {
        if (!inputText.trim()) return;
        
        const mention = parseMention(inputText);
        
        try {
            if (mention) {
                setIsAsking(true);
                await api.askAgent(sessionId, mention.agent, mention.question);
                setInputText('');
                setIsAutoScroll(true);
                fetchMessages();
            } else {
                await api.sendMessage(sessionId, inputText);
                setInputText('');
                setIsAutoScroll(true);
                fetchMessages();
            }
        } catch (error) {
            console.error('Failed to send:', error);
        } finally {
            setIsAsking(false);
        }
    };

    const handlePauseResume = async () => {
        setIsPausing(true);
        try {
            if (workflowStatus?.paused) {
                await api.resumeWorkflow(sessionId);
            } else {
                await api.pauseWorkflow(sessionId);
            }
            setTimeout(fetchWorkflowStatus, 500);
        } catch (error) {
            console.error('Failed to pause/resume:', error);
        } finally {
            setIsPausing(false);
        }
    };

    const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const value = e.target.value;
        setInputText(value);
        
        const lastAtIndex = value.lastIndexOf('@');
        if (lastAtIndex !== -1 && (lastAtIndex === 0 || value[lastAtIndex - 1] === ' ')) {
            const afterAt = value.slice(lastAtIndex + 1).split(' ')[0];
            setMentionFilter(afterAt.toLowerCase());
            setShowMentionDropdown(true);
            setMentionIndex(0);
        } else {
            setShowMentionDropdown(false);
        }
    };

    const filteredAgents = useMemo(() => {
        if (!mentionFilter) return AGENT_NAMES;
        return AGENT_NAMES.filter(name => 
            name.toLowerCase().startsWith(mentionFilter)
        );
    }, [mentionFilter]);

    const insertMention = (agentName: string) => {
        const lastAtIndex = inputText.lastIndexOf('@');
        const newText = inputText.slice(0, lastAtIndex) + '@' + agentName + ' ';
        setInputText(newText);
        setShowMentionDropdown(false);
        inputRef.current?.focus();
    };

    const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
        if (showMentionDropdown && filteredAgents.length > 0) {
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                setMentionIndex(i => Math.min(i + 1, filteredAgents.length - 1));
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                setMentionIndex(i => Math.max(i - 1, 0));
            } else if (e.key === 'Tab' || e.key === 'Enter') {
                if (showMentionDropdown) {
                    e.preventDefault();
                    insertMention(filteredAgents[mentionIndex]);
                    return;
                }
            } else if (e.key === 'Escape') {
                setShowMentionDropdown(false);
            }
        }
        
        if (e.key === 'Enter' && !e.shiftKey && !showMentionDropdown) {
            handleSendMessage();
        }
    };

    const toggleExpanded = (id: number) => {
        setExpandedIds((prev) => {
            const next = new Set(prev);
            if (next.has(id)) next.delete(id);
            else next.add(id);
            return next;
        });
    };

    useEffect(() => {
        setMessages([]);
        setExpandedIds(new Set());
        const messageInterval = setInterval(fetchMessages, 2000);
        const statusInterval = setInterval(fetchWorkflowStatus, 3000);
        fetchMessages();
        fetchWorkflowStatus();
        return () => {
            clearInterval(messageInterval);
            clearInterval(statusInterval);
        };
    }, [sessionId, fetchMessages, fetchWorkflowStatus]);

    useEffect(() => {
        if (isAutoScroll && messagesEndRef.current) {
            messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
        }
    }, [messages, isAutoScroll]);

    const handleScroll = () => {
        if (!scrollRef.current) return;
        const { scrollTop, scrollHeight, clientHeight } = scrollRef.current;
        const isBottom = scrollHeight - scrollTop - clientHeight < 60;
        setIsAutoScroll(isBottom);
    };

    const filteredMessages = useMemo(
        () => messages.filter((m) => m.message_type !== 'system'),
        [messages]
    );

    // Get message type indicator color
    const getTypeIndicator = (type: string) => {
        switch (type) {
            case 'success': return 'var(--neo-green)';
            case 'error': return 'var(--neo-red)';
            case 'warning': return 'var(--neo-yellow)';
            default: return 'transparent';
        }
    };

    return (
        <div className="chat-container">
            {/* Header */}
            <div className="chat-header">
                <div className="chat-header__title">
                    <MessageSquare size={18} />
                    <span>Agent Chat</span>
                </div>
                <div className="chat-header__controls">
                    {workflowStatus && (
                        <button
                            type="button"
                            className={`btn-control ${workflowStatus.paused ? 'btn-control--active' : ''}`}
                            onClick={handlePauseResume}
                            disabled={isPausing || workflowStatus.status === 'complete'}
                            title={workflowStatus.paused ? 'Resume workflow' : 'Pause workflow'}
                        >
                            {isPausing ? (
                                <Loader2 size={14} className="spin" />
                            ) : workflowStatus.paused ? (
                                <Play size={14} />
                            ) : (
                                <Pause size={14} />
                            )}
                        </button>
                    )}
                    <div className={`status-badge ${workflowStatus?.paused ? 'status-badge--paused' : 'status-badge--live'}`}>
                        <span className="status-dot" />
                        {workflowStatus?.paused ? 'Paused' : 'Live'}
                    </div>
                </div>
            </div>

            {/* Status Banner */}
            {workflowStatus?.paused && (
                <div className="status-banner status-banner--warning">
                    Workflow paused. Send a message or click resume to continue.
                </div>
            )}
            {workflowStatus?.current_agent && !workflowStatus.paused && (
                <div className="status-banner status-banner--info">
                    <Loader2 size={12} className="spin" />
                    {workflowStatus.current_agent} is working ({workflowStatus.sections_completed}/{workflowStatus.total_sections})
                </div>
            )}

            {/* Messages */}
            <div className="chat-messages" ref={scrollRef} onScroll={handleScroll}>
                {filteredMessages.length === 0 ? (
                    <div className="chat-empty">
                        <MessageSquare size={32} strokeWidth={1.5} />
                        <p>No messages yet</p>
                        <span>Messages will appear here when the workflow starts</span>
                    </div>
                ) : (
                    filteredMessages.map((msg) => {
                        const isUser = msg.from_agent === 'User';
                        const plainLength = (msg.message || '').replace(/\s+/g, ' ').length;
                        const lineCount = (msg.message || '').split(/\n/).length;
                        const isLong = plainLength > COLLAPSED_MAX_LENGTH || lineCount > COLLAPSED_LINES;
                        const expanded = expandedIds.has(msg.id);
                        const showExpand = isLong && !expanded;
                        const showCollapse = isLong && expanded;
                        const agentColor = AGENT_COLORS[msg.from_agent] || '#57C7E3';

                        return (
                            <div 
                                key={msg.id} 
                                className={`message-card ${isUser ? 'message-card--user' : ''}`}
                                style={{ '--agent-color': agentColor } as React.CSSProperties}
                            >
                                <AgentAvatar name={msg.from_agent} />
                                <div className="message-card__body">
                                    <div className="message-card__header">
                                        <span className="message-card__name" style={{ color: agentColor }}>
                                            {isUser ? 'You' : msg.from_agent}
                                        </span>
                                        {msg.to_agent && msg.to_agent !== 'all' && (
                                            <span className="message-card__recipient">
                                                to {msg.to_agent}
                                            </span>
                                        )}
                                        <span className="message-card__time">
                                            {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                        </span>
                                    </div>
                                    <div 
                                        className={`message-card__content ${showExpand ? 'message-card__content--collapsed' : ''}`}
                                        style={{ borderLeftColor: getTypeIndicator(msg.message_type) }}
                                    >
                                        <ReactMarkdown>{msg.message}</ReactMarkdown>
                                    </div>
                                    {(showExpand || showCollapse) && (
                                        <button
                                            type="button"
                                            className="message-card__toggle"
                                            onClick={() => toggleExpanded(msg.id)}
                                        >
                                            {showExpand ? (
                                                <>Show more <ChevronDown size={14} /></>
                                            ) : (
                                                <>Show less <ChevronUp size={14} /></>
                                            )}
                                        </button>
                                    )}
                                    {/* Preview button for section completion messages */}
                                    {msg.from_agent === 'Alex' && msg.message_type === 'success' && /Section\s+([A-M])\s/.test(msg.message) && (
                                        <button
                                            type="button"
                                            className="message-card__preview-btn"
                                            onClick={() => {
                                                const match = msg.message.match(/Section\s+([A-M])/);
                                                if (match) handlePreviewSection(match[1]);
                                            }}
                                        >
                                            <Eye size={12} /> Preview
                                        </button>
                                    )}
                                </div>
                            </div>
                        );
                    })
                )}
                <div ref={messagesEndRef} className="chat-anchor" />
            </div>

            {/* Section Preview Overlay */}
            {previewHtml && (
                <div className="section-preview-overlay">
                    <div className="section-preview-header">
                        <span className="section-preview-title">{previewTitle}</span>
                        <button type="button" className="section-preview-close" onClick={() => setPreviewHtml(null)}>
                            <X size={16} />
                        </button>
                    </div>
                    <div
                        className="section-preview-body"
                        dangerouslySetInnerHTML={{ __html: previewHtml }}
                    />
                </div>
            )}
            {previewLoading && (
                <div className="section-preview-loading">
                    <Loader2 size={16} className="spin" /> Loading preview...
                </div>
            )}

            {/* Input Area */}
            <div className="chat-input-area">
                <div className="chat-input-wrapper">
                    <input
                        ref={inputRef}
                        type="text"
                        className="chat-input"
                        placeholder="Message agents or @mention for direct questions..."
                        value={inputText}
                        onChange={handleInputChange}
                        onKeyDown={handleKeyDown}
                        aria-label="Message"
                    />
                    {showMentionDropdown && filteredAgents.length > 0 && (
                        <div className="mention-dropdown">
                            <div className="mention-dropdown__header">Mention an agent</div>
                            {filteredAgents.map((agent, idx) => (
                                <button
                                    key={agent}
                                    type="button"
                                    className={`mention-option ${idx === mentionIndex ? 'mention-option--selected' : ''}`}
                                    onClick={() => insertMention(agent)}
                                    onMouseEnter={() => setMentionIndex(idx)}
                                >
                                    <AgentAvatar name={agent} size={24} />
                                    <span>{agent}</span>
                                </button>
                            ))}
                        </div>
                    )}
                </div>
                <button
                    type="button"
                    className="btn-send"
                    onClick={handleSendMessage}
                    disabled={!inputText.trim() || isAsking}
                >
                    {isAsking ? <Loader2 size={16} className="spin" /> : <Send size={16} />}
                </button>
            </div>
        </div>
    );
};
