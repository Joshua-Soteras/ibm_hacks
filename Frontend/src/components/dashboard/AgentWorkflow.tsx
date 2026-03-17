import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown } from "lucide-react";
import type { AgentStepData } from "@/hooks/useAnalysisStream";
import Markdown from "@/components/ui/markdown";

const AgentStep = ({ step, isLast }: { step: AgentStepData; isLast: boolean }) => {
    const [expanded, setExpanded] = useState(false);
    const hasFullOutput = !!step.full_output;

    return (
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
                <div className="bg-secondary/10 p-2 rounded border border-secondary/20 overflow-x-auto">
                    <Markdown>{step.trace}</Markdown>
                </div>
                {hasFullOutput && (
                    <>
                        <button
                            onClick={() => setExpanded(prev => !prev)}
                            className="flex items-center gap-1 text-[8px] font-mono text-primary/70 hover:text-primary transition-colors self-start"
                        >
                            <motion.span
                                animate={{ rotate: expanded ? 180 : 0 }}
                                transition={{ duration: 0.2 }}
                                className="inline-flex"
                            >
                                <ChevronDown className="w-3 h-3" />
                            </motion.span>
                            {expanded ? "Collapse" : "Show full output"}
                        </button>
                        <AnimatePresence>
                            {expanded && (
                                <motion.div
                                    initial={{ height: 0, opacity: 0 }}
                                    animate={{ height: "auto", opacity: 1 }}
                                    exit={{ height: 0, opacity: 0 }}
                                    transition={{ duration: 0.2 }}
                                    className="overflow-hidden"
                                >
                                    <div className="bg-secondary/10 p-2 rounded border border-primary/20 max-h-[300px] overflow-y-auto overflow-x-auto">
                                        <Markdown>{step.full_output!}</Markdown>
                                    </div>
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </>
                )}
            </div>
        </div>
    );
};

const AgentWorkflow = ({ steps, isStreaming }: { steps: AgentStepData[]; isStreaming: boolean }) => {
    const activeCount = steps.filter(s => s.status === 'active').length;
    const completedCount = steps.filter(s => s.status === 'completed').length;
    const statusLabel = isStreaming
        ? `${activeCount} active · ${completedCount}/${steps.length} done`
        : completedCount === steps.length && completedCount > 0
          ? `${steps.length}/${steps.length} Complete`
          : 'Idle';

    return (
        <div className="card-surface h-full flex flex-col p-4 relative overflow-hidden">
            <div className="flex items-center justify-between mb-6">
                <h3 className="text-[10px] text-muted-foreground uppercase font-bold tracking-widest">Agent Workflow</h3>
                <span className="text-[9px] font-mono text-agent-active px-2 py-0.5 rounded-full bg-agent-active/10">{statusLabel}</span>
            </div>
            <div className="flex-1 overflow-y-auto pr-1 space-y-3">
                {isStreaming && steps.every(s => s.status === 'pending') && (
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
