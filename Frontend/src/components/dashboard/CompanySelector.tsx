import { ChevronDown } from 'lucide-react';

interface CompanySelectorProps {
    companies: string[];
    onSelect: (company: string) => void;
    selectedCompany: string | null;
}

const CompanySelector = ({ companies, onSelect, selectedCompany }: CompanySelectorProps) => {
    return (
        <div className="space-y-2">
            <label className="text-[10px] text-muted-foreground uppercase font-bold tracking-widest pl-1">
                Select Analyze Target
            </label>
            <div className="relative group">
                <select
                    value={selectedCompany || ""}
                    onChange={(e) => onSelect(e.target.value)}
                    className="w-full h-9 bg-secondary/20 hover:bg-secondary/30 border border-secondary/40 rounded-md px-3 text-xs text-foreground appearance-none cursor-pointer focus:outline-none focus:ring-1 focus:ring-primary/50 transition-all duration-200"
                >
                    <option value="" disabled className="bg-background">Select a company...</option>
                    {companies.map((company) => (
                        <option key={company} value={company} className="bg-background py-2">
                            {company}
                        </option>
                    ))}
                </select>
                <div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-muted-foreground group-hover:text-foreground transition-colors">
                    <ChevronDown size={14} />
                </div>
            </div>
        </div>
    );
};

export default CompanySelector;
