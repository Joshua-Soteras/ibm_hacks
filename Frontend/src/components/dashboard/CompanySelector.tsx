import { ChevronDown, Search } from 'lucide-react';

interface CompanySelectorProps {
    companies: string[];
    onSelect: (company: string) => void;
    selectedCompany: string | null;
}

const CompanySelector = ({ companies, onSelect, selectedCompany }: CompanySelectorProps) => {
    return (
        <div className="space-y-2">
            <div className="flex items-center gap-1.5 pl-1">
                <Search size={9} className="text-muted-foreground" />
                <label className="text-[10px] text-muted-foreground uppercase font-bold tracking-widest">
                    Analyze Target
                </label>
            </div>
            <div className="relative group">
                <select
                    value={selectedCompany || ""}
                    onChange={(e) => onSelect(e.target.value)}
                    className="w-full h-10 bg-secondary/20 hover:bg-secondary/40 border border-secondary/40 hover:border-primary/40 rounded-lg px-3 pr-8 text-xs text-foreground appearance-none cursor-pointer focus:outline-none focus:ring-1 focus:ring-primary/50 focus:border-primary/50 transition-all duration-200"
                >
                    <option value="" disabled className="bg-background text-muted-foreground">Select a company...</option>
                    {companies.map((company) => (
                        <option key={company} value={company} className="bg-background py-2">
                            {company}
                        </option>
                    ))}
                </select>
                <div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-muted-foreground group-hover:text-foreground transition-colors">
                    <ChevronDown size={13} />
                </div>
            </div>
            {companies.length === 0 && (
                <p className="text-[9px] font-mono text-muted-foreground/60 pl-1">Connecting to backend...</p>
            )}
        </div>
    );
};

export default CompanySelector;
