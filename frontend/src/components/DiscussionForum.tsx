import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import { Bot, ChevronDown, ChevronUp } from 'lucide-react';
import { api, ChatMessage } from '../api';
import './DiscussionForum.css';

const COLLAPSED_MAX_LENGTH = 280;
const COLLAPSED_LINES = 4;

interface DiscussionForumProps {
    sessionId: number;
}

export const DiscussionForum: React.FC<DiscussionForumProps> = ({ sessionId }) => {
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [inputText, setInputText] = useState('');
    const [isAutoScroll, setIsAutoScroll] = useState(true);
    const [expandedIds, setExpandedIds] = useState<Set<number>>(new Set());
    const scrollRef = useRef<HTMLDivElement>(null);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const fetchMessages = useCallback(async () => {
        try {
            const data = await api.getMessages(sessionId);
            const list = Array.isArray(data) ? data : [];
            setMessages(list.slice().reverse());
        } catch (error) {
            console.error('Failed to fetch messages:', error);
        }
    }, [sessionId]);

    const handleSendMessage = async () => {
        if (!inputText.trim()) return;
        try {
            await api.sendMessage(sessionId, inputText);
            setInputText('');
            setIsAutoScroll(true);
            fetchMessages();
        } catch (error) {
            console.error('Failed to send:', error);
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
        const interval = setInterval(fetchMessages, 2000);
        fetchMessages();
        return () => clearInterval(interval);
    }, [sessionId, fetchMessages]);

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

    return (
        <div className="discussion-container">
            <div className="discussion-header">
                <h3><Bot size={18} className="header-icon" /> Live Agent Protocol</h3>
                <div className="live-indicator">
                    <span className="pulse-dot" />
                    Live
                </div>
            </div>

            <div className="messages-list" ref={scrollRef} onScroll={handleScroll}>
                {filteredMessages.length === 0 ? (
                    <div className="empty-state">
                        <p>Initializing channel...</p>
                        <p className="empty-sub">Agents will appear here when the workflow starts.</p>
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

                        return (
                            <div
                                key={msg.id}
                                className={`message-row ${isUser ? 'message-row--user' : 'message-row--agent'}`}
                            >
                                <div
                                    className={`chat-bubble ${isUser ? 'chat-bubble--user' : 'chat-bubble--agent'}`}
                                    data-type={msg.message_type}
                                >
                                    {!isUser && (
                                        <div className="chat-bubble__label">
                                            {msg.from_agent}
                                            {msg.to_agent !== 'all' && (
                                                <span className="chat-bubble__to"> to {msg.to_agent}</span>
                                            )}
                                        </div>
                                    )}
                                    <div
                                        className={`chat-bubble__content ${showExpand ? 'chat-bubble__content--collapsed' : ''}`}
                                    >
                                        <ReactMarkdown>{msg.message}</ReactMarkdown>
                                    </div>
                                    {showExpand && (
                                        <button
                                            type="button"
                                            className="chat-bubble__expand"
                                            onClick={() => toggleExpanded(msg.id)}
                                        >
                                            <ChevronDown size={14} /> Show more
                                        </button>
                                    )}
                                    {showCollapse && (
                                        <button
                                            type="button"
                                            className="chat-bubble__expand"
                                            onClick={() => toggleExpanded(msg.id)}
                                        >
                                            <ChevronUp size={14} /> Show less
                                        </button>
                                    )}
                                    <div className="chat-bubble__time">
                                        {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                    </div>
                                </div>
                            </div>
                        );
                    })
                )}
                <div ref={messagesEndRef} className="messages-anchor" />
            </div>

            <div className="chat-input-area">
                <input
                    type="text"
                    className="chat-input"
                    placeholder="Type a message..."
                    value={inputText}
                    onChange={(e) => setInputText(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSendMessage()}
                    aria-label="Message"
                />
                <button
                    type="button"
                    className="btn-send"
                    onClick={handleSendMessage}
                    disabled={!inputText.trim()}
                >
                    Send
                </button>
            </div>
        </div>
    );
};
