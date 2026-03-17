import { useState, useRef, useCallback } from "react";
import { API_URL } from "@/lib/api";
import type { SimulationResult } from "@/lib/api";
import type { AgentStepData } from "./useAnalysisStream";

const CUSTOM_STEPS: AgentStepData[] = [
    { id: "agent_reasoning", title: "Risk Orchestrator — Analyzing", status: "pending", trace: "> Awaiting scenario input...", timestamp: "--:--:--" },
    { id: "agent_response", title: "Risk Orchestrator — Response", status: "pending", trace: "> Awaiting analysis...", timestamp: "--:--:--" },
];

function now() {
    return new Date().toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

export function useCustomScenarioStream() {
    const [customSteps, setCustomSteps] = useState<AgentStepData[]>(CUSTOM_STEPS.map(s => ({ ...s })));
    const [isCustomStreaming, setIsCustomStreaming] = useState(false);
    const [customResult, setCustomResult] = useState<SimulationResult | null>(null);
    const eventSourceRef = useRef<EventSource | null>(null);

    const startCustomStream = useCallback((company: string, scenarioText: string) => {
        if (eventSourceRef.current) {
            eventSourceRef.current.close();
        }

        setCustomSteps(CUSTOM_STEPS.map(s => ({ ...s })));
        setCustomResult(null);
        setIsCustomStreaming(true);

        const url = `${API_URL}/api/custom-scenario-stream/${encodeURIComponent(company)}?scenario=${encodeURIComponent(scenarioText)}`;
        const es = new EventSource(url);
        eventSourceRef.current = es;

        es.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);

                if (data.stage === "complete") {
                    setCustomResult(data.result);
                    setIsCustomStreaming(false);
                    setCustomSteps(prev => prev.map(s => ({ ...s, status: "completed" as const })));
                    es.close();
                    return;
                }

                if (data.stage === "error") {
                    setIsCustomStreaming(false);
                    setCustomSteps(prev => prev.map(s =>
                        s.status === "active"
                            ? { ...s, status: "completed" as const, trace: `> Error: ${data.error || "Unknown error"}` }
                            : s
                    ));
                    es.close();
                    return;
                }

                // Update matching step
                setCustomSteps(prev => prev.map(s => {
                    if (s.id === data.stage) {
                        return {
                            ...s,
                            title: data.title || s.title,
                            status: data.status as "active" | "completed",
                            trace: data.trace || s.trace,
                            timestamp: now(),
                            full_output: data.full_output || s.full_output,
                        };
                    }
                    return s;
                }));
            } catch {
                // ignore parse errors
            }
        };

        es.onerror = () => {
            setIsCustomStreaming(false);
            es.close();
        };
    }, []);

    const resetCustom = useCallback(() => {
        if (eventSourceRef.current) {
            eventSourceRef.current.close();
            eventSourceRef.current = null;
        }
        setCustomSteps(CUSTOM_STEPS.map(s => ({ ...s })));
        setCustomResult(null);
        setIsCustomStreaming(false);
    }, []);

    return { customSteps, isCustomStreaming, customResult, startCustomStream, resetCustom };
}
