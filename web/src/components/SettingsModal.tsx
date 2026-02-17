'use client';

import { useState, useEffect } from 'react';

interface Plugin {
    name: string;
    version: string;
    enabled: boolean;
    description: string;
}

interface Channel {
    name: string;
    type: string;
    status: 'active' | 'inactive' | 'error';
    config: Record<string, any>;
}

interface SettingsModalProps {
    onClose: () => void;
}

export default function SettingsModal({ onClose }: SettingsModalProps) {
    const [activeTab, setActiveTab] = useState<'plugins' | 'channels' | 'models'>('plugins');
    const [plugins, setPlugins] = useState<Plugin[]>([]);
    const [channels, setChannels] = useState<Channel[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchData();
    }, []);

    const fetchData = async () => {
        setLoading(true);
        try {
            const [pluginsRes, channelsRes] = await Promise.all([
                fetch('/api/plugins'),
                fetch('/api/channels')
            ]);

            if (pluginsRes.ok) {
                const data = await pluginsRes.json();
                // Map API response to UI model
                const mappedPlugins = (data.plugins || []).map((p: any) => ({
                    name: p.name,
                    version: p.version,
                    description: p.description,
                    enabled: p.loaded, // API uses 'loaded'
                }));
                setPlugins(mappedPlugins);
            }

            if (channelsRes.ok) {
                const data = await channelsRes.json();
                // Map API response to UI model
                // API returns: { type, name, running, has_handler }
                const mappedChannels = (data.channels || []).map((c: any) => ({
                    name: c.name,
                    type: c.type,
                    status: c.running ? 'active' : 'inactive',
                    config: {}, // Config is not exposed by API for security
                }));
                setChannels(mappedChannels);
            }
        } catch (e) {
            console.error("Failed to fetch settings", e);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm animate-fadeIn">
            <div className="w-[600px] h-[500px] bg-elyssia-surface border border-elyssia-border rounded-xl shadow-2xl flex flex-col overflow-hidden">
                {/* Header */}
                <div className="px-5 py-4 border-b border-elyssia-border flex items-center justify-between bg-elyssia-surface/50">
                    <h2 className="text-lg font-semibold text-elyssia-text flex items-center gap-2">
                        <span className="text-elyssia-accent">⚙️</span> Settings
                    </h2>
                    <button onClick={onClose} className="text-elyssia-muted hover:text-elyssia-text transition-colors">
                        ✕
                    </button>
                </div>

                {/* Tags */}
                <div className="flex border-b border-elyssia-border bg-elyssia-card/30">
                    <button
                        onClick={() => setActiveTab('plugins')}
                        className={`px-5 py-3 text-xs font-mono uppercase tracking-wider transition-colors ${activeTab === 'plugins' ? 'text-elyssia-accent border-b-2 border-elyssia-accent bg-elyssia-accent/5' : 'text-elyssia-muted hover:text-elyssia-text'
                            }`}
                    >
                        Plugins
                    </button>
                    <button
                        onClick={() => setActiveTab('channels')}
                        className={`px-5 py-3 text-xs font-mono uppercase tracking-wider transition-colors ${activeTab === 'channels' ? 'text-elyssia-accent border-b-2 border-elyssia-accent bg-elyssia-accent/5' : 'text-elyssia-muted hover:text-elyssia-text'
                            }`}
                    >
                        Channels
                    </button>
                    <button
                        onClick={() => setActiveTab('models')}
                        className={`px-5 py-3 text-xs font-mono uppercase tracking-wider transition-colors ${activeTab === 'models' ? 'text-elyssia-accent border-b-2 border-elyssia-accent bg-elyssia-accent/5' : 'text-elyssia-muted hover:text-elyssia-text'
                            }`}
                    >
                        Models
                    </button>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto p-5 bg-elyssia-bg/50">
                    {loading ? (
                        <div className="flex items-center justify-center h-full text-elyssia-muted text-sm font-mono">
                            Loading configuration...
                        </div>
                    ) : (
                        <>
                            {activeTab === 'plugins' && (
                                <div className="space-y-3">
                                    {plugins.length === 0 ? (
                                        <p className="text-elyssia-muted text-sm italic">No plugins detected.</p>
                                    ) : (
                                        plugins.map((p, i) => (
                                            <div key={i} className="p-3 bg-elyssia-card border border-elyssia-border rounded-lg flex items-start justify-between">
                                                <div>
                                                    <div className="flex items-center gap-2">
                                                        <h3 className="font-semibold text-sm text-elyssia-text">{p.name}</h3>
                                                        <span className="text-[10px] bg-elyssia-surface px-1.5 py-0.5 rounded text-elyssia-muted border border-elyssia-border">v{p.version}</span>
                                                    </div>
                                                    <p className="text-xs text-elyssia-muted mt-1">{p.description}</p>
                                                </div>
                                                <div className="flex items-center gap-2">
                                                    <div className={`w-2 h-2 rounded-full ${p.enabled ? 'bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.4)]' : 'bg-gray-500'}`} />
                                                    <span className="text-[10px] font-mono text-elyssia-muted uppercase">{p.enabled ? 'Active' : 'Disabled'}</span>
                                                </div>
                                            </div>
                                        ))
                                    )}
                                </div>
                            )}

                            {activeTab === 'channels' && (
                                <div className="space-y-3">
                                    {channels.length === 0 ? (
                                        <p className="text-elyssia-muted text-sm italic">No channels configured.</p>
                                    ) : (
                                        channels.map((c, i) => (
                                            <div key={i} className="p-3 bg-elyssia-card border border-elyssia-border rounded-lg">
                                                <div className="flex items-center justify-between mb-2">
                                                    <div className="flex items-center gap-2">
                                                        {c.type === 'telegram' && <span className="text-blue-400">✈️</span>}
                                                        {c.type === 'discord' && <span className="text-indigo-400">👾</span>}
                                                        <h3 className="font-semibold text-sm text-elyssia-text capitalize">{c.type}</h3>
                                                    </div>
                                                    <div className={`px-2 py-0.5 rounded text-[10px] font-mono uppercase border ${c.status === 'active'
                                                        ? 'bg-green-500/10 border-green-500/30 text-green-400'
                                                        : 'bg-red-500/10 border-red-500/30 text-red-400'
                                                        }`}>
                                                        {c.status}
                                                    </div>
                                                </div>
                                                <div className="text-xs text-elyssia-muted font-mono bg-black/20 p-2 rounded border border-elyssia-border/50">
                                                    {c.status === 'active' ? 'Bot Token: ••••••••' : 'Not Configured'}
                                                </div>
                                            </div>
                                        ))
                                    )}
                                </div>
                            )}

                            {activeTab === 'models' && (
                                <div className="space-y-3">
                                    <div className="p-4 bg-elyssia-card border border-elyssia-border rounded-lg">
                                        <h3 className="text-sm font-semibold text-elyssia-text mb-2">Current Provider</h3>
                                        <div className="flex items-center gap-3">
                                            <div className="px-3 py-1.5 bg-elyssia-surface border border-elyssia-border rounded text-xs font-mono text-elyssia-accent">
                                                Ollama / Local
                                            </div>
                                            <span className="text-xs text-elyssia-muted">
                                                Configuration via <code className="bg-black/30 px-1 py-0.5 rounded">config.yaml</code> only.
                                            </span>
                                        </div>
                                    </div>
                                    <p className="text-xs text-elyssia-muted/60 mt-4 text-center">
                                        To add OpenAI, Groq, or vLLM backends, edit the configuration file and restart.
                                    </p>
                                </div>
                            )}
                        </>
                    )}
                </div>

                {/* Footer */}
                <div className="p-4 border-t border-elyssia-border bg-elyssia-surface/50 text-[10px] text-elyssia-muted text-center font-mono">
                    Changes require server restart to take effect.
                </div>
            </div>
        </div>
    );
}
