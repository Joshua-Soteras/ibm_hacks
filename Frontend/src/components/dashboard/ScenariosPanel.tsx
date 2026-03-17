import { motion } from "framer-motion";

const Sparkline = ({ data }: { data: number[] }) => {
    const max = Math.max(...data);
    const min = Math.min(...data);
    const range = max - min || 1;
    const h = 24;
    const w = 80;
    const points = data.map((v, i) => `${(i / (data.length - 1)) * w},${h - ((v - min) / range) * h}`).join(' ');

    return (
        <svg width={w} height={h} className="overflow-visible">
            <polyline points={points} fill="none" stroke="currentColor" strokeWidth="1.5" />
        </svg>
    );
};

const ScenariosPanel = ({ scenarios }: { scenarios: any[] }) => {
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
            <h3 className="text-[10px] text-muted-foreground uppercase font-bold tracking-widest px-1">Probable Scenarios</h3>
            {scenarios.map((s) => (
                <div
                    key={s.id}
                    className={`card-surface p-3 risk-border-${s.impact} cursor-pointer hover:bg-secondary/50 transition-colors duration-200`}
                >
                    <div className="flex items-start justify-between gap-2">
                        <div className="flex-1 min-w-0">
                            <h4 className="text-xs font-medium text-foreground truncate">{s.title}</h4>
                            <div className="flex items-center gap-3 mt-1.5">
                                <span className="text-[10px] text-muted-foreground">
                                    P: <span className="font-mono text-foreground">{s.probability}%</span>
                                </span>
                                <span className={`text-[10px] font-mono ${s.costDelta > 0 ? 'text-risk-high' : 'text-risk-low'}`}>
                                    {s.costDelta > 0 ? '+' : ''}{s.costDelta}M
                                </span>
                            </div>
                        </div>
                        <div className={s.costDelta > 0 ? 'text-risk-high' : 'text-risk-low'}>
                            <Sparkline data={s.sparkline} />
                        </div>
                    </div>
                </div>
            ))}
        </motion.div>
    );
};

export default ScenariosPanel;
