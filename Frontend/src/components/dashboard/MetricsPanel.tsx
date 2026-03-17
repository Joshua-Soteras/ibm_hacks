import { motion, AnimatePresence } from "framer-motion";
import { Info } from "lucide-react";
import { Tooltip, TooltipTrigger, TooltipContent } from "@/components/ui/tooltip";
import type { SimulationResult } from "@/lib/api";

const METRIC_TOOLTIPS: Record<string, string> = {
    'Risk Score': 'Composite score (0\u2013100) weighting Trade (40%), Corporate (35%), and Substitutability (25%)',
    'Trade Concentration': 'Import concentration via HHI index, normalized using DOJ/FTC antitrust thresholds',
    'Corporate Exposure': 'Severity-weighted USGS supply risk across the company\u2019s mineral dependencies',
    'Supply Risk': 'USGS substitutability difficulty \u2014 how hard it is to find alternative sources',
};

const getRiskScoreColor = (value: string): string => {
    const num = parseInt(value, 10);
    if (isNaN(num)) return 'text-foreground';
    if (num > 70) return 'text-risk-high';
    if (num >= 30) return 'text-risk-mid';
    return 'text-risk-low';
};

const MetricCard = ({ label, value, delta, tooltip }: { label: string; value: string; delta: number; tooltip?: string }) => {
    const valueColor = label === 'Risk Score' ? getRiskScoreColor(value) : 'text-foreground';

    return (
        <div className="card-surface p-4">
            <div className="flex items-center gap-1">
                <span className="text-[10px] text-muted-foreground uppercase font-bold tracking-widest">{label}</span>
                {tooltip && (
                    <Tooltip>
                        <TooltipTrigger asChild>
                            <Info size={10} className="text-muted-foreground/50 cursor-help shrink-0" />
                        </TooltipTrigger>
                        <TooltipContent side="right" className="bg-card border border-secondary/40 text-foreground max-w-[220px] text-[10px]">
                            {tooltip}
                        </TooltipContent>
                    </Tooltip>
                )}
            </div>
            <div className="flex items-baseline gap-2 mt-1">
                <AnimatePresence mode="wait">
                    <motion.span
                        key={value}
                        initial={{ y: -8, opacity: 0 }}
                        animate={{ y: 0, opacity: 1 }}
                        exit={{ y: 8, opacity: 0 }}
                        transition={{ duration: 0.2 }}
                        className={`text-2xl font-mono tabular-nums ${valueColor}`}
                    >
                        {value}
                    </motion.span>
                </AnimatePresence>
                {delta !== 0 && (
                    <span className={`text-xs font-mono ${delta > 0 ? 'text-risk-high' : 'text-risk-low'}`}>
                        {delta > 0 ? '+' : ''}{delta}
                    </span>
                )}
            </div>
        </div>
    );
};

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
                <MetricCard key={i} {...m} tooltip={METRIC_TOOLTIPS[m.label]} />
            ))}
        </motion.div>
    );
};

export default MetricsPanel;
