import axios from 'axios';

// Backend adresimiz
const API_BASE_URL = 'http://127.0.0.1:8000';

const api = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

export const uploadDocument = async (file) => {
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

// Geriye dönük uyumluluk için eski fonksiyon adını da tutuyoruz
export const uploadPDF = uploadDocument;

export const getDocuments = async () => {
    const response = await api.get('/documents');
    return response.data;
};

export const askQuestion = async (question, docId = null) => {
    const response = await api.post('/ask', { 
        question,
        doc_id: docId 
    });
    return response.data;
};

export default api;