import { useEffect, useRef, useState } from "react";
import { supplyRoutes } from "@/data/simulatedData";

const GlobeView = ({ arcs }: { arcs: any[] }) => {
    const globeRef = useRef<any>(null);
    const containerRef = useRef<HTMLDivElement>(null);
    const [Globe, setGlobe] = useState<any>(null);
    const [dimensions, setDimensions] = useState({ width: 0, height: 0 });

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

    useEffect(() => {
        if (globeRef.current) {
            const controls = globeRef.current.controls();
            if (controls) {
                controls.autoRotate = true;
                controls.autoRotateSpeed = 0.4;
                controls.enableZoom = true;
            }
            globeRef.current.pointOfView({ lat: 20, lng: 100, altitude: 2.5 }, 1000);
        }
    }, [Globe]);

    const arcsData = arcs.length > 0 ? arcs : [];

    const pointsData = supplyRoutes.flatMap((r: any) => [
        { lat: r.startLat, lng: r.startLng, color: r.color, size: r.riskLevel === 'high' ? 0.6 : 0.3, label: r.label.split(' → ')[0] },
        { lat: r.endLat, lng: r.endLng, color: r.color, size: r.riskLevel === 'high' ? 0.6 : 0.3, label: r.label.split(' → ')[1] },
    ]);

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
                pointsData={pointsData}
                pointLat="lat"
                pointLng="lng"
                pointColor="color"
                pointAltitude={0.01}
                pointRadius="size"
                pointLabel="label"
                atmosphereColor="hsl(217, 91%, 60%)"
                atmosphereAltitude={0.15}
            />
            {/* Header overlay */}
            <div className="absolute top-4 left-4 right-4 flex items-start justify-between pointer-events-none">
                <div>
                    <h2 className="text-sm font-medium text-foreground">Global Supply Network</h2>
                    <p className="text-[10px] font-mono text-muted-foreground mt-0.5">6 active routes · 2 critical alerts</p>
                </div>
                <div className="flex gap-3">
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
            </div>
        </div>
    );
};

export default GlobeView;
