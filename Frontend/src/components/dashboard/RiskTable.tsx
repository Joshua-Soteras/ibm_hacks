import { motion } from "framer-motion";
import { riskEntries } from "@/data/simulatedData";

const riskLevelColor = (level: string) => {
    switch (level) {
        case 'high': return 'text-risk-high';
        case 'mid': return 'text-risk-mid';
        case 'low': return 'text-risk-low';
        default: return 'text-muted-foreground';
    }
};

const RiskTable = () => {
    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.2, ease: [0.2, 0, 0, 1] }}
            className="card-surface p-4 h-full flex flex-col"
        >
            <div className="flex items-center justify-between mb-3">
                <h3 className="text-[10px] text-muted-foreground uppercase font-bold tracking-widest">Risk Analysis</h3>
                <span className="text-[9px] font-mono text-risk-high px-2 py-0.5 rounded-full bg-risk-high/10">
                    2 Critical
                </span>
            </div>
            <div className="flex-1 overflow-auto">
                <table className="w-full text-xs">
                    <thead>
                        <tr className="text-[9px] text-muted-foreground uppercase tracking-wider border-b border-border">
                            <th className="text-left py-2 font-medium">Component</th>
                            <th className="text-left py-2 font-medium">Route</th>
                            <th className="text-center py-2 font-medium">Score</th>
                            <th className="text-left py-2 font-medium">Category</th>
                            <th className="text-left py-2 font-medium">Status</th>
                            <th className="text-right py-2 font-medium">ΔLead</th>
                        </tr>
                    </thead>
                    <tbody>
                        {riskEntries.map((r) => (
                            <tr key={r.id} className="border-b border-border/50 hover:bg-secondary/30 transition-colors duration-150 cursor-pointer">
                                <td className="py-2.5 font-mono font-medium text-foreground">{r.component}</td>
                                <td className="py-2.5 text-muted-foreground">
                                    <span className="text-foreground/70">{r.origin}</span>
                                    <span className="text-muted-foreground mx-1">→</span>
                                    <span className="text-foreground/70">{r.destination}</span>
                                </td>
                                <td className="py-2.5 text-center">
                                    <span className={`font-mono font-semibold ${riskLevelColor(r.riskLevel)}`}>{r.riskScore}</span>
                                </td>
                                <td className="py-2.5 text-muted-foreground">{r.category}</td>
                                <td className="py-2.5">
                                    <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium
                    ${r.riskLevel === 'high' ? 'bg-risk-high/10 text-risk-high' : ''}
                    ${r.riskLevel === 'mid' ? 'bg-risk-mid/10 text-risk-mid' : ''}
                    ${r.riskLevel === 'low' ? 'bg-risk-low/10 text-risk-low' : ''}
                  `}>
                                        {r.status}
                                    </span>
                                </td>
                                <td className={`py-2.5 text-right font-mono ${r.leadTimeDelta.startsWith('+') ? 'text-risk-high' : 'text-risk-low'}`}>
                                    {r.leadTimeDelta}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </motion.div>
    );
};

export default RiskTable;
