import axios from 'axios';

// Backend adresimiz
const API_BASE_URL = 'http://127.0.0.1:8000';

const api = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

export const uploadPDF = async (file) => {
    const formData = new FormData();
    formData.append('file', file);

    // Dosya yükleme "multipart/form-data" ister
    const response = await api.post('/upload', formData, {
        headers: {
            'Content-Type': 'multipart/form-data',
        },
    });
    return response.data;
};

export const askQuestion = async (question) => {
    const response = await api.post('/ask', { question });
    return response.data;
};

export default api;