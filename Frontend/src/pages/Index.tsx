import { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchCompanies, fetchAnalyze } from "@/lib/api";
import MetricsPanel from "@/components/dashboard/MetricsPanel";
import ScenariosPanel from "@/components/dashboard/ScenariosPanel";
import GlobeView from "@/components/dashboard/GlobeView";
import AgentWorkflow from "@/components/dashboard/AgentWorkflow";
import RiskTable from "@/components/dashboard/RiskTable";
import CompanySelector from "@/components/dashboard/CompanySelector";
import countryCoordsData from "@/data/countryCoords.json";

const countryCoords: Record<string, number[]> = countryCoordsData;

const Navbar = ({ selectedCompany, score }: { selectedCompany: string | null; score?: number }) => {
    const [now, setNow] = useState(new Date());

    useEffect(() => {
        const id = setInterval(() => setNow(new Date()), 1000);
        return () => clearInterval(id);
    }, []);

    const time = now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
    const date = now.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });

    return (
        <div className="h-10 flex items-center justify-between px-4 border-b border-white/[0.06] bg-background/80 backdrop-blur-md flex-shrink-0 relative z-20">
            {/* Left: branding */}
            <div className="flex items-center gap-3">
                <div className="flex items-center gap-2">
                    <div className="w-6 h-6 rounded-md flex items-center justify-center"
                        style={{ background: 'linear-gradient(135deg, #3b82f6, #1d4ed8)', boxShadow: '0 0 12px rgba(59,130,246,0.4)' }}>
                        <span className="text-[9px] font-bold text-white tracking-tight">MW</span>
                    </div>
                    <span className="text-xs font-semibold text-foreground tracking-wide">MineralWatch</span>
                </div>
                <div className="w-px h-4 bg-white/10" />
                <span className="text-[10px] text-muted-foreground font-mono hidden sm:block">Supply Chain Risk Intelligence</span>
            </div>

            {/* Right: status pills */}
            <div className="flex items-center gap-3">
                {selectedCompany && score !== undefined && (
                    <div className="flex items-center gap-2 px-3 py-1 rounded-full border"
                        style={{
                            background: score > 70 ? 'rgba(239,68,68,0.08)' : score > 40 ? 'rgba(245,158,11,0.08)' : 'rgba(34,197,94,0.08)',
                            borderColor: score > 70 ? 'rgba(239,68,68,0.25)' : score > 40 ? 'rgba(245,158,11,0.25)' : 'rgba(34,197,94,0.25)',
                        }}>
                        <div className={`w-1.5 h-1.5 rounded-full animate-pulse ${score > 70 ? 'bg-risk-high' : score > 40 ? 'bg-risk-mid' : 'bg-risk-low'}`} />
                        <span className="text-[10px] font-mono text-foreground">{selectedCompany}</span>
                        <span className={`text-[10px] font-mono font-bold ${score > 70 ? 'text-risk-high' : score > 40 ? 'text-risk-mid' : 'text-risk-low'}`}>
                            {score}
                        </span>
                    </div>
                )}
                <div className="flex items-center gap-1.5 px-2 py-1 rounded-full bg-risk-low/10 border border-risk-low/20">
                    <div className="w-1.5 h-1.5 rounded-full bg-risk-low animate-pulse" />
                    <span className="text-[9px] font-mono text-risk-low">LIVE</span>
                </div>
                <span className="text-[9px] font-mono text-muted-foreground tabular-nums">{date} · {time}</span>
            </div>
        </div>
    );
};

const Index = () => {
    const [selectedCompany, setSelectedCompany] = useState<string | null>(null);

    const { data: companies = [] } = useQuery({
        queryKey: ['companies'],
        queryFn: fetchCompanies
    });

    const { data: analysis, isLoading: isAnalyzing } = useQuery({
        queryKey: ['analyze', selectedCompany],
        queryFn: () => fetchAnalyze(selectedCompany!),
        enabled: !!selectedCompany,
    });

    const arcs = (analysis?.trade_flows || []).map((f: any) => {
        const start = countryCoords[f.country] || [0, 0];
        const end = [37.09, -95.71];
        return {
            startLat: start[0],
            startLng: start[1],
            endLat: end[0],
            endLng: end[1],
            color: f.risk === 'high' ? '#ef4444' : f.risk === 'elevated' ? '#f59e0b' : '#22c55e',
            label: `${f.mineral}: ${f.country} → USA (${f.share}%)`,
            riskLevel: f.risk
        };
    });

    return (
        <div className="h-screen w-screen bg-background flex flex-col overflow-hidden relative">
            {/* Dot grid background */}
            <div className="absolute inset-0 bg-dot-grid pointer-events-none z-0" />

            {/* Radial glow centered on globe area */}
            <div className="absolute pointer-events-none z-0"
                style={{
                    top: '10%',
                    left: '25%',
                    width: '50%',
                    height: '60%',
                    background: 'radial-gradient(ellipse at center, rgba(59,130,246,0.06) 0%, transparent 70%)',
                }}
            />

            <Navbar selectedCompany={selectedCompany} score={analysis?.score} />

            <div className="flex-1 p-3 grid grid-cols-12 grid-rows-6 gap-3 overflow-hidden min-h-0 relative z-10">
                {/* Left Panel */}
                <div className="col-span-3 row-span-6 flex flex-col gap-3 overflow-y-auto pr-1 min-h-0">
                    {/* Company Selector */}
                    <div className="card-surface p-4 flex-shrink-0">
                        <CompanySelector
                            companies={companies}
                            onSelect={setSelectedCompany}
                            selectedCompany={selectedCompany}
                        />
                    </div>

                    {/* Company Info */}
                    {analysis && (
                        <div className="card-surface p-4 flex-shrink-0 animate-in fade-in slide-in-from-left-4 duration-500"
                            style={{ borderLeft: `2px solid ${analysis.score > 70 ? '#ef4444' : analysis.score > 40 ? '#f59e0b' : '#22c55e'}` }}>
                            <div className="flex items-center gap-2 mb-2">
                                <div className={`w-2 h-2 rounded-full ${analysis.score > 70 ? 'bg-risk-high animate-pulse-glow' : 'bg-risk-low'}`} />
                                <span className="text-[10px] text-muted-foreground uppercase font-bold tracking-widest">
                                    {analysis.score > 70 ? 'Critical' : 'Stable'} Dependency
                                </span>
                            </div>
                            <h1 className="text-sm font-semibold text-foreground">{analysis.company}</h1>
                            <p className="text-[10px] font-mono text-muted-foreground mt-1">
                                {analysis.minerals.join(' · ')}
                            </p>
                            <p className="text-[10px] font-mono text-muted-foreground mt-2 line-clamp-3 italic opacity-70">
                                "{analysis.summary}"
                            </p>
                        </div>
                    )}

                    {/* Divider */}
                    <div className="flex items-center gap-2 flex-shrink-0 px-1">
                        <div className="flex-1 h-px bg-white/[0.05]" />
                        <span className="text-[9px] text-muted-foreground/40 uppercase tracking-widest font-bold">Metrics</span>
                        <div className="flex-1 h-px bg-white/[0.05]" />
                    </div>

                    <MetricsPanel analysis={analysis} isLoading={isAnalyzing} />

                    {/* Divider */}
                    <div className="flex items-center gap-2 flex-shrink-0 px-1">
                        <div className="flex-1 h-px bg-white/[0.05]" />
                        <span className="text-[9px] text-muted-foreground/40 uppercase tracking-widest font-bold">Scenarios</span>
                        <div className="flex-1 h-px bg-white/[0.05]" />
                    </div>

                    <ScenariosPanel scenarios={analysis?.scenarios || []} />
                </div>

                {/* Center: Globe */}
                <div className="col-span-6 row-span-3 card-surface overflow-hidden relative scanline">
                    {isAnalyzing && (
                        <div className="absolute inset-0 z-10 flex items-center justify-center bg-background/30 backdrop-blur-sm">
                            <div className="flex flex-col items-center gap-3">
                                <div className="relative w-10 h-10">
                                    <div className="absolute inset-0 rounded-full border border-primary/20 animate-ping" />
                                    <div className="w-10 h-10 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                                </div>
                                <span className="text-[10px] font-mono text-primary uppercase tracking-widest">Re-computing spatial risk...</span>
                            </div>
                        </div>
                    )}
                    {/* Welcome overlay when no company selected */}
                    {!selectedCompany && !isAnalyzing && (
                        <div className="absolute inset-0 z-10 flex flex-col items-center justify-center gap-2 pointer-events-none">
                            <p className="text-[11px] font-mono text-muted-foreground/60 uppercase tracking-widest">Select a company to begin analysis</p>
                            <div className="flex gap-1.5">
                                {['Gallium', 'Tungsten', 'Cobalt'].map(m => (
                                    <span key={m} className="text-[9px] font-mono px-2 py-0.5 rounded-full bg-secondary/30 text-muted-foreground/50 border border-white/[0.04]">{m}</span>
                                ))}
                            </div>
                        </div>
                    )}
                    <GlobeView arcs={arcs} />
                </div>

                {/* Right Panel */}
                <div className="col-span-3 row-span-6">
                    <AgentWorkflow isAnalyzing={isAnalyzing} selectedCompany={selectedCompany} />
                </div>

                {/* Bottom: Risk Table */}
                <div className="col-span-6 row-span-3">
                    <RiskTable flows={analysis?.trade_flows || []} isLoading={isAnalyzing} />
                </div>
            </div>
        </div>
    );
};

export default Index;
