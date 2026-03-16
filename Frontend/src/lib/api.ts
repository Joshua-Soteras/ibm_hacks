import axios from "axios";

const API_URL = "http://localhost:8000";

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

