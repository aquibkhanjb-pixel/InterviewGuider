import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor
api.interceptors.request.use(
  (config) => {
    console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => {
    console.error('API Request Error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor
api.interceptors.response.use(
  (response) => {
    console.log(`API Response: ${response.status} ${response.config.url}`);
    return response;
  },
  (error) => {
    console.error('API Response Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

export const interviewAPI = {
  healthCheck: () => api.get('/api/health/'),
  getCompanies: () => api.get('/api/companies/'),
  getCompanyExperiences: (company, options = {}) => {
    const { limit = 50, offset = 0 } = options;
    return api.get(`/api/companies/${company}/experiences?limit=${limit}&offset=${offset}`);
  },
  getCompanyInsights: (company) => api.get(`/api/insights/${company}`),
  getRecommendations: (company) => api.get(`/api/insights/${company}/recommendations`),
  triggerAnalysis: (company, options = {}) =>
    api.post(`/api/analysis/${company}`, options),
  getJobStatus: (jobId) => api.get(`/api/analysis/job/${jobId}`),
  getAnalysisStatus: () => api.get('/api/analysis/status'),
  compareCompanies: (companies) => 
    api.post('/api/compare/', { companies }),
};