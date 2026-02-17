'use client';

import type { Model, ToolInfo } from '@/app/page';

export interface Conversation {
    id: string;
    title: string;
    updated_at: number;
}

interface SidebarProps {
    models: Model[];
    currentModel: string;
    tools: ToolInfo[];
    toolsEnabled: boolean;
    conversations: Conversation[];
    activeConversationId: string | null;
    onModelChange: (model: string) => void;
    onToolsToggle: () => void;
    onSelectConversation: (id: string) => void;
    onDeleteConversation: (id: string) => void;
    onClearChat: () => void;
    onClose: () => void;
    onOpenSettings: () => void;
}

export default function Sidebar({
    models,
    currentModel,
    tools,
    toolsEnabled,
    conversations,
    activeConversationId,
    onModelChange,
    onSelectConversation,
    onDeleteConversation,
    onClearChat,
    onOpenSettings,
}: SidebarProps) {
    return (
        <div className="w-64 bg-elyssia-surface border-r border-elyssia-border flex flex-col shrink-0">
            {/* Header */}
            <div className="p-4 border-b border-elyssia-border">
                <button
                    onClick={onClearChat}
                    className="w-full py-2 px-3 bg-elyssia-accent text-white font-semibold rounded-md shadow-sm hover:bg-[#ff7a3d] transition-colors flex items-center justify-center gap-2 text-sm"
                >
                    <span>+</span>
                    <span>New Thread</span>
                </button>
            </div>

            {/* List */}
            <div className="flex-1 overflow-y-auto px-3 py-3 space-y-1">
                <div className="px-2 mb-2 text-[10px] font-bold text-elyssia-text-dim uppercase tracking-wider">
                    Recent
                </div>
                {conversations.length > 0 ? (
                    conversations.map((conv) => (
                        <div
                            key={conv.id}
                            onClick={() => onSelectConversation(conv.id)}
                            className={`group cursor-pointer px-3 py-2 rounded-md transition-all text-sm flex items-center justify-between ${activeConversationId === conv.id
                                    ? 'bg-elyssia-card text-elyssia-text shadow-sm ring-1 ring-elyssia-border'
                                    : 'text-elyssia-text-dim hover:bg-elyssia-card/50 hover:text-elyssia-text'
                                }`}
                        >
                            <span className="truncate">{conv.title || 'Untitled'}</span>
                        </div>
                    ))
                ) : (
                    <div className="px-3 py-8 text-center border-2 border-dashed border-elyssia-border rounded-lg">
                        <span className="text-xs text-elyssia-text-dim">No threads</span>
                    </div>
                )}
            </div>

            {/* Footer */}
            <div className="p-3 border-t border-elyssia-border bg-bg/50">
                <div className="mb-3">
                    <label className="text-[10px] uppercase font-bold text-elyssia-text-dim mb-1.5 block">
                        Model
                    </label>
                    <select
                        value={currentModel}
                        onChange={(e) => onModelChange(e.target.value)}
                        className="w-full bg-elyssia-card border border-elyssia-border text-elyssia-text text-xs rounded-md px-2 py-1.5 focus:border-elyssia-accent focus:ring-1 focus:ring-elyssia-accent outline-none"
                    >
                        {models.map((m) => (
                            <option key={m.name} value={m.name}>{m.name}</option>
                        ))}
                    </select>
                </div>

                <div className="flex items-center justify-between">
                    <button onClick={onOpenSettings} className="p-1.5 text-elyssia-text-dim hover:text-elyssia-text rounded-md hover:bg-elyssia-card transition-colors">
                        Settings
                    </button>
                    <div className="w-2 h-2 rounded-full bg-elyssia-accent"></div>
                </div>
            </div>
        </div>
    );
}
