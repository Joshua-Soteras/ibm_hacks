import { useState } from "react";
import { motion } from "framer-motion";
import type { ScenarioCard } from "@/lib/api";

interface ScenariosPanelProps {
    scenarios: ScenarioCard[];
    isLoading: boolean;
    activeScenarioId: string | null;
    onSimulate: (scenario: ScenarioCard) => void;
    onReset: () => void;
    isSimulating: boolean;
    onCustomScenario?: (text: string) => void;
    isCustomScenarioActive?: boolean;
}

const ConcentrationBar = ({ pct }: { pct: number }) => (
    <div className="w-16 h-4 bg-secondary/20 rounded-sm overflow-hidden relative">
        <div
            className={`h-full rounded-sm ${pct > 70 ? 'bg-risk-high' : pct > 40 ? 'bg-risk-mid' : 'bg-risk-low'}`}
            style={{ width: `${Math.min(pct, 100)}%` }}
        />
        <span className="absolute inset-0 flex items-center justify-center text-[8px] font-mono text-foreground">
            {pct.toFixed(0)}%
        </span>
    </div>
);

const ScenariosPanel = ({ scenarios, isLoading, activeScenarioId, onSimulate, onReset, isSimulating, onCustomScenario, isCustomScenarioActive }: ScenariosPanelProps) => {
    const [customText, setCustomText] = useState("");

    const handleCustomSubmit = () => {
        const trimmed = customText.trim();
        if (trimmed && onCustomScenario) {
            onCustomScenario(trimmed);
            setCustomText("");
        }
    };
    if (isLoading) {
        return (
            <div className="flex flex-col gap-3">
                <h3 className="text-[10px] text-muted-foreground uppercase font-bold tracking-widest px-1">Probable Scenarios</h3>
                <div className="card-surface p-4 flex items-center justify-center">
                    <span className="text-[10px] font-mono text-muted-foreground animate-pulse">Loading scenarios...</span>
                </div>
            </div>
        );
    }

    if (!scenarios || scenarios.length === 0) {
        return (
            <div className="flex flex-col gap-3">
                <h3 className="text-[10px] text-muted-foreground uppercase font-bold tracking-widest px-1">Probable Scenarios</h3>
                <div className="card-surface p-4 text-center">
                    <span className="text-[10px] font-mono text-muted-foreground italic">Select a company for scenario modeling</span>
                </div>
            </div>
        );
    }

    return (
        <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.4, delay: 0.1, ease: [0.2, 0, 0, 1] }}
            className="flex flex-col gap-3"
        >
            <div className="flex items-center justify-between px-1">
                <h3 className="text-[10px] text-muted-foreground uppercase font-bold tracking-widest">Probable Scenarios</h3>
                {(activeScenarioId || isCustomScenarioActive) && (
                    <button
                        onClick={onReset}
                        className="text-[9px] font-mono text-primary hover:text-primary/80 px-2 py-0.5 rounded bg-primary/10 hover:bg-primary/20 transition-colors"
                    >
                        Reset
                    </button>
                )}
            </div>
            {onCustomScenario && (
                <div className="card-surface p-2.5 flex items-center gap-2">
                    <input
                        type="text"
                        value={customText}
                        onChange={(e) => setCustomText(e.target.value)}
                        onKeyDown={(e) => e.key === "Enter" && handleCustomSubmit()}
                        placeholder="Describe a custom scenario..."
                        disabled={isSimulating || isCustomScenarioActive}
                        className="flex-1 bg-transparent text-[11px] text-foreground placeholder:text-muted-foreground/50 outline-none font-mono disabled:opacity-50"
                    />
                    <button
                        onClick={handleCustomSubmit}
                        disabled={!customText.trim() || isSimulating || isCustomScenarioActive}
                        className="text-[9px] font-mono text-primary hover:text-primary/80 px-2 py-1 rounded bg-primary/10 hover:bg-primary/20 transition-colors disabled:opacity-30 disabled:pointer-events-none"
                    >
                        Analyze
                    </button>
                </div>
            )}
            {scenarios.map((s) => (
                <div
                    key={s.id}
                    onClick={() => !isSimulating && onSimulate(s)}
                    className={`card-surface p-3 risk-border-${s.impact} cursor-pointer hover:bg-secondary/50 transition-all duration-200
                        ${activeScenarioId === s.id ? 'ring-1 ring-primary bg-primary/5' : ''}
                        ${isSimulating ? 'opacity-50 pointer-events-none' : ''}`}
                >
                    <div className="flex items-start justify-between gap-2">
                        <div className="flex-1 min-w-0">
                            <h4 className="text-xs font-medium text-foreground truncate">{s.title}</h4>
                            <div className="flex items-center gap-3 mt-1.5">
                                <span className="text-[10px] text-muted-foreground">
                                    {s.country} · <span className="font-mono text-foreground">{s.mineral}</span>
                                </span>
                                <span className={`text-[9px] font-mono px-1.5 py-0.5 rounded ${s.impact === 'high' ? 'bg-risk-high/10 text-risk-high' : 'bg-risk-mid/10 text-risk-mid'}`}>
                                    {s.impact}
                                </span>
                            </div>
                        </div>
                        <ConcentrationBar pct={s.top_share_pct} />
                    </div>
                </div>
            ))}
        </motion.div>
    );
};

export default ScenariosPanel;
