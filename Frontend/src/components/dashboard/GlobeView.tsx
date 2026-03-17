import { useEffect, useRef, useState, useCallback } from "react";
import { Maximize2, RotateCcw } from "lucide-react";

const GlobeView = ({ arcs }: { arcs: any[] }) => {
    const globeRef = useRef<any>(null);
    const containerRef = useRef<HTMLDivElement>(null);
    const [Globe, setGlobe] = useState<any>(null);
    const [dimensions, setDimensions] = useState({ width: 0, height: 0 });
    const [isFocused, setIsFocused] = useState(false);

    useEffect(() => {
        import("react-globe.gl").then((mod: { default: any }) => {
            setGlobe(() => mod.default);
        });
    }, []);

    useEffect(() => {
        if (!containerRef.current) return;
        const obs = new ResizeObserver((entries) => {
            const { width, height } = entries[0].contentRect;
            setDimensions({ width, height });
        });
        obs.observe(containerRef.current);
        return () => obs.disconnect();
    }, []);

    const resetView = useCallback(() => {
        if (globeRef.current) {
            globeRef.current.pointOfView({ lat: 20, lng: 100, altitude: 2.5 }, 1000);
            setIsFocused(false);
            
            const controls = globeRef.current.controls();
            if (controls) {
                controls.autoRotate = true;
            }
        }
    }, []);

    useEffect(() => {
        if (globeRef.current && Globe) {
            const controls = globeRef.current.controls();
            if (controls) {
                controls.autoRotate = true;
                controls.autoRotateSpeed = 0.4;
                controls.enableZoom = true;
            }
            resetView();
        }
    }, [Globe, resetView]);

    const handleArcClick = (arc: any) => {
        if (globeRef.current) {
            // Focus on the origin (source country)
            globeRef.current.pointOfView({ 
                lat: arc.startLat, 
                lng: arc.startLng, 
                altitude: 0.8 
            }, 1000);
            
            setIsFocused(true);
            
            // Disable auto-rotate when focused
            const controls = globeRef.current.controls();
            if (controls) {
                controls.autoRotate = false;
            }
        }
    };

    const arcsData = arcs.length > 0 ? arcs : [];

    // Derive points from arcs to show origins and destination (USA)
    const pointsData = arcs.flatMap((arc: any) => [
        { 
            lat: arc.startLat, 
            lng: arc.startLng, 
            color: arc.color, 
            size: arc.riskLevel === 'high' ? 0.6 : 0.3, 
            label: arc.label.split(': ')[1]?.split(' → ')[0],
            arcData: arc
        },
        { 
            lat: arc.endLat, 
            lng: arc.endLng, 
            color: arc.color, 
            size: 0.1, 
            label: "USA",
            arcData: arc
        },
    ]);

    const criticalCount = arcs.filter(a => a.riskLevel === 'high').length;

    if (!Globe) {
        return (
            <div ref={containerRef} className="w-full h-full flex items-center justify-center">
                <span className="text-[10px] font-mono text-agent-active animate-pulse">Initializing spatial view...</span>
            </div>
        );
    }

    return (
        <div ref={containerRef} className="w-full h-full relative overflow-hidden">
            <Globe
                ref={globeRef}
                width={dimensions.width || 600}
                height={dimensions.height || 400}
                globeImageUrl="//unpkg.com/three-globe/example/img/earth-night.jpg"
                backgroundColor="rgba(0,0,0,0)"
                arcsData={arcsData}
                arcColor="color"
                arcStroke={0.8}
                arcDashLength={0.5}
                arcDashGap={0.5}
                arcDashAnimateTime={2000}
                arcLabel="label"
                onArcClick={handleArcClick}
                pointsData={pointsData}
                pointLat="lat"
                pointLng="lng"
                pointColor="color"
                pointAltitude={0.01}
                pointRadius="size"
                pointLabel="label"
                onPointClick={(point: any) => handleArcClick(point.arcData)}
                atmosphereColor="hsl(217, 91%, 60%)"
                atmosphereAltitude={0.15}
            />
            
            {/* Header overlay */}
            <div className="absolute top-4 left-4 right-4 flex items-start justify-between pointer-events-none">
                <div className="flex flex-col gap-2">
                    <div>
                        <h2 className="text-sm font-medium text-foreground">Global Supply Network</h2>
                        <p className="text-[10px] font-mono text-muted-foreground mt-0.5">
                            {arcs.length} active routes · {criticalCount} critical alerts
                        </p>
                    </div>
                </div>
                
                <div className="flex flex-col items-end gap-3">
                    <div className="flex gap-3 pointer-events-auto bg-background/40 backdrop-blur-md p-2 rounded-lg border border-secondary/20">
                        {[
                            { color: 'bg-risk-high', label: 'Critical' },
                            { color: 'bg-risk-mid', label: 'Warning' },
                            { color: 'bg-risk-low', label: 'Nominal' },
                        ].map((l) => (
                            <div key={l.label} className="flex items-center gap-1.5">
                                <div className={`w-2 h-2 rounded-full ${l.color}`} />
                                <span className="text-[9px] text-muted-foreground">{l.label}</span>
                            </div>
                        ))}
                    </div>

                    <div className="flex gap-2 pointer-events-auto">
                        {isFocused && (
                            <button 
                                onClick={resetView}
                                className="flex items-center gap-1.5 px-2 py-1 bg-secondary/20 hover:bg-secondary/40 border border-secondary/40 rounded-md text-[9px] text-foreground transition-all animate-in fade-in zoom-in duration-200"
                            >
                                <RotateCcw size={10} />
                                Reset View
                            </button>
                        )}
                        <div className="px-2 py-1 bg-secondary/10 border border-secondary/20 rounded-md text-[9px] text-muted-foreground flex items-center gap-1.5">
                            <Maximize2 size={10} />
                            Interactive Mode
                        </div>
                    </div>
                </div>
            </div>
            
            {/* Interaction Toast */}
            {!isFocused && arcs.length > 0 && (
                <div className="absolute bottom-4 left-1/2 -translate-x-1/2 px-3 py-1.5 bg-background/60 backdrop-blur-md border border-secondary/20 rounded-full pointer-events-none animate-bounce-subtle">
                    <span className="text-[9px] text-muted-foreground font-mono">Click a vector line to focus source region</span>
                </div>
            )}
        </div>
    );
};

export default GlobeView;
