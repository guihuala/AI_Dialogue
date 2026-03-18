import { useEffect, useState, useRef } from 'react';

export const CustomCursor = () => {
    const [mousePos, setMousePos] = useState({ x: 0, y: 0 });
    const [mainPos, setMainPos] = useState({ x: 0, y: 0 });
    const [trailPos, setTrailPos] = useState({ x: 0, y: 0 });
    const [isHovering, setIsHovering] = useState(false);
    const [isMouseDown, setIsMouseDown] = useState(false);
    
    // Using refs to keep track of current mouse position for the animation loop
    const mouseRef = useRef({ x: 0, y: 0 });
    const mainRef = useRef({ x: 0, y: 0 });
    const trailRef = useRef({ x: 0, y: 0 });
    const requestRef = useRef<number>();

    useEffect(() => {
        const updatePosition = (e: MouseEvent) => {
            mouseRef.current = { x: e.clientX, y: e.clientY };
            setMousePos({ x: e.clientX, y: e.clientY });
            
            const target = e.target as HTMLElement;
            const isClickable = target.closest('button, a, input, select, textarea, [role="button"], .clickable');
            setIsHovering(!!isClickable);
        };

        const handleMouseDown = () => setIsMouseDown(true);
        const handleMouseUp = () => setIsMouseDown(false);

        window.addEventListener('mousemove', updatePosition);
        window.addEventListener('mousedown', handleMouseDown);
        window.addEventListener('mouseup', handleMouseUp);

        // Core animation loop for smooth, springy movement
        const animate = () => {
            // Main cursor follow (fast)
            const mainDistX = mouseRef.current.x - mainRef.current.x;
            const mainDistY = mouseRef.current.y - mainRef.current.y;
            mainRef.current.x += mainDistX * 0.25;
            mainRef.current.y += mainDistY * 0.25;
            setMainPos({ ...mainRef.current });

            // Trail cursor follow (slower + lag)
            const trailDistX = mainRef.current.x - trailRef.current.x;
            const trailDistY = mainRef.current.y - trailRef.current.y;
            trailRef.current.x += trailDistX * 0.15;
            trailRef.current.y += trailDistY * 0.15;
            setTrailPos({ ...trailRef.current });

            requestRef.current = requestAnimationFrame(animate);
        };

        requestRef.current = requestAnimationFrame(animate);

        return () => {
            window.removeEventListener('mousemove', updatePosition);
            window.removeEventListener('mousedown', handleMouseDown);
            window.removeEventListener('mouseup', handleMouseUp);
            if (requestRef.current) cancelAnimationFrame(requestRef.current);
        };
    }, []);

    return (
        <div className="fixed inset-0 pointer-events-none z-[99999] overflow-hidden">
            {/* 1. Outer Trail (Large, Ghostly) */}
            <div 
                className="absolute w-12 h-12 border border-[var(--color-cyan-main)]/10 rounded-full transition-opacity duration-300"
                style={{ 
                    left: trailPos.x - 24, 
                    top: trailPos.y - 24,
                    opacity: isMouseDown ? 0.6 : (isHovering ? 0.8 : 0.2),
                    transform: `scale(${isHovering ? 1.5 : 1})`
                }}
            />

            {/* 2. Secondary Active Ring */}
            <div 
                className="absolute w-8 h-8 border-2 border-[var(--color-cyan-main)]/30 rounded-full"
                style={{ 
                    left: mainPos.x - 16, 
                    top: mainPos.y - 16,
                    transform: `scale(${isMouseDown ? 1.2 : (isHovering ? 1.8 : 1)})`,
                    opacity: isMouseDown ? 1 : 0.5
                }}
            >
                {/* Micro animation for hovering */}
                <div className={`absolute -inset-1 border border-[var(--color-yellow-main)]/40 rounded-full transition-opacity duration-300 ${isHovering ? 'opacity-100 animate-ping' : 'opacity-0'}`} />
            </div>

            {/* 3. Main Cursor Core */}
            <div 
                className={`absolute w-4 h-4 rounded-full flex items-center justify-center border-2 border-white shadow-[0_0_15px_rgba(34,211,238,0.4)] transition-all duration-200 ${isMouseDown ? 'bg-[var(--color-yellow-main)] scale-75' : 'bg-[var(--color-cyan-main)]'}`}
                style={{ 
                    left: mainPos.x - 8, 
                    top: mainPos.y - 8,
                    transform: isHovering ? 'scale(1.3)' : 'scale(1)'
                }}
            >
                <div className={`w-1 h-1 rounded-full bg-white transition-all ${isHovering ? 'scale-150' : ''}`} />
            </div>

            {/* 4. Click Visual Ripple (Only on current mouse pos) */}
            <div 
                className={`absolute w-10 h-10 border-4 border-[var(--color-yellow-main)]/30 rounded-full transition-all duration-500 ease-out pointer-events-none scale-0 ${isMouseDown ? 'scale-150 opacity-0' : 'opacity-0'}`}
                style={{ 
                    left: mousePos.x - 20, 
                    top: mousePos.y - 20,
                }}
            />
        </div>
    );
};
