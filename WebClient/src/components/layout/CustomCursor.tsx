import { useEffect, useState } from 'react';

export const CustomCursor = () => {
    const [mousePos, setMousePos] = useState({ x: -100, y: -100 });
    const [isHovering, setIsHovering] = useState(false);
    const [isMouseDown, setIsMouseDown] = useState(false);
    const [isVisible, setIsVisible] = useState(false);

    useEffect(() => {
        if (typeof window === 'undefined') return;
        const media = window.matchMedia('(hover: hover) and (pointer: fine)');
        if (!media.matches) return;

        const updatePosition = (e: PointerEvent) => {
            setMousePos({ x: e.clientX, y: e.clientY });
            setIsVisible(true);

            const target = e.target as HTMLElement | null;
            const isClickable = !!target?.closest('button, a, input, select, textarea, [role="button"], .clickable');
            setIsHovering(isClickable);
        };

        const handlePointerDown = () => setIsMouseDown(true);
        const handlePointerUp = () => setIsMouseDown(false);
        const handlePointerLeave = () => setIsVisible(false);

        window.addEventListener('pointermove', updatePosition);
        window.addEventListener('pointerdown', handlePointerDown);
        window.addEventListener('pointerup', handlePointerUp);
        window.addEventListener('pointerleave', handlePointerLeave);
        document.addEventListener('mouseleave', handlePointerLeave);

        return () => {
            window.removeEventListener('pointermove', updatePosition);
            window.removeEventListener('pointerdown', handlePointerDown);
            window.removeEventListener('pointerup', handlePointerUp);
            window.removeEventListener('pointerleave', handlePointerLeave);
            document.removeEventListener('mouseleave', handlePointerLeave);
        };
    }, []);

    return (
        <div className="fixed inset-0 pointer-events-none z-[99999] overflow-hidden">
            <div
                className="absolute rounded-full border border-[var(--color-cyan-main)]/25 bg-[var(--color-cyan-main)]/8 transition-[opacity,transform] duration-150 ease-out"
                style={{
                    left: mousePos.x - 14,
                    top: mousePos.y - 14,
                    width: 28,
                    height: 28,
                    opacity: isVisible ? (isHovering ? 0.95 : 0.55) : 0,
                    transform: `scale(${isMouseDown ? 0.92 : isHovering ? 1.18 : 1})`,
                }}
            />

            <div
                className="absolute rounded-full border border-white shadow-[0_0_16px_rgba(0,188,212,0.28)] transition-[opacity,transform,background-color] duration-100 ease-out"
                style={{
                    left: mousePos.x - 5,
                    top: mousePos.y - 5,
                    width: 10,
                    height: 10,
                    opacity: isVisible ? 1 : 0,
                    transform: `scale(${isMouseDown ? 0.72 : isHovering ? 1.15 : 1})`,
                    backgroundColor: isMouseDown ? 'var(--color-yellow-main)' : 'var(--color-cyan-main)',
                }}
            />
        </div>
    );
};
