'use client';

import { createContext, useContext, useEffect, useState } from 'react';
import axios from 'axios';
import { useRouter, usePathname } from 'next/navigation';

interface User {
    username: string;
}

interface AuthContextType {
    user: User | null;
    login: (token: string, username: string) => void;
    logout: () => void;
    loading: boolean;
}

const AuthContext = createContext<AuthContextType>({
    user: null,
    login: () => { },
    logout: () => { },
    loading: true,
});

const API_Base = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export function AuthProvider({ children }: { children: React.ReactNode }) {
    const [user, setUser] = useState<User | null>(null);
    const [loading, setLoading] = useState(true);
    const router = useRouter();
    const pathname = usePathname();

    useEffect(() => {
        // Hydrate from localStorage
        const token = localStorage.getItem('access_token');
        const username = localStorage.getItem('username');

        if (token && username) {
            setUser({ username });
            axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
        }
        setLoading(false);
    }, []);

    useEffect(() => {
        // Protect routes
        if (!loading && !user && pathname !== '/login' && pathname !== '/register') {
            router.push('/login');
        }
    }, [user, loading, pathname, router]);

    const login = (token: string, username: string) => {
        localStorage.setItem('access_token', token);
        localStorage.setItem('username', username);
        axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
        setUser({ username });
        router.push('/');
    };

    const logout = () => {
        localStorage.removeItem('access_token');
        localStorage.removeItem('username');
        delete axios.defaults.headers.common['Authorization'];
        setUser(null);
        router.push('/login');
    };

    return (
        <AuthContext.Provider value={{ user, login, logout, loading }}>
            {children}
        </AuthContext.Provider>
    );
}

export const useAuth = () => useContext(AuthContext);
