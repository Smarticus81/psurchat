import React, { useState, useEffect, useRef, useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import { Bot } from 'lucide-react';
import { api, ChatMessage } from '../api';
import './DiscussionForum.css';

interface DiscussionForumProps {
    sessionId: number;
}

export const DiscussionForum: React.FC<DiscussionForumProps> = ({ sessionId }) => {
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [inputText, setInputText] = useState('');
    const [isAutoScroll, setIsAutoScroll] = useState(true);
    const scrollRef = useRef<HTMLDivElement>(null);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const fetchMessages = async () => {
        try {
            const data = await api.getMessages(sessionId);
            // The API returns messages sorted DESC (newest first). 
            // We want to display them chronologically (oldest at top), so we reverse.
            setMessages(data.reverse());
        } catch (error) {
            console.error('Failed to fetch messages:', error);
        }
    };

    const handleSendMessage = async () => {
        if (!inputText.trim()) return;
        try {
            await api.sendMessage(sessionId, inputText);
            setInputText('');
            setIsAutoScroll(true); // Snap to bottom on send
            fetchMessages();
        } catch (error) {
            console.error("Failed to send:", error);
        }
    };

    // Initial load and polling
    useEffect(() => {
        setMessages([]); // Clear previous session messages immediately
        const interval = setInterval(fetchMessages, 2000);
        fetchMessages();
        return () => clearInterval(interval);
    }, [sessionId]);

    // Auto-scroll logic
    useEffect(() => {
        if (isAutoScroll && messagesEndRef.current) {
            messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
        }
    }, [messages, isAutoScroll]);

    // Detect manual scrolling to disable auto-scroll
    const handleScroll = () => {
        if (!scrollRef.current) return;
        const { scrollTop, scrollHeight, clientHeight } = scrollRef.current;
        const isBottom = scrollHeight - scrollTop === clientHeight;
        setIsAutoScroll(isBottom);
    };

    // Filter messages for selected agent AND exclude system data dumps
    const filteredMessages = useMemo(() => {
        let msgs = messages.filter(m => m.message_type !== 'system');

        // The original fetchMessages already reverses for chronological display.
        // If the new display logic expects newest at bottom, and the API returns newest first,
        // then the initial reverse in fetchMessages might be counter-productive if we then reverse again here.
        // Let's assume the goal is to have oldest at top, newest at bottom, which means the initial reverse is correct.
        // The provided snippet has `msgs = [...msgs].reverse();` which would make it newest at top again.
        // I will remove the second reverse here to maintain chronological order (oldest at top, newest at bottom).
        // If the intent was to display newest at top, the initial reverse in fetchMessages should be removed.
        // For now, I'll keep the initial reverse and remove the second reverse here to keep chronological order.
        // If the user truly wants newest at bottom, the initial reverse in fetchMessages is correct.
        // The comment "Reverse them for display (Newest at bottom)" in the provided snippet is confusing
        // because reversing an already chronologically ordered list would put newest at top.
        // Given the original code's intent to display chronologically (oldest at top), I'll ensure that.
        // The `fetchMessages` already reverses the API data to be oldest first.
        // So, `msgs` here is already oldest first.
        // If the goal is "Newest at bottom", then `msgs` is already in the correct order for rendering.
        // The line `msgs = [...msgs].reverse();` would put newest at top.
        // I will remove that line to keep the chronological order (oldest at top, newest at bottom).
        return msgs;
    }, [messages]);

    return (
        <div className="discussion-container">
            <div className="discussion-header">
                <h3><Bot size={18} style={{ marginRight: '8px' }} />Live Agent Protocol</h3>
                <div className="live-indicator">
                    <span className="pulse-dot"></span>
                    Live Channel
                </div>
            </div>

            <div className="messages-list" ref={scrollRef} onScroll={handleScroll}>
                {filteredMessages.length === 0 ? (
                    <div className="empty-state">
                        <p>Initializing secure channel...</p>
                        <p style={{ fontSize: '0.8rem', opacity: 0.6 }}>Waiting for agent handshake.</p>
                    </div>
                ) : (
                    filteredMessages.map((msg) => (
                        <div key={msg.id} className={`message-bubble ${msg.from_agent === 'System' ? 'system-msg' : ''} ${msg.from_agent === 'Alex' ? 'orchestrator-msg' : ''}`}>
                            <div className="message-header">
                                <span className="agent-name">{msg.from_agent}</span>
                                <span className="timestamp">{msg.to_agent !== 'all' && <span className="recipient">➜ {msg.to_agent}</span>}</span>
                            </div>
                            <div className="message-content">
                                <ReactMarkdown>{msg.message}</ReactMarkdown>
                            </div>
                            <div className="message-footer">
                                {new Date(msg.timestamp).toLocaleTimeString()}
                            </div>
                        </div>
                    ))
                )}
                <div ref={messagesEndRef} />
            </div>

            <div className="input-area chat-input-area">
                <input
                    type="text"
                    className="chat-input"
                    placeholder="Type a message to intervene in the agent workflow..."
                    value={inputText}
                    onChange={(e) => setInputText(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSendMessage()}
                    aria-label="Intervention message"
                />
                <button type="button" className="btn-send" onClick={handleSendMessage} disabled={!inputText.trim()}>
                    Send
                </button>
            </div>
        </div>
    );
};
