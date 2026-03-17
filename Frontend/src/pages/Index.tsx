import { useState, useEffect } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { fetchCompanies, fetchCompanyScenarios, simulateDisruption } from "@/lib/api";
import type { ScenarioCard, SimulationResult } from "@/lib/api";
import { useAnalysisStream } from "@/hooks/useAnalysisStream";
import { useCustomScenarioStream } from "@/hooks/useCustomScenarioStream";
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
    const [activeScenario, setActiveScenario] = useState<ScenarioCard | null>(null);
    const [simulationResult, setSimulationResult] = useState<SimulationResult | null>(null);
    const [speedMultiplier, setSpeedMultiplier] = useState(1);

    const { steps, isStreaming, analysisResult, startStream } = useAnalysisStream();
    const { customSteps, isCustomStreaming, customResult, startCustomStream, resetCustom } = useCustomScenarioStream();
    const analysis = analysisResult;
    const isAnalyzing = isStreaming;

    const { data: companies = [] } = useQuery({
        queryKey: ['companies'],
        queryFn: fetchCompanies
    });

    const { data: scenarios = [], isLoading: scenariosLoading } = useQuery({
        queryKey: ['scenarios', selectedCompany],
        queryFn: () => fetchCompanyScenarios(selectedCompany!),
        enabled: !!selectedCompany && !!analysis,
    });

    const simulateMutation = useMutation({
        mutationFn: (scenario: ScenarioCard) =>
            simulateDisruption(selectedCompany!, scenario.country, scenario.mineral),
        onSuccess: (result) => setSimulationResult(result),
    });

    const handleCompanySelect = (company: string) => {
        setSelectedCompany(company);
        setActiveScenario(null);
        setSimulationResult(null);
        startStream(company);
    };

    const handleSimulate = (scenario: ScenarioCard) => {
        setActiveScenario(scenario);
        simulateMutation.mutate(scenario);
    };

    const handleResetScenario = () => {
        setActiveScenario(null);
        setSimulationResult(null);
        resetCustom();
    };

    const handleCustomScenario = (text: string) => {
        if (!selectedCompany) return;
        setActiveScenario(null);
        setSimulationResult(null);
        startCustomStream(selectedCompany, text);
    };

    // Apply custom scenario result when it arrives
    useEffect(() => {
        if (customResult) {
            setSimulationResult(customResult);
        }
    }, [customResult]);

    // Map trade flows to globe arcs — use disrupted flows when simulation is active
    const flows = simulationResult?.disrupted_trade_flows || analysis?.trade_flows || [];
    const arcs = flows.map((f: any, index: number) => {
        const start = countryCoords[f.country] || [0, 0];
        const end = [37.09, -95.71]; // USA

        let color = f.risk === 'high' ? '#ef4444' : f.risk === 'elevated' ? '#f59e0b' : '#22c55e';
        let stroke = f.risk === 'high' ? 1.2 : f.risk === 'elevated' ? 0.8 : 0.4;
        let animateTime = f.risk === 'high' ? 4000 : f.risk === 'elevated' ? 2500 : 1200;
        let status = f.status || 'active';
        const initialGap = (index / flows.length) * 2;

        if (simulationResult) {
            if (status === 'disrupted') {
                color = 'rgba(239, 68, 68, 0.4)'; // ghost red
                stroke = 0.3;
            } else if (status === 'stressed') {
                color = '#f59e0b';
                stroke = 1.5;
            }
        }

        return {
            startLat: start[0],
            startLng: start[1],
            endLat: end[0],
            endLng: end[1],
            color,
            stroke,
            status,
            animateTime,
            initialGap,
            label: `${f.mineral}: ${f.country} → USA (${f.share}%)`,
            riskLevel: f.risk
        };
    });

    return (
        <div className="h-screen w-screen bg-background flex flex-col overflow-hidden">
            {/* Header */}
            <div className="flex items-center gap-3 px-4 py-2 border-b border-border/40">
                <img src="/roq-icon.png" alt="Roq" className="h-7 w-7 rounded" />
                <h1 className="text-lg font-bold tracking-tight text-foreground">Roq</h1>
                <span className="text-[10px] font-mono text-muted-foreground uppercase tracking-widest ml-1">Supply Chain Intelligence</span>
            </div>
            {/* Dashboard Grid */}
            <div className="flex-1 p-4 grid grid-cols-12 grid-rows-6 gap-4 overflow-hidden">
            {/* Left Panel: Selector + Metrics + Scenarios */}
            <div className="col-span-3 row-span-6 flex flex-col gap-4 overflow-y-auto pr-1">
                <div className="card-surface p-4">
                    <CompanySelector
                        companies={companies}
                        onSelect={handleCompanySelect}
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
                    </div>
                )}

                <MetricsPanel analysis={analysis} isLoading={isAnalyzing} simulationResult={simulationResult} />
                <ScenariosPanel
                    scenarios={scenarios}
                    isLoading={scenariosLoading}
                    activeScenarioId={activeScenario?.id ?? null}
                    onSimulate={handleSimulate}
                    onReset={handleResetScenario}
                    isSimulating={simulateMutation.isPending}
                    onCustomScenario={handleCustomScenario}
                    isCustomScenarioActive={isCustomStreaming}
                />
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
                <GlobeView arcs={arcs} speedMultiplier={speedMultiplier} onSpeedChange={setSpeedMultiplier} />
            </div>

            {/* Right Panel: Agent Workflow */}
            <div className="col-span-3 row-span-6">
                <AgentWorkflow steps={isCustomStreaming ? customSteps : steps} isStreaming={isStreaming || isCustomStreaming} />
            </div>

            {/* Bottom: Risk Table */}
            <div className="col-span-6 row-span-2">
                <RiskTable flows={simulationResult?.disrupted_trade_flows || analysis?.trade_flows || []} isLoading={isAnalyzing} />
            </div>
            </div>
        </div>
    );
};

export default Index;
