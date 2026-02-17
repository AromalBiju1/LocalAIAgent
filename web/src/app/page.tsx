'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import axios from 'axios';
import Sidebar, { Conversation } from '@/components/Sidebar';
import ChatWindow from '@/components/ChatWindow';
import ChatInput from '@/components/ChatInput';
import ToolPanel from '@/components/ToolPanel';
import TitleBar from '@/components/TitleBar';
import StartupSequence from '@/components/StartupSequence'; // [NEW]

import SettingsModal from '@/components/SettingsModal';

export interface ChatMessage {
    id: string;
    role: 'user' | 'assistant' | 'system' | 'tool';
    content: string;
    timestamp: Date;
    isStreaming?: boolean;
    toolCalls?: ToolCall[];
    thinking?: string;
}

export interface ToolCall {
    name: string;
    arguments: Record<string, any>;
    result?: string;
    status: 'pending' | 'running' | 'done' | 'error';
}

export interface Model {
    name: string;
    available: boolean;
}

export interface ToolInfo {
    name: string;
    description: string;
    parameters: Record<string, any>;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';

export default function Home() {
    const [showStartup, setShowStartup] = useState(true); // [NEW] Control startup sequence

    // Core logic state
    const [conversationId, setConversationId] = useState<string | null>(null);
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [isStreaming, setIsStreaming] = useState(false);
    const [models, setModels] = useState<Model[]>([]);
    const [tools, setTools] = useState<ToolInfo[]>([]);
    const [conversations, setConversations] = useState<Conversation[]>([]);
    const [currentModel, setCurrentModel] = useState('qwen3:4b');
    const [toolsEnabled, setToolsEnabled] = useState(true);
    const [sidebarOpen, setSidebarOpen] = useState(true);
    const [toolPanelOpen, setToolPanelOpen] = useState(false);
    const [settingsOpen, setSettingsOpen] = useState(false);
    const [activeToolCalls, setActiveToolCalls] = useState<ToolCall[]>([]);
    const [connected, setConnected] = useState(false);
    const abortRef = useRef<AbortController | null>(null);

    // Fetch initial data on mount
    useEffect(() => {
        // [MODIFIED] Check if we've already shown startup in this session (optional, but requested to "make it more futuristic" so maybe always show it or check session storage)
        const hasBooted = sessionStorage.getItem('elyssia_booted');
        if (hasBooted) {
            setShowStartup(false);
        }

        fetchModels();
        fetchTools();
        checkHealth();
        fetchConversations();

        // Polling for health check (auto-reconnect)
        const interval = setInterval(() => {
            checkHealth();
        }, 5000);

        // Check URL for conversation ID
        if (typeof window !== 'undefined') {
            const params = new URLSearchParams(window.location.search);
            const chatId = params.get('chat');
            if (chatId) {
                setConversationId(chatId);
                loadHistory(chatId);
            }
        }

        return () => clearInterval(interval);
    }, []);

    const handleStartupComplete = () => {
        setShowStartup(false);
        sessionStorage.setItem('elyssia_booted', 'true');
    };

    const fetchConversations = async () => {
        try {
            const res = await axios.get(`${API_BASE}/api/memory/conversations`);
            setConversations(res.data);
        } catch (e) {
            console.error("Failed to load conversations", e);
        }
    };

    const loadHistory = async (id: string, updateUrl = false) => {
        try {
            const res = await axios.get(`${API_BASE}/api/memory/conversations/${id}`);
            const data = res.data;
            const history: ChatMessage[] = data.messages.map((m: any) => ({
                id: m.id,
                role: m.role,
                content: m.content,
                timestamp: new Date(m.timestamp * 1000), // generic timestamp conversion
            }));
            // Filter out system messages if desired, or keep them
            setMessages(history.filter(m => m.role !== 'system'));
            setConversationId(id);

            if (updateUrl && typeof window !== 'undefined') {
                window.history.pushState({}, '', `?chat=${id}`);
            }
        } catch (e) {
            console.error("Failed to load history", e);
        }
    };

    const deleteConversation = async (id: string) => {
        if (!confirm('Are you sure you want to delete this chat?')) return;

        try {
            await axios.delete(`${API_BASE}/api/memory/conversations/${id}`);
            setConversations(prev => prev.filter(c => c.id !== id));
            if (conversationId === id) {
                clearChat();
            }

        } catch (e) {
            console.error("Failed to delete conversation", e);
        }
    };

    const checkHealth = async () => {
        try {
            const res = await axios.get(`${API_BASE}/api/health`);
            setConnected(true);
            setCurrentModel(res.data.model);
        } catch {
            setConnected(false);
        }
    };

    const fetchModels = async () => {
        try {
            const res = await axios.get(`${API_BASE}/api/models`);
            setModels(res.data);
        } catch { }
    };

    const fetchTools = async () => {
        try {
            const res = await axios.get(`${API_BASE}/api/tools`);
            setTools(res.data);
        } catch { }
    };

    const sendMessage = useCallback(async (content: string) => {
        if (!content.trim() || isStreaming) return;

        // Ensure we have a conversation ID
        let activeChatId = conversationId;
        if (!activeChatId) {
            try {
                const res = await axios.post(`${API_BASE}/api/memory/conversations`, {
                    title: content.slice(0, 30)
                });

                activeChatId = res.data.id;
                setConversationId(activeChatId);
                window.history.pushState({}, '', `?chat=${activeChatId}`);
                // Refresh list to show new chat
                fetchConversations();
            } catch (e) {
                console.error("Failed to create conversation", e);
            }
        }

        const userMsg: ChatMessage = {
            id: crypto.randomUUID(),
            role: 'user',
            content: content.trim(),
            timestamp: new Date(),
        };

        const assistantMsg: ChatMessage = {
            id: crypto.randomUUID(),
            role: 'assistant',
            content: '',
            timestamp: new Date(),
            isStreaming: true,
        };

        setMessages(prev => [...prev, userMsg, assistantMsg]);
        setIsStreaming(true);

        const allMessages = [...messages, userMsg].map(m => ({
            role: m.role,
            content: m.content,
        }));

        try {
            abortRef.current = new AbortController();

            const res = await fetch(`${API_BASE}/api/chat/stream`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    messages: allMessages,
                    stream: true,
                    tools_enabled: toolsEnabled,
                    conversation_id: activeChatId, // Send ID for persistence
                }),
                signal: abortRef.current.signal,
            });

            if (!res.ok) throw new Error(`HTTP ${res.status}`);

            const reader = res.body?.getReader();
            const decoder = new TextDecoder();

            if (!reader) throw new Error('No response body');

            let fullContent = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const text = decoder.decode(value, { stream: true });
                const lines = text.split('\n');

                for (const line of lines) {
                    if (!line.startsWith('data: ')) continue;
                    const payload = line.slice(6).trim();
                    if (payload === '[DONE]') break;

                    try {
                        const event = JSON.parse(payload);

                        if (event.event === 'thinking') {
                            setMessages(prev =>
                                prev.map(m =>
                                    m.id === assistantMsg.id
                                        ? { ...m, thinking: (m.thinking || '') + event.content }
                                        : m
                                )
                            );
                        }

                        if (event.event === 'token') {
                            fullContent += event.content;
                            setMessages(prev =>
                                prev.map(m =>
                                    m.id === assistantMsg.id
                                        ? { ...m, content: fullContent, isStreaming: !event.done }
                                        : m
                                )
                            );
                        }

                        if (event.event === 'tool_call') {
                            let args: Record<string, any> = {};
                            try { args = JSON.parse(event.content || '{}'); } catch { }
                            const tc: ToolCall = {
                                name: event.tool_name || '',
                                arguments: args,
                                status: 'running',
                            };
                            setActiveToolCalls(prev => [...prev, tc]);
                            setToolPanelOpen(true);
                        }

                        if (event.event === 'tool_result') {
                            setActiveToolCalls(prev =>
                                prev.map(tc =>
                                    tc.name === event.tool_name && tc.status === 'running'
                                        ? { ...tc, result: event.tool_result, status: 'done' as const }
                                        : tc
                                )
                            );
                        }

                        if (event.event === 'error') {
                            fullContent += `\n\n⚠️ Error: ${event.content}`;
                            setMessages(prev =>
                                prev.map(m =>
                                    m.id === assistantMsg.id
                                        ? { ...m, content: fullContent, isStreaming: false }
                                        : m
                                )
                            );
                        }
                    } catch { }
                }
            }

            // Finalize
            setMessages(prev =>
                prev.map(m =>
                    m.id === assistantMsg.id
                        ? { ...m, isStreaming: false }
                        : m
                )
            );

            // Re-fetch conversations to update timestamp/order
            fetchConversations();

        } catch (err: any) {
            if (err.name !== 'AbortError') {
                setMessages(prev =>
                    prev.map(m =>
                        m.id === assistantMsg.id
                            ? {
                                ...m,
                                content: `⚠️ Connection error: ${err.message}. Make sure the backend is running on ${API_BASE}`,
                                isStreaming: false,
                            }
                            : m
                    )
                );
            }
        } finally {
            setIsStreaming(false);
            abortRef.current = null;
        }
    }, [messages, isStreaming, toolsEnabled, conversationId]);

    const stopStreaming = () => {
        abortRef.current?.abort();
        setIsStreaming(false);
    };

    const clearChat = () => {
        setMessages([]);
        setActiveToolCalls([]);
        setConversationId(null);
        if (typeof window !== 'undefined') {
            window.history.pushState({}, '', '/');
        }
    };

    return (
        <div className="h-screen flex flex-col overflow-hidden bg-bg relative">
            {/* Startup Overlay */}
            {showStartup && <StartupSequence onComplete={handleStartupComplete} />}

            {/* Ambient Background Elements */}
            <div className="absolute inset-0 grid-bg opacity-30 pointer-events-none"></div>
            <div className="absolute inset-0 scanlines pointer-events-none"></div>

            {/* Main Interface */}
            <div className={`flex flex-col h-full z-10 transition-opacity duration-1000 ${showStartup ? 'opacity-0' : 'opacity-100'}`}>

                {/* Title Bar */}
                <TitleBar
                    connected={connected}
                    model={currentModel}
                    onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
                    onToggleTools={() => setToolPanelOpen(!toolPanelOpen)}
                />

                {/* Main Content */}
                <div className="flex flex-1 overflow-hidden relative">
                    {/* Sidebar */}
                    {sidebarOpen && (
                        <Sidebar
                            models={models}
                            currentModel={currentModel}
                            tools={tools}
                            toolsEnabled={toolsEnabled}
                            conversations={conversations}
                            activeConversationId={conversationId}
                            onModelChange={setCurrentModel}
                            onToolsToggle={() => setToolsEnabled(!toolsEnabled)}
                            onSelectConversation={(id) => loadHistory(id, true)}
                            onDeleteConversation={deleteConversation}
                            onClearChat={clearChat}
                            onClose={() => setSidebarOpen(false)}
                            onOpenSettings={() => setSettingsOpen(true)}
                        />
                    )}

                    {/* Settings Modal */}
                    {settingsOpen && <SettingsModal onClose={() => setSettingsOpen(false)} />}

                    {/* Chat Area */}
                    <div className="flex-1 flex flex-col min-w-0 bg-bg/50 backdrop-blur-sm relative">
                        <ChatWindow messages={messages} isStreaming={isStreaming} />
                        <ChatInput
                            onSend={sendMessage}
                            onStop={stopStreaming}
                            isStreaming={isStreaming}
                            disabled={!connected}
                        />
                    </div>

                    {/* Tool Panel */}
                    {toolPanelOpen && (
                        <ToolPanel
                            toolCalls={activeToolCalls}
                            tools={tools}
                            onClose={() => setToolPanelOpen(false)}
                        />
                    )}
                </div>
            </div>
        </div>
    );
}

