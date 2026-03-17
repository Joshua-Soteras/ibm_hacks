import { motion } from "framer-motion";
import type { SimulationResult } from "@/lib/api";

const MetricCard = ({ label, value, delta }: { label: string; value: string; delta: number }) => (
    <div className="card-surface p-4">
        <span className="text-[10px] text-muted-foreground uppercase font-bold tracking-widest">{label}</span>
        <div className="flex items-baseline gap-2 mt-1">
            <span className="text-2xl font-mono text-foreground tabular-nums">{value}</span>
            {delta !== 0 && (
                <span className={`text-xs font-mono ${delta > 0 ? 'text-risk-high' : 'text-risk-low'}`}>
                    {delta > 0 ? '+' : ''}{delta}
                </span>
            )}
        </div>
    </div>
);

interface MetricsPanelProps {
    analysis: any;
    isLoading: boolean;
    simulationResult?: SimulationResult | null;
}

const MetricsPanel = ({ analysis, isLoading, simulationResult }: MetricsPanelProps) => {
    const sim = simulationResult;
    const metrics = analysis ? [
        {
            label: 'Risk Score',
            value: sim ? sim.disrupted_score.toString() : analysis.score.toString(),
            delta: sim ? sim.score_delta : 0
        },
        {
            label: 'Trade Concentration',
            value: `${sim ? sim.disrupted_breakdown.trade : analysis.breakdown.trade}%`,
            delta: sim ? sim.disrupted_breakdown.trade - analysis.breakdown.trade : 0
        },
        {
            label: 'Corporate Exposure',
            value: `${sim ? sim.disrupted_breakdown.corporate : analysis.breakdown.corporate}%`,
            delta: sim ? sim.disrupted_breakdown.corporate - analysis.breakdown.corporate : 0
        },
        {
            label: 'Supply Risk',
            value: `${sim ? sim.disrupted_breakdown.substitutability : analysis.breakdown.substitutability}%`,
            delta: sim ? sim.disrupted_breakdown.substitutability - analysis.breakdown.substitutability : 0
        },
    ] : [
        { label: 'Risk Score', value: '0', delta: 0 },
        { label: 'Trade Concentration', value: '0%', delta: 0 },
        { label: 'Corporate Exposure', value: '0%', delta: 0 },
        { label: 'Supply Risk', value: '0%', delta: 0 },
    ];

    return (
        <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.4, ease: [0.2, 0, 0, 1] }}
            className={`grid grid-cols-1 gap-3 transition-opacity duration-300 ${isLoading ? 'opacity-50' : 'opacity-100'}`}
        >
            {metrics.map((m, i) => (
                <MetricCard key={i} {...m} />
            ))}
        </motion.div>
    );
};

export default MetricsPanel;
