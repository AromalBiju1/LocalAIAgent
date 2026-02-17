'use client';

import { useState, useEffect } from 'react';

interface StartupSequenceProps {
    onComplete: () => void;
}

export default function StartupSequence({ onComplete }: StartupSequenceProps) {
    const [mounted, setMounted] = useState(false);
    const [progress, setProgress] = useState(0);

    useEffect(() => {
        setMounted(true);

        const timer = setInterval(() => {
            setProgress(prev => {
                if (prev >= 100) {
                    clearInterval(timer);
                    setTimeout(onComplete, 500);
                    return 100;
                }
                return prev + 2; // Smooth but quick
            });
        }, 30);

        return () => clearInterval(timer);
    }, []);

    return (
        <div className={`fixed inset-0 z-50 bg-bg flex flex-col items-center justify-center transition-opacity duration-500 ${mounted ? 'opacity-100' : 'opacity-0'}`}>

            {/* Centered content */}
            <div className="w-full max-w-sm px-8">
                <div className="flex items-center justify-between mb-4">
                    <span className="font-mono text-sm font-bold text-elyssia-text tracking-tight">Elyssia Agent</span>
                </div>

                {/* Progress Bar Container */}
                <div className="h-1.5 w-full bg-elyssia-surface rounded-full overflow-hidden">
                    {/* Orange Lobster Progress */}
                    <div
                        className="h-full bg-elyssia-accent transition-all duration-75 ease-out rounded-full"
                        style={{ width: `${progress}%` }}
                    />
                </div>

                <div className="mt-4 flex justify-between font-mono text-xs text-elyssia-muted">
                    <span>Initializing environment...</span>
                    <span>{progress}%</span>
                </div>
            </div>

            {/* Bottom Credit */}
            <div className="absolute bottom-8 text-[10px] text-elyssia-muted/50 font-mono flex items-center gap-2">
                <span className="text-[var(--pink-accent)]">◆</span>
                <span>Elyssia Core // Systems Active</span>
            </div>
        </div>
    );
}
