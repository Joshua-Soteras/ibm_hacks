import { agentSteps } from "@/data/simulatedData";

const AgentStep = ({ step, isLast }: { step: any; isLast: boolean }) => (
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
            <pre className="text-[9px] font-mono text-muted-foreground bg-secondary/10 p-2 rounded border border-secondary/20 leading-relaxed overflow-x-auto">
                {step.trace}
            </pre>
        </div>
    </div>
);

const AgentWorkflow = ({ isAnalyzing }: { isAnalyzing: boolean }) => {
    return (
        <div className="card-surface h-full flex flex-col p-4">
            <div className="flex items-center justify-between mb-6">
                <h3 className="text-[10px] text-muted-foreground uppercase font-bold tracking-widest">Agent Workflow</h3>
                <span className="text-[9px] font-mono text-agent-active px-2 py-0.5 rounded-full bg-agent-active/10">3/5 Active</span>
            </div>
            <div className={`flex-1 overflow-y-auto pr-1 space-y-3 transition-opacity duration-300 ${isAnalyzing ? 'opacity-50' : 'opacity-100'}`}>
                {isAnalyzing && (
                    <div className="flex items-center gap-2 mb-4 p-2 bg-primary/10 border border-primary/20 rounded">
                        <div className="w-2 h-2 rounded-full bg-primary animate-pulse" />
                        <span className="text-[10px] font-mono text-primary uppercase">Risk Orchestrator: Planning analysis...</span>
                    </div>
                )}
                {agentSteps.map((step, i) => (
                    <AgentStep key={step.id} step={step} isLast={i === agentSteps.length - 1} />
                ))}
            </div>
        </div>
    );
};

export default AgentWorkflow;
