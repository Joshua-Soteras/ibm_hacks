import { motion } from "framer-motion";
import { Globe } from "lucide-react";

const RiskTable = ({ flows, isLoading }: { flows: any[]; isLoading: boolean }) => {
    return (
        <div className="card-surface h-full flex flex-col overflow-hidden">
            <div className="p-4 border-b border-secondary/20 flex items-center justify-between">
                <h3 className="text-[10px] text-muted-foreground uppercase font-bold tracking-widest">Trade Flow Risk Analysis</h3>
                <span className="text-[9px] font-mono text-muted-foreground">{flows.length > 0 ? `${flows.length} Active Vectors` : 'No data'}</span>
            </div>
            <div className="flex-1 overflow-y-auto px-4">
                {flows.length > 0 ? (
                    <table className="w-full text-left">
                        <thead className="sticky top-0 bg-background/80 backdrop-blur-sm z-10">
                            <tr className="text-[9px] text-muted-foreground uppercase tracking-wider border-b border-secondary/20">
                                <th className="py-3 font-bold">Mineral</th>
                                <th className="py-3 font-bold">Origin</th>
                                <th className="py-3 font-bold">Destination</th>
                                <th className="py-3 font-bold">Concentration</th>
                                <th className="py-3 font-bold">Risk Level</th>
                                <th className="py-3 font-bold">Status</th>
                                <th className="py-3 font-bold text-right">Lead Time</th>
                            </tr>
                        </thead>
                        <tbody>
                            {flows.map((flow, i) => (
                                <motion.tr
                                    key={i}
                                    initial={{ opacity: 0, y: 5 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    transition={{ delay: i * 0.05 }}
                                    className="text-[11px] border-b border-secondary/20 hover:bg-secondary/10 transition-colors cursor-pointer"
                                >
                                    <td className="py-2.5 font-medium text-foreground">{flow.mineral}</td>
                                    <td className="py-2.5 text-muted-foreground">{flow.country}</td>
                                    <td className="py-2.5 text-muted-foreground">USA</td>
                                    <td className="py-2.5">
                                        <div className="flex items-center gap-2">
                                            <div className="flex-1 h-1 bg-secondary/30 rounded-full overflow-hidden">
                                                <motion.div
                                                    className={`h-full ${flow.risk === 'high' ? 'bg-risk-high' : flow.risk === 'elevated' ? 'bg-risk-mid' : 'bg-risk-low'}`}
                                                    initial={{ width: 0 }}
                                                    animate={{ width: `${flow.share}%` }}
                                                    transition={{ duration: 0.6, delay: i * 0.05, ease: 'easeOut' }}
                                                />
                                            </div>
                                            <span className="font-mono tabular-nums min-w-[3ch]">{Math.round(flow.share)}%</span>
                                        </div>
                                    </td>
                                    <td className="py-2.5">
                                        <span className={`px-1.5 py-0.5 rounded-full text-[9px] uppercase font-bold border ${
                                            flow.risk === 'high' ? 'bg-risk-high/10 text-risk-high border-risk-high/20' :
                                            flow.risk === 'elevated' ? 'bg-risk-mid/10 text-risk-mid border-risk-mid/20' :
                                            'bg-risk-low/10 text-risk-low border-risk-low/20'
                                        }`}>
                                            {flow.risk}
                                        </span>
                                    </td>
                                    <td className="py-2.5 font-mono text-muted-foreground">ACTIVE</td>
                                    <td className="py-2.5 text-right font-mono text-muted-foreground">—</td>
                                </motion.tr>
                            ))}
                        </tbody>
                    </table>
                ) : (
                    <div className="h-full flex flex-col items-center justify-center gap-3 py-6">
                        <div className="w-10 h-10 rounded-full bg-secondary/20 flex items-center justify-center">
                            <Globe size={18} className="text-muted-foreground/50" />
                        </div>
                        <span className="text-[10px] font-mono text-muted-foreground text-center">
                            {isLoading ? "Processing trade flows..." : "Select a company to analyze supply chain risk."}
                        </span>
                    </div>
                )}
            </div>
        </div>
    );
};

export default RiskTable;
