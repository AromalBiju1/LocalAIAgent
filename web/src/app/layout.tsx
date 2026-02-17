import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
    title: 'ElyssiaAgent — Local AI Agent',
    description: 'Local AI Agent with tool calling, streaming, and a Linux-inspired interface.',
};

import { AuthProvider } from '@/context/AuthContext';

export default function RootLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <html lang="en">
            <body className="bg-elyssia-bg text-elyssia-text antialiased">
                <AuthProvider>
                    {children}
                </AuthProvider>
            </body>
        </html>
    );
}
