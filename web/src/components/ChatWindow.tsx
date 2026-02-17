'use client';

import { useRef, useEffect, useState } from 'react';
import type { ChatMessage } from '@/app/page';

interface ChatWindowProps {
    messages: ChatMessage[];
    isStreaming: boolean;
}

export default function ChatWindow({ messages, isStreaming }: ChatWindowProps) {
    const bottomRef = useRef<HTMLDivElement>(null);
    const containerRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    if (messages.length === 0) {
        return (
            <div className="flex-1 flex flex-col items-center justify-center p-8 bg-dots">
                <div className="w-full max-w-xl text-center">
                    <div className="w-16 h-16 bg-elyssia-surface rounded-2xl border border-elyssia-border mx-auto mb-6 flex items-center justify-center shadow-[0_0_30px_-5px_var(--pink-glow)] group">
                        <svg viewBox="0 0 24 24" fill="none" className="w-8 h-8 text-[var(--pink-accent)] drop-shadow-[0_0_8px_rgba(236,72,153,0.5)]" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                            {/* Central Core */}
                            <path d="M12 8l3 3-3 3-3-3 3-3z" fill="currentColor" fillOpacity="0.8" />
                            {/* Left Wing */}
                            <path d="M9 11l-4-4c-1.5-1.5-3 0-3 2s2 4 4 5" opacity="0.7" />
                            <path d="M5 14c-2 1-3 3-1 4 2 1 4-1 5-3" opacity="0.5" />
                            {/* Right Wing */}
                            <path d="M15 11l4-4c1.5-1.5 3 0 3 2s-2 4-4 5" opacity="0.7" />
                            <path d="M19 14c2 1 3 3 1 4-2 1-4-1-5-3" opacity="0.5" />
                        </svg>
                    </div>

                    <h2 className="text-2xl font-bold text-elyssia-text mb-3 tracking-tight">
                        <span style={{ color: 'var(--pink-accent)' }}>Elyssia</span>
                    </h2>
                    <p className="text-elyssia-text-dim mb-8 text-sm font-mono">
                        Advanced Agentic Framework.
                    </p>

                    <div className="grid grid-cols-2 gap-3 text-left">
                        <QuickAction icon="⚡" label="Quick Analysis" />
                        <QuickAction icon="🛠️" label="Scaffold Project" />
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div ref={containerRef} className="flex-1 overflow-y-auto px-4 py-8 space-y-10">
            {messages.map((msg) => (
                <MessageBubble key={msg.id} message={msg} />
            ))}
            <div ref={bottomRef} />
        </div>
    );
}

function QuickAction({ icon, label }: { icon: string, label: string }) {
    return (
        <button className="p-3 bg-elyssia-surface border border-elyssia-border rounded-lg hover:border-elyssia-accent hover:bg-elyssia-surface/80 transition-all flex items-center gap-3 group">
            <span className="text-lg group-hover:scale-110 transition-transform">{icon}</span>
            <span className="text-sm font-medium text-elyssia-text font-mono">{label}</span>
        </button>
    )
}

function ThinkingDropdown({ thinking, isStreaming }: { thinking: string; isStreaming: boolean }) {
    const [isOpen, setIsOpen] = useState(false);

    if (!thinking) return null;

    return (
        <div className="mb-3">
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="flex items-center gap-2 px-3 py-1.5 bg-elyssia-surface border border-elyssia-border rounded-md hover:border-elyssia-accent-dim transition-colors"
            >
                <div className={`w-2 h-2 rounded-full ${isStreaming ? 'bg-elyssia-accent animate-pulse' : 'bg-elyssia-text-dim'}`} />
                <span className="font-mono text-xs text-elyssia-text-dim font-medium uppercase tracking-wide">
                    {isStreaming ? 'Processing' : 'Thought Process'}
                </span>
                <span className={`text-elyssia-text-dim text-[10px] transition-transform ${isOpen ? 'rotate-180' : ''}`}>▼</span>
            </button>
            {isOpen && (
                <div className="mt-2 p-4 bg-elyssia-card border border-elyssia-border rounded-lg text-xs font-mono text-elyssia-text-dim leading-relaxed shadow-sm">
                    {thinking}
                </div>
            )}
        </div>
    );
}

function MessageBubble({ message }: { message: ChatMessage }) {
    const isUser = message.role === 'user';

    return (
        <div className={`flex gap-5 max-w-3xl mx-auto w-full group ${isUser ? 'flex-row-reverse' : ''}`}>

            {/* Avatar */}
            <div className={`w-8 h-8 rounded-lg shrink-0 flex items-center justify-center font-bold text-xs shadow-sm overflow-hidden
                ${isUser ? 'bg-elyssia-surface border border-elyssia-border text-elyssia-text' : 'bg-elyssia-surface border border-elyssia-accent/30 text-elyssia-accent shadow-[0_0_10px_-3px_var(--pink-accent)]'}`}>
                {isUser ? 'U' : (
                    <svg viewBox="0 0 24 24" fill="none" className="w-5 h-5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M12 8l3 3-3 3-3-3 3-3z" fill="currentColor" fillOpacity="0.8" />
                        <path d="M9 11l-4-4c-1.5-1.5-3 0-3 2s2 4 4 5" opacity="0.7" />
                        <path d="M5 14c-2 1-3 3-1 4 2 1 4-1 5-3" opacity="0.5" />
                        <path d="M15 11l4-4c1.5-1.5 3 0 3 2s-2 4-4 5" opacity="0.7" />
                        <path d="M19 14c2 1 3 3 1 4-2 1-4-1-5-3" opacity="0.5" />
                    </svg>
                )}
            </div>

            <div className={`flex flex-col min-w-0 max-w-[85%] ${isUser ? 'items-end' : 'items-start'}`}>

                {/* Meta */}
                <div className="flex items-center gap-2 mb-2">
                    <span className="text-sm font-semibold text-elyssia-text">
                        {isUser ? 'You' : 'Elyssia'}
                    </span>
                    <span className="text-xs text-elyssia-text-dim font-mono">
                        {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                </div>

                {/* Assistant Thinking */}
                {!isUser && message.thinking && (
                    <ThinkingDropdown
                        thinking={message.thinking}
                        isStreaming={!!message.isStreaming && !message.content}
                    />
                )}

                {/* Content */}
                <div className={`prose prose-invert prose-sm max-w-none leading-7 ${isUser ? 'text-right' : ''}`}>
                    <div className="markdown-body">
                        {message.content}
                        {message.isStreaming && (
                            <span className="inline-flex items-center gap-1.5 ml-2 text-xs font-mono text-elyssia-accent animate-pulse">
                                <span className="w-1.5 h-1.5 rounded-full bg-elyssia-accent"></span>
                                Elyssia is thinking...
                            </span>
                        )}
                    </div>
                </div>

                {/* Tool Calls - The "Lobster" Look */}
                {message.toolCalls && message.toolCalls.length > 0 && (
                    <div className="mt-4 w-full">
                        {message.toolCalls.map((tc, i) => (
                            <div key={i} className="mb-2 p-3 rounded-lg bg-elyssia-surface border border-elyssia-border flex items-center justify-between font-mono text-xs hover:border-elyssia-accent/50 transition-colors">
                                <div className="flex items-center gap-2.5">
                                    <span className="text-elyssia-accent">λ</span>
                                    <span className="text-elyssia-text">{tc.name}</span>
                                </div>
                                <div className="flex items-center gap-2">
                                    <span className={`w-1.5 h-1.5 rounded-full ${tc.status === 'done' ? 'bg-[#2FBF71]' : // Mint
                                        tc.status === 'error' ? 'bg-[#E23D2D]' : // Red
                                            'bg-[#FFB020]' // Amber
                                        }`} />
                                    <span className="text-elyssia-text-dim uppercase tracking-wider text-[10px]">{tc.status}</span>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
