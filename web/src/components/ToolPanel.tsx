'use client';

import type { ToolCall, ToolInfo } from '@/app/page';

interface ToolPanelProps {
    toolCalls: ToolCall[];
    tools: ToolInfo[];
    onClose: () => void;
}

export default function ToolPanel({ toolCalls, tools, onClose }: ToolPanelProps) {
    return (
        <div className="w-80 bg-elyssia-surface border-l border-elyssia-border flex flex-col shrink-0 overflow-hidden animate-fadeIn">
            {/* Header */}
            <div className="px-4 py-3 border-b border-elyssia-border flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-elyssia-accent">
                        <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" />
                    </svg>
                    <span className="font-semibold text-sm">Tool Activity</span>
                </div>
                <button
                    onClick={onClose}
                    className="p-1 hover:bg-elyssia-hover rounded text-elyssia-muted hover:text-elyssia-text transition-colors"
                >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M18 6L6 18M6 6l12 12" />
                    </svg>
                </button>
            </div>

            {/* Tool calls history */}
            <div className="flex-1 overflow-y-auto px-3 py-3 space-y-3">
                {toolCalls.length === 0 ? (
                    <div className="text-center py-12">
                        <div className="text-3xl mb-3 opacity-30">⚡</div>
                        <p className="text-xs text-elyssia-muted font-mono">
                            No tool calls yet.
                            <br />
                            Ask me to search, calculate, or run code.
                        </p>
                    </div>
                ) : (
                    toolCalls.map((tc, i) => (
                        <div key={i} className="tool-card rounded-xl p-3 animate-slideUp">
                            {/* Tool name + status */}
                            <div className="flex items-center justify-between mb-2">
                                <div className="flex items-center gap-2">
                                    <span className="text-elyssia-accent font-mono text-xs font-semibold">
                                        {getToolIcon(tc.name)} {tc.name}
                                    </span>
                                </div>
                                <span className={`px-2 py-0.5 rounded-full text-[10px] font-mono ${tc.status === 'done'
                                        ? 'bg-green-500/15 text-green-400 border border-green-500/20'
                                        : tc.status === 'running'
                                            ? 'bg-yellow-500/15 text-yellow-400 border border-yellow-500/20 animate-pulse'
                                            : tc.status === 'error'
                                                ? 'bg-red-500/15 text-red-400 border border-red-500/20'
                                                : 'bg-elyssia-border text-elyssia-muted border border-elyssia-border'
                                    }`}>
                                    {tc.status}
                                </span>
                            </div>

                            {/* Arguments */}
                            {Object.keys(tc.arguments).length > 0 && (
                                <div className="mb-2">
                                    <div className="text-[10px] text-elyssia-muted font-mono mb-0.5">Input:</div>
                                    <pre className="text-[11px] text-elyssia-text/70 bg-elyssia-bg rounded-lg p-2 overflow-x-auto font-mono">
                                        {JSON.stringify(tc.arguments, null, 2)}
                                    </pre>
                                </div>
                            )}

                            {/* Result */}
                            {tc.result && (
                                <div>
                                    <div className="text-[10px] text-elyssia-muted font-mono mb-0.5">Output:</div>
                                    <pre className="text-[11px] text-elyssia-text/70 bg-elyssia-bg rounded-lg p-2 overflow-x-auto font-mono max-h-32 overflow-y-auto">
                                        {tc.result}
                                    </pre>
                                </div>
                            )}
                        </div>
                    ))
                )}
            </div>

            {/* Registered tools footer */}
            <div className="border-t border-elyssia-border px-3 py-2">
                <div className="text-[10px] text-elyssia-muted/40 font-mono">
                    {tools.length} tools registered · {toolCalls.length} calls made
                </div>
            </div>
        </div>
    );
}

function getToolIcon(name: string): string {
    switch (name) {
        case 'web_search': return '🔍';
        case 'calculator': return '🧮';
        case 'python_execute': return '🐍';
        default: return '⚡';
    }
}
