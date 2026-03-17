import ReactMarkdown from "react-markdown";

const Markdown = ({ children, className = "" }: { children: string; className?: string }) => (
    <div className={`prose-sm prose-invert max-w-none
        [&_p]:text-[10px] [&_p]:font-mono [&_p]:text-muted-foreground [&_p]:leading-relaxed [&_p]:my-1
        [&_strong]:text-foreground [&_strong]:font-semibold
        [&_em]:text-muted-foreground/80
        [&_ul]:text-[10px] [&_ul]:font-mono [&_ul]:text-muted-foreground [&_ul]:my-1 [&_ul]:pl-3 [&_ul]:list-disc
        [&_ol]:text-[10px] [&_ol]:font-mono [&_ol]:text-muted-foreground [&_ol]:my-1 [&_ol]:pl-3 [&_ol]:list-decimal
        [&_li]:my-0.5
        [&_h1]:text-xs [&_h1]:font-semibold [&_h1]:text-foreground [&_h1]:mt-2 [&_h1]:mb-1
        [&_h2]:text-[11px] [&_h2]:font-semibold [&_h2]:text-foreground [&_h2]:mt-2 [&_h2]:mb-1
        [&_h3]:text-[10px] [&_h3]:font-semibold [&_h3]:text-foreground [&_h3]:mt-1.5 [&_h3]:mb-0.5
        [&_code]:text-[9px] [&_code]:bg-secondary/20 [&_code]:px-1 [&_code]:py-0.5 [&_code]:rounded [&_code]:text-primary/80
        [&_pre]:bg-secondary/10 [&_pre]:p-2 [&_pre]:rounded [&_pre]:border [&_pre]:border-secondary/20 [&_pre]:my-1 [&_pre]:overflow-x-auto
        [&_pre_code]:bg-transparent [&_pre_code]:p-0
        [&_a]:text-primary/80 [&_a]:underline [&_a]:underline-offset-2
        [&_blockquote]:border-l-2 [&_blockquote]:border-primary/30 [&_blockquote]:pl-2 [&_blockquote]:my-1 [&_blockquote]:italic
        [&_table]:text-[9px] [&_table]:font-mono [&_th]:text-left [&_th]:pr-3 [&_th]:text-foreground [&_td]:pr-3
        [&_hr]:border-secondary/20 [&_hr]:my-2
        ${className}`}
    >
        <ReactMarkdown>{children}</ReactMarkdown>
    </div>
);

export default Markdown;
