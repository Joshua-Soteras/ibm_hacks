export interface SupplyRoute {
    startLat: number;
    startLng: number;
    endLat: number;
    endLng: number;
    color: string;
    label: string;
    riskLevel: 'high' | 'mid' | 'low';
}

export interface AgentStep {
    id: string;
    title: string;
    status: 'completed' | 'active' | 'pending';
    trace: string;
    timestamp: string;
}

export interface Scenario {
    id: string;
    title: string;
    impact: 'high' | 'mid' | 'low';
    probability: number;
    costDelta: number;
    sparkline: number[];
}

export interface RiskEntry {
    id: string;
    component: string;
    origin: string;
    destination: string;
    riskScore: number;
    riskLevel: 'high' | 'mid' | 'low';
    category: string;
    status: string;
    leadTimeDelta: string;
}

export interface Metric {
    label: string;
    value: string;
    delta: number;
    unit?: string;
}

export const supplyRoutes: SupplyRoute[] = [
    { startLat: 25.03, startLng: 121.56, endLat: 30.27, endLng: -97.74, color: '#ef4444', label: 'TSMC → Austin', riskLevel: 'high' },
    { startLat: 37.56, startLng: 126.97, endLat: 52.52, endLng: 13.40, color: '#f59e0b', label: 'Samsung → Berlin', riskLevel: 'mid' },
    { startLat: 22.30, startLng: 114.17, endLat: 34.05, endLng: -118.24, color: '#22c55e', label: 'Shenzhen → LA', riskLevel: 'low' },
    { startLat: 35.68, startLng: 139.69, endLat: 48.86, endLng: 2.35, color: '#ef4444', label: 'Tokyo → Paris', riskLevel: 'high' },
    { startLat: 1.35, startLng: 103.82, endLat: 51.51, endLng: -0.13, color: '#f59e0b', label: 'Singapore → London', riskLevel: 'mid' },
    { startLat: 13.08, startLng: 80.27, endLat: 37.77, endLng: -122.42, color: '#22c55e', label: 'Chennai → San Francisco', riskLevel: 'low' },
];

export const agentSteps: AgentStep[] = [
    { id: '1', title: 'Data Ingestion Agent', status: 'completed', trace: '> Fetched 14,302 shipment records from ERP\n> Cross-referenced 3 carrier APIs\n> Anomaly detected: Route 402 latency +38h', timestamp: '14:32:01' },
    { id: '2', title: 'Risk Assessment Agent', status: 'completed', trace: '> Scoring geopolitical risk factors...\n> Taiwan Strait tension index: 0.82/1.0\n> Semiconductor supply elasticity: LOW', timestamp: '14:32:18' },
    { id: '3', title: 'Logistics Optimizer', status: 'active', trace: '> Recalculating lead times for Route 402\n> Alt route via Vietnam: +$2.4M, -12 days\n> Alt route via Malaysia: +$1.8M, -8 days', timestamp: '14:32:45' },
    { id: '4', title: 'Scenario Modeler', status: 'pending', trace: '> Awaiting optimized route data...\n> Will generate 3 scenario projections', timestamp: '--:--:--' },
    { id: '5', title: 'Executive Briefer', status: 'pending', trace: '> Pending scenario analysis\n> Will compile risk summary for C-suite', timestamp: '--:--:--' },
];

export const scenarios: Scenario[] = [
    { id: '1', title: 'Taiwan Strait Disruption', impact: 'high', probability: 34, costDelta: 12.4, sparkline: [2, 4, 3, 8, 12, 15, 14, 18] },
    { id: '2', title: 'Port Congestion (LA/LB)', impact: 'mid', probability: 62, costDelta: 4.2, sparkline: [1, 2, 3, 4, 5, 6, 5, 7] },
    { id: '3', title: 'Carrier Rate Surge Q2', impact: 'mid', probability: 78, costDelta: 2.8, sparkline: [3, 3, 4, 5, 4, 6, 7, 8] },
    { id: '4', title: 'Alternative Supplier Online', impact: 'low', probability: 45, costDelta: -3.1, sparkline: [8, 7, 6, 5, 4, 3, 3, 2] },
];

export const riskEntries: RiskEntry[] = [
    { id: '1', component: 'Semiconductor-X9', origin: 'Taipei, TW', destination: 'Austin, TX', riskScore: 92, riskLevel: 'high', category: 'Geopolitical', status: 'Mitigating', leadTimeDelta: '+38h' },
    { id: '2', component: 'OLED Panel v3', origin: 'Seoul, KR', destination: 'Berlin, DE', riskScore: 67, riskLevel: 'mid', category: 'Logistics', status: 'Monitoring', leadTimeDelta: '+12h' },
    { id: '3', component: 'Li-Ion Cell Pack', origin: 'Shenzhen, CN', destination: 'Los Angeles, CA', riskScore: 31, riskLevel: 'low', category: 'Supply', status: 'Stable', leadTimeDelta: '-2h' },
    { id: '4', component: 'Precision Optics M7', origin: 'Tokyo, JP', destination: 'Paris, FR', riskScore: 85, riskLevel: 'high', category: 'Geopolitical', status: 'Escalated', leadTimeDelta: '+52h' },
    { id: '5', component: 'RF Module K2', origin: 'Singapore, SG', destination: 'London, UK', riskScore: 54, riskLevel: 'mid', category: 'Regulatory', status: 'Under Review', leadTimeDelta: '+8h' },
];

export const metrics: Metric[] = [
    { label: 'Active Routes', value: '2,847', delta: -3.2 },
    { label: 'At-Risk Shipments', value: '142', delta: 18.4 },
    { label: 'Avg Lead Time', value: '14.2d', delta: 8.1 },
    { label: 'Cost Exposure', value: '$24.8M', delta: 12.4 },
];
