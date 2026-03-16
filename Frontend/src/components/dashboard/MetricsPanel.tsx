import { motion } from "framer-motion";
import { metrics } from "@/data/simulatedData";

const MetricCard = ({ label, value, delta }: { label: string; value: string; delta: number }) => (
    <div className="card-surface p-4">
        <span className="text-[10px] text-muted-foreground uppercase font-bold tracking-widest">{label}</span>
        <div className="flex items-baseline gap-2 mt-1">
            <span className="text-2xl font-mono text-foreground tabular-nums">{value}</span>
            <span className={`text-xs font-mono ${delta > 0 ? 'text-risk-high' : 'text-risk-low'}`}>
                {delta > 0 ? '↑' : '↓'}{Math.abs(delta)}%
            </span>
        </div>
    </div>
);

const MetricsPanel = () => {
    return (
        <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.4, ease: [0.2, 0, 0, 1] }}
            className="grid grid-cols-1 gap-3"
        >
            {metrics.map((m, i) => (
                <MetricCard key={i} {...m} />
            ))}
        </motion.div>
    );
};

export default MetricsPanel;
