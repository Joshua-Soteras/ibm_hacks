interface Step {
    id: string;
    title: string;
    status: 'completed' | 'active' | 'pending';
    timestamp: string;
    trace: string;
}

const AgentStep = ({ step, isLast }: { step: Step; isLast: boolean }) => (
    <div className="relative pl-6 pb-6 last:pb-2">
        {!isLast && (
            <div className="absolute left-[7px] top-[14px] bottom-0 w-[1px] bg-secondary/30" />
        )}
        <div className={`absolute left-0 top-[6px] w-3.5 h-3.5 rounded-full border-2 bg-background z-10 
            ${step.status === 'completed' ? 'border-risk-low' : step.status === 'active' ? 'border-agent-active animate-pulse' : 'border-secondary'}`} 
        />
        <div className="flex flex-col gap-1">
            <div className="flex items-center justify-between">
                <span className={`text-[11px] font-semibold ${step.status === 'active' ? 'text-agent-active' : 'text-foreground'}`}>
                    {step.title}
                </span>
                <span className="text-[9px] font-mono text-muted-foreground">{step.timestamp}</span>
            </div>
            <pre className="text-[9px] font-mono text-muted-foreground bg-secondary/10 p-2 rounded border border-secondary/20 leading-relaxed overflow-x-auto whitespace-pre-wrap">
                {step.trace}
            </pre>
        </div>
    </div>
);

const AgentWorkflow = ({ isAnalyzing, selectedCompany }: { isAnalyzing: boolean; selectedCompany: string | null }) => {
    // Generate dynamic steps based on state
    const steps: Step[] = [
        {
            id: "1",
            title: "Data Ingestion Agent",
            status: selectedCompany ? 'completed' : 'pending',
            timestamp: "14:32:01",
            trace: selectedCompany ? `> Fetched SEC filings for ${selectedCompany}\n> Cross-referenced USITC trade flow data\n> SQL Query: SELECT * FROM edgar_filing_details WHERE Company = '${selectedCompany}'` : "> Waiting for target selection..."
        },
        {
            id: "2",
            title: "Risk Assessment Agent",
            status: isAnalyzing ? 'active' : selectedCompany ? 'completed' : 'pending',
            timestamp: "14:32:18",
            trace: isAnalyzing ? "> Compiling HHI concentration index...\n> Mapping USGS supply risk status..." : selectedCompany ? "> Risk scores computed successfully.\n> Trade concentration: OK" : "> Standing by..."
        },
        {
            id: "3",
            title: "Logistics Optimizer",
            status: isAnalyzing ? 'pending' : selectedCompany ? 'completed' : 'pending',
            timestamp: "14:32:45",
            trace: selectedCompany ? "> Recalculating lead times for 75 vectors\n> Route 402: Alt route via Vietnam +$2.4M" : "> Awaiting assessment data..."
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
            <div className="flex items-center justify-between mb-6">
                <h3 className="text-[10px] text-muted-foreground uppercase font-bold tracking-widest">Agent Workflow</h3>
                <span className="text-[9px] font-mono text-agent-active px-2 py-0.5 rounded-full bg-agent-active/10">
                    {activeCount}/4 Active
                </span>
            </div>
            
            <div className="flex-1 overflow-y-auto pr-1 space-y-3">
                {isAnalyzing && (
                    <div className="flex items-center gap-2 mb-4 p-2 bg-primary/10 border border-primary/20 rounded">
                        <div className="w-2 h-2 rounded-full bg-primary animate-pulse" />
                        <span className="text-[10px] font-mono text-primary uppercase">Risk Orchestrator: Solving multi-vector optimization...</span>
                    </div>
                )}
                
                {steps.map((step, i) => (
                    <AgentStep key={step.id} step={step} isLast={i === steps.length - 1} />
                ))}
            </div>

            {/* Subtle background decoration */}
            <div className="absolute -bottom-10 -right-10 w-40 h-40 bg-primary/5 rounded-full blur-3xl -z-10" />
        </div>
    );
};

export default AgentWorkflow;
