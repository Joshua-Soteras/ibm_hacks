import MetricsPanel from "@/components/dashboard/MetricsPanel";
import ScenariosPanel from "@/components/dashboard/ScenariosPanel";
import GlobeView from "@/components/dashboard/GlobeView";
import AgentWorkflow from "@/components/dashboard/AgentWorkflow";
import RiskTable from "@/components/dashboard/RiskTable";

const Index = () => {
    return (
        <div className="h-screen w-screen bg-background p-4 grid grid-cols-12 grid-rows-6 gap-4 overflow-hidden">
            {/* Left Panel: Metrics + Scenarios */}
            <div className="col-span-3 row-span-6 flex flex-col gap-4 overflow-y-auto pr-1">
                {/* Critical Component Header */}
                <div className="card-surface p-4">
                    <div className="flex items-center gap-2 mb-2">
                        <div className="w-2 h-2 rounded-full bg-risk-high animate-pulse-glow" />
                        <span className="text-[10px] text-muted-foreground uppercase font-bold tracking-widest">Critical Component</span>
                    </div>
                    <h1 className="text-sm font-semibold text-foreground">Semiconductor-X9</h1>
                    <p className="text-[10px] font-mono text-muted-foreground mt-1">TSMC → Austin, TX · Route 402</p>
                    <p className="text-[10px] font-mono text-risk-high mt-1">Route 402 Latency detected. +38h delay.</p>
                </div>

                <MetricsPanel />
                <ScenariosPanel />
            </div>

            {/* Center: Globe */}
            <div className="col-span-6 row-span-4 card-surface overflow-hidden">
                <GlobeView />
            </div>

            {/* Right Panel: Agent Workflow */}
            <div className="col-span-3 row-span-6">
                <AgentWorkflow />
            </div>

            {/* Bottom: Risk Table */}
            <div className="col-span-6 row-span-2">
                <RiskTable />
            </div>
        </div>
    );
};

export default Index;
