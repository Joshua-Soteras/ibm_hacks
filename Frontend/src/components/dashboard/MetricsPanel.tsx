import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown } from "lucide-react";

const DESCRIPTIONS: Record<string, { what: string; how: string; range: string }> = {
    'Risk Score': {
        what: 'A weighted composite of trade concentration, corporate exposure, and substitutability.',
        how: 'Calculated as 40% trade concentration + 35% corporate exposure + 25% substitutability penalty.',
        range: '0 = no risk · 100 = maximum risk',
    },
    'Trade Concentration': {
        what: 'How dependent the U.S. is on a single country for critical mineral imports.',
        how: 'Derived from the Herfindahl-Hirschman Index (HHI) of USITC import data. Higher = more concentrated.',
        range: '0% = diversified · 100% = single-source monopoly',
    },
    'Corporate Exposure': {
        what: "How much this company's SEC filings mention critical mineral dependencies.",
        how: 'Based on keyword frequency and risk language in 10-K filings from EDGAR. Weighted by mineral supply risk.',
        range: '0% = no mentions · 100% = high dependency language',
    },
    'Substitute Readiness': {
        what: 'How easily the minerals this company relies on can be replaced with alternatives.',
        how: 'Sourced from USGS substitutability ratings. Low score = hard to substitute.',
        range: '0% = no substitutes · 100% = easy to replace',
    },
};

const RiskGauge = ({ score }: { score: number }) => {
    const [open, setOpen] = useState(false);
    const size = 80;
    const strokeWidth = 7;
    const radius = (size - strokeWidth) / 2;
    const circumference = 2 * Math.PI * radius;
    const arc = circumference * 0.75;
    const progress = (score / 100) * arc;
    const color = score > 70 ? '#ef4444' : score > 40 ? '#f59e0b' : '#22c55e';
    const label = score > 70 ? 'Critical' : score > 40 ? 'Elevated' : 'Stable';
    const desc = DESCRIPTIONS['Risk Score'];

    return (
        <div
            className="card-surface p-4 cursor-pointer hover:bg-secondary/10 transition-colors duration-200"
            onClick={() => setOpen(o => !o)}
        >
            <div className="flex items-center gap-4">
                <div className="relative flex-shrink-0" style={{ width: size, height: size }}>
                    <svg width={size} height={size} style={{ transform: 'rotate(135deg)' }}>
                        <circle cx={size / 2} cy={size / 2} r={radius} fill="none"
                            stroke="rgba(255,255,255,0.06)" strokeWidth={strokeWidth}
                            strokeDasharray={`${arc} ${circumference}`} strokeLinecap="round" />
                        <circle cx={size / 2} cy={size / 2} r={radius} fill="none"
                            stroke={color} strokeWidth={strokeWidth}
                            strokeDasharray={`${progress} ${circumference}`} strokeLinecap="round"
                            style={{ filter: `drop-shadow(0 0 4px ${color})`, transition: 'stroke-dasharray 0.8s ease' }} />
                    </svg>
                    <div className="absolute inset-0 flex flex-col items-center justify-center" style={{ paddingBottom: 4 }}>
                        <span className="text-lg font-mono font-bold tabular-nums text-foreground leading-none">{score}</span>
                        <span className="text-[8px] font-mono uppercase tracking-wider mt-0.5" style={{ color }}>{label}</span>
                    </div>
                </div>
                <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                        <span className="text-[10px] text-muted-foreground uppercase font-bold tracking-widest">Risk Score</span>
                        <ChevronDown size={12} className={`text-muted-foreground transition-transform duration-200 ${open ? 'rotate-180' : ''}`} />
                    </div>
                    <span className="text-[10px] font-mono text-muted-foreground mt-1 block">Composite index</span>
                    <span className="text-[10px] font-mono mt-1 block" style={{ color }}>
                        {score > 50 ? '↑' : '↓'}{score > 50 ? score - 50 : 50 - score}pts vs baseline
                    </span>
                </div>
            </div>
            <AnimatePresence>
                {open && (
                    <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        transition={{ duration: 0.2 }}
                        className="overflow-hidden"
                    >
                        <div className="mt-3 pt-3 border-t border-secondary/20 space-y-1.5">
                            <p className="text-[10px] text-foreground/80 leading-relaxed">{desc.what}</p>
                            <p className="text-[10px] font-mono text-muted-foreground leading-relaxed">{desc.how}</p>
                            <p className="text-[9px] font-mono text-muted-foreground/60 mt-1">{desc.range}</p>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
};

const MetricCard = ({ label, value, delta, accent }: { label: string; value: string; delta: number; accent: string }) => {
    const [open, setOpen] = useState(false);
    const desc = DESCRIPTIONS[label];

    return (
        <div
            className="card-surface p-4 cursor-pointer hover:bg-secondary/10 transition-colors duration-200"
            style={{ borderLeft: `2px solid ${accent}` }}
            onClick={() => setOpen(o => !o)}
        >
            <div className="flex items-center justify-between">
                <span className="text-[10px] text-muted-foreground uppercase font-bold tracking-widest">{label}</span>
                <ChevronDown size={12} className={`text-muted-foreground transition-transform duration-200 ${open ? 'rotate-180' : ''}`} />
            </div>
            <div className="flex items-baseline gap-2 mt-1">
                <span className="text-2xl font-mono text-foreground tabular-nums">{value}</span>
                <span className={`text-xs font-mono ${delta > 0 ? 'text-risk-high' : 'text-risk-low'}`}>
                    {delta > 0 ? '↑' : '↓'}{Math.abs(delta)}%
                </span>
            </div>
            <AnimatePresence>
                {open && desc && (
                    <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        transition={{ duration: 0.2 }}
                        className="overflow-hidden"
                    >
                        <div className="mt-3 pt-3 border-t border-secondary/20 space-y-1.5">
                            <p className="text-[10px] text-foreground/80 leading-relaxed">{desc.what}</p>
                            <p className="text-[10px] font-mono text-muted-foreground leading-relaxed">{desc.how}</p>
                            <p className="text-[9px] font-mono text-muted-foreground/60">{desc.range}</p>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
};

const MetricsPanel = ({ analysis, isLoading }: { analysis: any; isLoading: boolean }) => {
    const subMetrics = analysis ? [
        { label: 'Trade Concentration', value: `${analysis.breakdown.trade}%`, delta: 2.1, accent: analysis.breakdown.trade > 60 ? '#ef4444' : analysis.breakdown.trade > 40 ? '#f59e0b' : '#22c55e' },
        { label: 'Corporate Exposure', value: `${analysis.breakdown.corporate}%`, delta: 5.4, accent: analysis.breakdown.corporate > 60 ? '#ef4444' : analysis.breakdown.corporate > 40 ? '#f59e0b' : '#22c55e' },
        { label: 'Substitute Readiness', value: `${analysis.breakdown.substitutability}%`, delta: -1.2, accent: '#3b82f6' },
    ] : [
        { label: 'Trade Concentration', value: '—', delta: 0, accent: 'rgba(255,255,255,0.08)' },
        { label: 'Corporate Exposure', value: '—', delta: 0, accent: 'rgba(255,255,255,0.08)' },
        { label: 'Substitute Readiness', value: '—', delta: 0, accent: 'rgba(255,255,255,0.08)' },
    ];

    return (
        <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.4, ease: [0.2, 0, 0, 1] }}
            className={`grid grid-cols-1 gap-3 transition-opacity duration-300 ${isLoading ? 'opacity-50' : 'opacity-100'}`}
        >
            {analysis ? (
                <RiskGauge score={analysis.score} />
            ) : (
                <div className="card-surface p-4 flex items-center gap-4" style={{ borderLeft: '2px solid rgba(255,255,255,0.08)' }}>
                    <div className="w-[80px] h-[80px] flex-shrink-0 rounded-full border-2 border-secondary/20 flex items-center justify-center">
                        <span className="text-[10px] font-mono text-muted-foreground">—</span>
                    </div>
                    <div>
                        <span className="text-[10px] text-muted-foreground uppercase font-bold tracking-widest block">Risk Score</span>
                        <span className="text-[10px] font-mono text-muted-foreground mt-1 block">No company selected</span>
                    </div>
                </div>
            )}
            {subMetrics.map((m, i) => (
                <MetricCard key={i} {...m} />
            ))}
        </motion.div>
    );
};

export default MetricsPanel;
