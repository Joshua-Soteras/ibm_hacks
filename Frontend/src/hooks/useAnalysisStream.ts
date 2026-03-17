import { useState, useRef, useCallback } from "react";
import { API_URL } from "@/lib/api";

export interface AgentStepData {
    id: string;
    title: string;
    status: "pending" | "active" | "completed";
    trace: string;
    timestamp: string;
}

const INITIAL_STEPS: AgentStepData[] = [
    { id: "orchestrator_planning", title: "Risk Orchestrator", status: "pending", trace: "> Awaiting dispatch...", timestamp: "--:--:--" },
    { id: "trade_intel", title: "Trade Intelligence Agent", status: "pending", trace: "> Awaiting dispatch...", timestamp: "--:--:--" },
    { id: "corporate_exposure", title: "Corporate Exposure Agent", status: "pending", trace: "> Awaiting dispatch...", timestamp: "--:--:--" },
    { id: "orchestrator_scoring", title: "Risk Orchestrator — Scoring", status: "pending", trace: "> Awaiting dispatch...", timestamp: "--:--:--" },
];

function now() {
    return new Date().toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

export function useAnalysisStream() {
    const [steps, setSteps] = useState<AgentStepData[]>(INITIAL_STEPS);
    const [isStreaming, setIsStreaming] = useState(false);
    const [analysisResult, setAnalysisResult] = useState<any>(null);
    const eventSourceRef = useRef<EventSource | null>(null);

    const startStream = useCallback((company: string) => {
        // Close any existing connection
        if (eventSourceRef.current) {
            eventSourceRef.current.close();
        }

        setSteps(INITIAL_STEPS.map(s => ({ ...s })));
        setAnalysisResult(null);
        setIsStreaming(true);

        const es = new EventSource(`${API_URL}/api/analyze-stream/${encodeURIComponent(company)}`);
        eventSourceRef.current = es;

        es.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);

                if (data.stage === "complete") {
                    setAnalysisResult(data.result);
                    setIsStreaming(false);
                    setSteps(prev => prev.map(s => ({ ...s, status: "completed" as const })));
                    es.close();
                    return;
                }

                if (data.stage === "error") {
                    setIsStreaming(false);
                    es.close();
                    return;
                }

                // Update matching step
                setSteps(prev => prev.map(s => {
                    if (s.id === data.stage) {
                        return {
                            ...s,
                            title: data.title || s.title,
                            status: data.status as "active" | "completed",
                            trace: data.trace || s.trace,
                            timestamp: now(),
                        };
                    }
                    return s;
                }));
            } catch {
                // ignore parse errors
            }
        };

        es.onerror = () => {
            setIsStreaming(false);
            es.close();
        };
    }, []);

    const reset = useCallback(() => {
        if (eventSourceRef.current) {
            eventSourceRef.current.close();
            eventSourceRef.current = null;
        }
        setSteps(INITIAL_STEPS.map(s => ({ ...s })));
        setAnalysisResult(null);
        setIsStreaming(false);
    }, []);

    return { steps, isStreaming, analysisResult, startStream, reset };
}
