import { useState } from "react";
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
    const now = new Date();
    const time = now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
    const date = now.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });

    return (
        <div className="h-10 flex items-center justify-between px-4 border-b border-secondary/30 bg-background/60 backdrop-blur-sm flex-shrink-0">
            <div className="flex items-center gap-3">
                <div className="flex items-center gap-2">
                    <div className="w-5 h-5 rounded bg-primary flex items-center justify-center">
                        <span className="text-[8px] font-bold text-white">MW</span>
                    </div>
                    <span className="text-xs font-semibold text-foreground tracking-wide">MineralWatch</span>
                </div>
                <div className="w-px h-4 bg-secondary/50" />
                <span className="text-[10px] text-muted-foreground font-mono">Supply Chain Risk Intelligence</span>
            </div>

            <div className="flex items-center gap-4">
                {selectedCompany && score !== undefined && (
                    <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-secondary/20 border border-secondary/30">
                        <div className={`w-1.5 h-1.5 rounded-full ${score > 70 ? 'bg-risk-high animate-pulse' : score > 40 ? 'bg-risk-mid' : 'bg-risk-low'}`} />
                        <span className="text-[10px] font-mono text-foreground">{selectedCompany}</span>
                        <span className={`text-[10px] font-mono font-bold ${score > 70 ? 'text-risk-high' : score > 40 ? 'text-risk-mid' : 'text-risk-low'}`}>
                            {score}
                        </span>
                    </div>
                )}
                <div className="flex items-center gap-2">
                    <div className="w-1.5 h-1.5 rounded-full bg-risk-low animate-pulse" />
                    <span className="text-[9px] font-mono text-muted-foreground">LIVE</span>
                </div>
                <span className="text-[9px] font-mono text-muted-foreground">{date} · {time}</span>
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
        <div className="h-screen w-screen bg-background flex flex-col overflow-hidden">
            <Navbar selectedCompany={selectedCompany} score={analysis?.score} />

            <div className="flex-1 p-3 grid grid-cols-12 grid-rows-6 gap-3 overflow-hidden min-h-0">
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

                    {/* Divider label */}
                    <div className="flex items-center gap-2 flex-shrink-0 px-1">
                        <div className="flex-1 h-px bg-secondary/30" />
                        <span className="text-[9px] text-muted-foreground/50 uppercase tracking-widest font-bold">Metrics</span>
                        <div className="flex-1 h-px bg-secondary/30" />
                    </div>

                    <MetricsPanel analysis={analysis} isLoading={isAnalyzing} />

                    {/* Divider label */}
                    <div className="flex items-center gap-2 flex-shrink-0 px-1">
                        <div className="flex-1 h-px bg-secondary/30" />
                        <span className="text-[9px] text-muted-foreground/50 uppercase tracking-widest font-bold">Scenarios</span>
                        <div className="flex-1 h-px bg-secondary/30" />
                    </div>

                    <ScenariosPanel scenarios={analysis?.scenarios || []} />
                </div>

                {/* Center: Globe */}
                <div className="col-span-6 row-span-3 card-surface overflow-hidden relative">
                    {isAnalyzing && (
                        <div className="absolute inset-0 z-10 flex items-center justify-center bg-background/20 backdrop-blur-sm">
                            <div className="flex flex-col items-center gap-2">
                                <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                                <span className="text-[10px] font-mono text-primary uppercase tracking-widest">Re-computing spatial risk...</span>
                            </div>
                        </div>
                    )}
                    <GlobeView arcs={arcs} />
                </div>

                {/* Right Panel */}
                <div className="col-span-3 row-span-6">
                    <AgentWorkflow isAnalyzing={isAnalyzing} selectedCompany={selectedCompany} />
                </div>

                {/* Bottom: Risk Table — now row-span-3 for more room */}
                <div className="col-span-6 row-span-3">
                    <RiskTable flows={analysis?.trade_flows || []} isLoading={isAnalyzing} />
                </div>
            </div>
        </div>
    );
};

export default Index;
