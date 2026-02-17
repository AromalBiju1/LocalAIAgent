'use client';

import { useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import axios from 'axios';

export default function LoginPage() {
    const { login } = useAuth();
    const [isRegister, setIsRegister] = useState(false);
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');

        const API_Base = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

        try {
            if (isRegister) {
                await axios.post(`${API_Base}/auth/register`, { username, password });
                // Auto login after register? Or just switch to login mode?
                // Let's switch to login mode for simplicity
                setIsRegister(false);
                alert('Registration successful! Please log in.');
            } else {
                const formData = new FormData();
                formData.append('username', username);
                formData.append('password', password);

                const res = await axios.post(`${API_Base}/auth/token`, formData);
                login(res.data.access_token, username);
            }
        } catch (err: any) {
            setError(err.response?.data?.detail || 'An error occurred');
        }
    };

    return (
        <div className="min-h-screen flex items-center justify-center bg-bg relative overflow-hidden">
            {/* Background Effects */}
            <div className="absolute inset-0 grid-bg opacity-30 pointer-events-none"></div>
            <div className="absolute inset-0 scanlines pointer-events-none"></div>

            <div className="w-full max-w-md p-8 bg-elyssia-surface border border-elyssia-border rounded-2xl shadow-[0_0_50px_-10px_rgba(0,0,0,0.5)] z-10 relative">

                <div className="text-center mb-8">
                    <div className="w-16 h-16 bg-elyssia-surface rounded-2xl border border-elyssia-accent/30 mx-auto mb-4 flex items-center justify-center shadow-[0_0_20px_-5px_var(--pink-accent)]">
                        <svg viewBox="0 0 24 24" fill="none" className="w-8 h-8 text-elyssia-accent" stroke="currentColor" strokeWidth="1.5">
                            <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
                        </svg>
                    </div>
                    <h1 className="text-2xl font-bold text-elyssia-text tracking-tight">
                        {isRegister ? 'Initialize Identity' : 'System Access'}
                    </h1>
                    <p className="text-sm text-elyssia-text-dim font-mono mt-2">
                        Elyssia Agent v1.0
                    </p>
                </div>

                <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                        <label className="block text-xs font-mono text-elyssia-text-dim uppercase mb-1">Username</label>
                        <input
                            type="text"
                            value={username}
                            onChange={(e) => setUsername(e.target.value)}
                            className="w-full bg-elyssia-card border border-elyssia-border rounded-lg px-4 py-2 text-elyssia-text focus:border-elyssia-accent outline-none transition-colors"
                            required
                        />
                    </div>
                    <div>
                        <label className="block text-xs font-mono text-elyssia-text-dim uppercase mb-1">Password</label>
                        <input
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            className="w-full bg-elyssia-card border border-elyssia-border rounded-lg px-4 py-2 text-elyssia-text focus:border-elyssia-accent outline-none transition-colors"
                            required
                        />
                    </div>

                    {error && (
                        <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-xs font-mono">
                            ERROR: {error}
                        </div>
                    )}

                    <button
                        type="submit"
                        className="w-full py-2.5 bg-elyssia-accent text-white rounded-lg font-medium hover:bg-elyssia-accent-dim transition-all shadow-[0_0_15px_-5px_var(--pink-accent)]"
                    >
                        {isRegister ? 'Register Identity' : 'Authenticate'}
                    </button>
                </form>

                <div className="mt-6 text-center">
                    <button
                        onClick={() => setIsRegister(!isRegister)}
                        className="text-xs text-elyssia-text-dim hover:text-elyssia-text transition-colors font-mono underline decoration-dotted"
                    >
                        {isRegister ? 'Already have an ID? Login' : 'Need access? Register'}
                    </button>
                </div>
            </div>
        </div>
    );
}
