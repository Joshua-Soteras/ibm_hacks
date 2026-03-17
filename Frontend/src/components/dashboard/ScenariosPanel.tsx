import { motion } from "framer-motion";

const Sparkline = ({ data, positive }: { data: number[]; positive: boolean }) => {
    const max = Math.max(...data);
    const min = Math.min(...data);
    const range = max - min || 1;
    const w = 100;
    const h = 36;
    const pts = data.map((v, i) => [
        (i / (data.length - 1)) * w,
        h - ((v - min) / range) * (h - 4) - 2
    ]);
    const polyline = pts.map(([x, y]) => `${x},${y}`).join(' ');
    const area = [
        `0,${h}`,
        ...pts.map(([x, y]) => `${x},${y}`),
        `${w},${h}`
    ].join(' ');
    const stroke = positive ? '#ef4444' : '#22c55e';
    const fillId = `fill-${Math.random().toString(36).slice(2)}`;

    return (
        <svg width={w} height={h} className="overflow-visible flex-shrink-0">
            <defs>
                <linearGradient id={fillId} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={stroke} stopOpacity="0.25" />
                    <stop offset="100%" stopColor={stroke} stopOpacity="0" />
                </linearGradient>
            </defs>
            <polygon points={area} fill={`url(#${fillId})`} />
            <polyline points={polyline} fill="none" stroke={stroke} strokeWidth="1.5" strokeLinejoin="round" strokeLinecap="round" />
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
                                <span className={`text-[10px] font-mono font-semibold ${s.costDelta > 0 ? 'text-risk-high' : 'text-risk-low'}`}>
                                    {s.costDelta > 0 ? '+' : ''}${s.costDelta}M
                                </span>
                            </div>
                        </div>
                        <Sparkline data={s.sparkline} positive={s.costDelta > 0} />
                    </div>
                </div>
            ))}
        </motion.div>
    );
};

export default ScenariosPanel;
