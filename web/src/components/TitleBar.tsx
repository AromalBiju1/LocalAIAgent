'use client';

interface TitleBarProps {
    connected: boolean;
    model: string;
    onToggleSidebar: () => void;
    onToggleTools: () => void;
}

export default function TitleBar({ connected, model, onToggleSidebar, onToggleTools }: TitleBarProps) {
    return (
        <div className="h-12 bg-bg border-b border-elyssia-border flex items-center px-4 gap-4 select-none shrink-0">

            {/* Sidebar Toggle */}
            <button
                onClick={onToggleSidebar}
                className="p-1.5 text-elyssia-text-dim hover:text-elyssia-text hover:bg-elyssia-surface rounded-md transition-all"
            >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <line x1="3" y1="12" x2="21" y2="12" />
                    <line x1="3" y1="6" x2="21" y2="6" />
                    <line x1="3" y1="18" x2="21" y2="18" />
                </svg>
            </button>

            {/* Breadcrumbs */}
            <div className="flex-1 flex items-center gap-2 font-mono text-xs">
                <span className="font-bold text-elyssia-text">Elyssia</span>
                <span className="text-elyssia-border">/</span>
                <div className="flex items-center gap-1.5 bg-elyssia-surface border border-elyssia-border px-2 py-0.5 rounded text-elyssia-text">
                    <span className="w-1.5 h-1.5 rounded-full bg-[var(--pink-accent)]"></span>
                    <span>{model}</span>
                </div>
            </div>

            {/* Right Actions */}
            <div className="flex items-center gap-3">
                <button
                    onClick={onToggleTools}
                    className={`flex items-center gap-2 px-3 py-1.5 rounded-md border text-xs font-mono transition-all ${connected
                        ? 'bg-elyssia-surface border-elyssia-border text-elyssia-text hover:border-elyssia-accent'
                        : 'bg-red-500/10 border-red-500/20 text-red-400'
                        }`}
                >
                    <span>{connected ? 'System Online' : 'Offline'}</span>
                    <div className={`w-1.5 h-1.5 rounded-full ${connected ? 'bg-[#2FBF71]' : 'bg-[#E23D2D]'}`} />
                </button>
            </div>
        </div>
    );
}
