interface Step {
    id: string;
    title: string;
    status: 'completed' | 'active' | 'pending';
    timestamp: string;
    trace: string;
}

const AgentStep = ({ step, isLast }: { step: Step; isLast: boolean }) => {
    const isActive = step.status === 'active';
    const isCompleted = step.status === 'completed';

    return (
        <div
            className={`relative pl-6 pb-5 last:pb-2 rounded-lg transition-all duration-300 ${isActive ? 'bg-agent-active/5 border border-agent-active/20 px-3 py-3 ml-[-4px]' : ''}`}
        >
            {!isLast && (
                <div className={`absolute left-[7px] top-[14px] bottom-0 w-[1px] ${isActive ? 'bg-agent-active/40' : 'bg-secondary/30'}`}
                    style={isActive ? { boxShadow: '0 0 4px rgba(34,197,94,0.3)' } : {}}
                />
            )}
            <div className={`absolute left-0 top-[6px] w-3.5 h-3.5 rounded-full border-2 bg-background z-10
                ${isCompleted ? 'border-risk-low' : isActive ? 'border-agent-active animate-pulse' : 'border-secondary'}`}
                style={isActive ? { boxShadow: '0 0 8px rgba(34,197,94,0.5)' } : {}}
            />
            <div className="flex flex-col gap-1">
                <div className="flex items-center justify-between">
                    <span className={`text-[11px] font-semibold ${isActive ? 'text-agent-active' : isCompleted ? 'text-foreground' : 'text-muted-foreground'}`}>
                        {step.title}
                    </span>
                    <span className={`text-[9px] font-mono ${isActive ? 'text-agent-active/70' : 'text-muted-foreground'}`}>{step.timestamp}</span>
                </div>
                <pre className={`text-[9px] font-mono p-2 rounded border leading-relaxed overflow-x-auto whitespace-pre-wrap
                    ${isActive ? 'text-agent-active/80 bg-agent-active/5 border-agent-active/20' : 'text-muted-foreground bg-secondary/10 border-secondary/20'}`}>
                    {step.trace}
                </pre>
            </div>
        </div>
    );
};

const AgentWorkflow = ({ isAnalyzing, selectedCompany }: { isAnalyzing: boolean; selectedCompany: string | null }) => {
    const steps: Step[] = [
        {
            id: "1",
            title: "Data Ingestion Agent",
            status: selectedCompany ? 'completed' : 'pending',
            timestamp: "14:32:01",
            trace: selectedCompany
                ? `> Fetched SEC filings for ${selectedCompany}\n> Cross-referenced USITC trade flow data\n> SQL Query: SELECT * FROM edgar_filing_details WHERE Company = '${selectedCompany}'`
                : "> Waiting for target selection..."
        },
        {
            id: "2",
            title: "Risk Assessment Agent",
            status: isAnalyzing ? 'active' : selectedCompany ? 'completed' : 'pending',
            timestamp: "14:32:18",
            trace: isAnalyzing
                ? "> Compiling HHI concentration index...\n> Mapping USGS supply risk status..."
                : selectedCompany
                    ? "> Risk scores computed successfully.\n> Trade concentration: OK"
                    : "> Standing by..."
        },
        {
            id: "3",
            title: "Logistics Optimizer",
            status: isAnalyzing ? 'pending' : selectedCompany ? 'completed' : 'pending',
            timestamp: "14:32:45",
            trace: selectedCompany
                ? "> Recalculating lead times for 75 vectors\n> Route 402: Alt route via Vietnam +$2.4M"
                : "> Awaiting assessment data..."
        },
        {
            id: "4",
            title: "Scenario Modeler",
            status: 'pending',
            timestamp: "--:--:--",
            trace: "> Awaiting refined supply chain graph..."
        }
    ];

    const activeCount = steps.filter(s => s.status !== 'pending').length;

    return (
        <div className="card-surface h-full flex flex-col p-4 relative overflow-hidden">
            <div className="flex items-center justify-between mb-4">
                <h3 className="text-[10px] text-muted-foreground uppercase font-bold tracking-widest">Agent Workflow</h3>
                <span className="text-[9px] font-mono text-agent-active px-2 py-0.5 rounded-full bg-agent-active/10 border border-agent-active/20">
                    {activeCount}/4 Active
                </span>
            </div>

            {isAnalyzing && (
                <div className="flex items-center gap-2 mb-4 p-2 bg-primary/10 border border-primary/20 rounded">
                    <div className="w-2 h-2 rounded-full bg-primary animate-pulse" />
                    <span className="text-[10px] font-mono text-primary uppercase">Risk Orchestrator: Solving multi-vector optimization...</span>
                </div>
            )}

            <div className="flex-1 overflow-y-auto pr-1 space-y-1">
                {steps.map((step, i) => (
                    <AgentStep key={step.id} step={step} isLast={i === steps.length - 1} />
                ))}
            </div>

            <div className="absolute -bottom-10 -right-10 w-40 h-40 bg-primary/5 rounded-full blur-3xl -z-10" />
        </div>
    );
};

export default AgentWorkflow;
