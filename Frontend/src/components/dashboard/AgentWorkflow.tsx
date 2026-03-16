import { motion } from "framer-motion";
import { agentSteps } from "@/data/simulatedData";
import { useState } from "react";

const AgentStep = ({ step, isLast }: { step: typeof agentSteps[0]; isLast: boolean }) => {
    const [expanded, setExpanded] = useState(step.status === 'active');

    return (
        <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.3, ease: [0.2, 0, 0, 1] }}
            className={`relative pl-6 pb-5 ${!isLast ? 'border-l border-border' : ''} cursor-pointer`}
            onClick={() => setExpanded(!expanded)}
        >
            <div
                className={`absolute left-[-5px] top-0.5 w-2.5 h-2.5 rounded-full transition-all duration-200
          ${step.status === 'active' ? 'status-dot-active animate-pulse-glow' : ''}
          ${step.status === 'completed' ? 'bg-agent-active' : ''}
          ${step.status === 'pending' ? 'status-dot-idle' : ''}
        `}
            />
            <div className="flex items-center justify-between mb-1">
                <h4 className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">{step.title}</h4>
                <span className="text-[9px] font-mono text-muted-foreground">{step.timestamp}</span>
            </div>

            {expanded && (
                <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    className="bg-background p-2 rounded-md border border-border/50 mt-1"
                >
                    <code className="text-[10px] leading-relaxed font-mono whitespace-pre-wrap block
            ${step.status === 'completed' ? 'text-agent-active/80' : ''}
            ${step.status === 'active' ? 'text-primary' : ''}
            ${step.status === 'pending' ? 'text-muted-foreground' : ''}
          ">
                        {step.trace}
                    </code>
                </motion.div>
            )}

            {!expanded && (
                <p className="text-[10px] font-mono text-muted-foreground truncate mt-0.5">
                    {step.trace.split('\n')[0]}
                </p>
            )}
        </motion.div>
    );
};

const AgentWorkflow = () => {
    return (
        <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.4, ease: [0.2, 0, 0, 1] }}
            className="card-surface p-4 h-full flex flex-col"
        >
            <div className="flex items-center justify-between mb-4">
                <h3 className="text-[10px] text-muted-foreground uppercase font-bold tracking-widest">Agent Workflow</h3>
                <span className="text-[9px] font-mono text-agent-active px-2 py-0.5 rounded-full bg-agent-active/10">3/5 Active</span>
            </div>
            <div className="flex-1 overflow-y-auto pr-1">
                {agentSteps.map((step, i) => (
                    <AgentStep key={step.id} step={step} isLast={i === agentSteps.length - 1} />
                ))}
            </div>
        </motion.div>
    );
};

export default AgentWorkflow;
