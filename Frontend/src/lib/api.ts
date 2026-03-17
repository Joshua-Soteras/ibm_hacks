import axios from "axios";

export const API_URL = "http://localhost:8000";

export interface ScenarioCard {
    id: string;
    title: string;
    country: string;
    mineral: string;
    impact: "high" | "mid";
    top_share_pct: number;
}

export interface SimulationResult {
    company: string;
    baseline_score: number;
    disrupted_score: number;
    score_delta: number;
    severity: "critical" | "high" | "moderate" | "low";
    supply_gap_pct: number;
    disrupted_mineral: string;
    disrupted_country: string;
    disrupted_breakdown: {
        trade: number;
        corporate: number;
        substitutability: number;
    };
    disrupted_trade_flows: Array<{
        mineral: string;
        country: string;
        share: number;
        risk: string;
        status: "disrupted" | "stressed" | "active";
    }>;
}

export const getRoot = async () => {
    const response = await axios.get(API_URL);
    return response.data;
}

export const getHealth = async () => {
    const response = await axios.get(`${API_URL}/health`);
    return response.data;
}

export const fetchCompanies = async () => {
    const response = await axios.get(`${API_URL}/companies`);
    return response.data.companies;
}

export const fetchAnalyze = async (company: string) => {
    const response = await axios.get(`${API_URL}/analyze/${company}`);
    return response.data;
}

export const fetchCompanyScenarios = async (company: string): Promise<ScenarioCard[]> => {
    const response = await axios.get(`${API_URL}/api/company/scenarios/${company}`);
    return response.data.scenarios;
}

export const simulateDisruption = async (
    company: string,
    country: string,
    mineral: string,
    disruption_pct: number = 100.0
): Promise<SimulationResult> => {
    const response = await axios.post(`${API_URL}/api/simulate`, {
        company, country, mineral, disruption_pct
    });
    return response.data;
}

