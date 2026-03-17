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

    // Map trade flows to globe arcs
    const arcs = (analysis?.trade_flows || []).map((f: any) => {
        const start = countryCoords[f.country] || [0, 0];
        const end = [37.09, -95.71]; // USA
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
        <div className="h-screen w-screen bg-background p-4 grid grid-cols-12 grid-rows-6 gap-4 overflow-hidden">
            {/* Left Panel: Selector + Metrics + Scenarios */}
            <div className="col-span-3 row-span-6 flex flex-col gap-4 overflow-y-auto pr-1">
                <div className="card-surface p-4">
                    <CompanySelector 
                        companies={companies} 
                        onSelect={setSelectedCompany} 
                        selectedCompany={selectedCompany} 
                    />
                </div>

                {analysis && (
                    <div className="card-surface p-4 animate-in fade-in slide-in-from-left-4 duration-500">
                        <div className="flex items-center gap-2 mb-2">
                            <div className={`w-2 h-2 rounded-full ${analysis.score > 70 ? 'bg-risk-high animate-pulse-glow' : 'bg-risk-low'}`} />
                            <span className="text-[10px] text-muted-foreground uppercase font-bold tracking-widest">
                                {analysis.score > 70 ? 'Critical' : 'Stable'} Dependency
                            </span>
                        </div>
                        <h1 className="text-sm font-semibold text-foreground">{analysis.company}</h1>
                        <p className="text-[10px] font-mono text-muted-foreground mt-1">
                            Minerals: {analysis.minerals.join(', ')}
                        </p>
                        <p className="text-[10px] font-mono text-muted-foreground mt-2 line-clamp-3 italic opacity-70">
                           "{analysis.summary}"
                        </p>
                    </div>
                )}

                <MetricsPanel analysis={analysis} isLoading={isAnalyzing} />
                <ScenariosPanel scenarios={analysis?.scenarios || []} />
            </div>

            {/* Center: Globe */}
            <div className="col-span-6 row-span-4 card-surface overflow-hidden relative">
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

            {/* Right Panel: Agent Workflow */}
            <div className="col-span-3 row-span-6">
                <AgentWorkflow isAnalyzing={isAnalyzing} selectedCompany={selectedCompany} />
            </div>

            {/* Bottom: Risk Table */}
            <div className="col-span-6 row-span-2">
                <RiskTable flows={analysis?.trade_flows || []} isLoading={isAnalyzing} />
            </div>
        </div>
    );
};

export default Index;
