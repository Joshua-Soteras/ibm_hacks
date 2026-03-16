import axios from "axios";

const API_URL = "http://localhost:8000";

export const getRoot = async () => {
    const response = await axios.get(API_URL);
    return response.data;
}

export const getHealth = async () => {
    const response = await axios.get(`${API_URL}/health`);
    console.log(response.data);
    return response.data;
}

