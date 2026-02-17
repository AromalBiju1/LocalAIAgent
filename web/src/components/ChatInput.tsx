'use client';

import { useState, useRef, useEffect } from 'react';

interface ChatInputProps {
    onSend: (content: string) => void;
    onStop: () => void;
    isStreaming: boolean;
    disabled: boolean;
}

export default function ChatInput({ onSend, onStop, isStreaming, disabled }: ChatInputProps) {
    const [input, setInput] = useState('');
    const textareaRef = useRef<HTMLTextAreaElement>(null);

    // Auto-resize textarea
    useEffect(() => {
        const ta = textareaRef.current;
        if (ta) {
            ta.style.height = 'auto';
            ta.style.height = `${Math.min(ta.scrollHeight, 160)}px`;
        }
    }, [input]);

    // Focus on mount
    useEffect(() => {
        textareaRef.current?.focus();
    }, []);

    const handleSubmit = () => {
        if (input.trim() && !isStreaming && !disabled) {
            onSend(input);
            setInput('');
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSubmit();
        }
    };

    return (
        <div className="border-t border-elyssia-border bg-elyssia-surface px-4 py-3 shrink-0">
            <div className="max-w-4xl mx-auto flex items-end gap-3">
                {/* Terminal prompt prefix */}
                <span className="text-elyssia-accent font-mono text-sm pb-2.5 select-none shrink-0">
                    ❯
                </span>

                {/* Textarea */}
                <div className="flex-1 relative">
                    <textarea
                        ref={textareaRef}
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder={disabled ? 'Backend offline — start with: python run.py --mode web' : 'Type a message... (Shift+Enter for newline)'}
                        disabled={disabled || isStreaming}
                        rows={1}
                        className="w-full bg-elyssia-card border border-elyssia-border rounded-xl px-4 py-2.5 text-sm
                       text-elyssia-text placeholder-elyssia-muted/50 font-mono
                       resize-none input-glow transition-all
                       disabled:opacity-40 disabled:cursor-not-allowed"
                    />
                </div>

                {/* Send / Stop button */}
                {isStreaming ? (
                    <button
                        onClick={onStop}
                        className="p-2.5 rounded-xl bg-red-500/15 border border-red-500/30 text-red-400
                       hover:bg-red-500/25 transition-all shrink-0"
                        title="Stop generating"
                    >
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                            <rect x="6" y="6" width="12" height="12" rx="2" />
                        </svg>
                    </button>
                ) : (
                    <button
                        onClick={handleSubmit}
                        disabled={!input.trim() || disabled}
                        className="p-2.5 rounded-xl bg-elyssia-accent/15 border border-elyssia-accent/30 text-elyssia-accent
                       hover:bg-elyssia-accent/25 hover:shadow-glow-sm transition-all shrink-0
                       disabled:opacity-30 disabled:cursor-not-allowed disabled:hover:shadow-none"
                        title="Send message"
                    >
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M22 2L11 13" />
                            <path d="M22 2l-7 20-4-9-9-4 20-7z" />
                        </svg>
                    </button>
                )}
            </div>

            {/* Bottom bar */}
            <div className="max-w-4xl mx-auto mt-1.5 flex items-center justify-between">
                <span className="text-[10px] text-elyssia-muted/40 font-mono">
                    enter to send · shift+enter for newline
                </span>
                {isStreaming && (
                    <span className="text-[10px] text-elyssia-accent font-mono flex items-center gap-1">
                        <span className="w-1.5 h-1.5 rounded-full bg-elyssia-accent animate-pulse" />
                        streaming...
                    </span>
                )}
            </div>
        </div>
    );
}
