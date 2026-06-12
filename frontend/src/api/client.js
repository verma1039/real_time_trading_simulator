import axios from 'axios';

// In-memory storage for the access token
let currentAccessToken = null;

export const setAccessToken = (token) => {
  currentAccessToken = token;
};

export const getAccessToken = () => currentAccessToken;

export const client = axios.create({
  baseURL: '/api/v1',
  withCredentials: true, // Necessary for the HttpOnly refresh token cookie
  headers: {
    'Content-Type': 'application/json',
  },
});

// Attach the access token to every outgoing request if we have it
client.interceptors.request.use(
  (config) => {
    if (currentAccessToken) {
      config.headers['Authorization'] = `Bearer ${currentAccessToken}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// State for managing concurrent refresh requests
let isRefreshing = false;
let failedQueue = [];

const processQueue = (error, token = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

// Handle 401 Unauthorized responses and trigger token refresh
client.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // Prevent infinite loops on auth endpoints
    if (originalRequest.url === '/auth/refresh' || originalRequest.url === '/auth/login' || originalRequest.url === '/auth/logout') {
      return Promise.reject(error);
    }

    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        try {
          const token = await new Promise((resolve, reject) => {
            failedQueue.push({ resolve, reject });
          });
          originalRequest.headers['Authorization'] = `Bearer ${token}`;
          return client(originalRequest);
        } catch (err) {
          return Promise.reject(err);
        }
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        const { data } = await client.post('/auth/refresh');
        const newToken = data.access_token;
        
        setAccessToken(newToken);
        processQueue(null, newToken);
        
        originalRequest.headers['Authorization'] = `Bearer ${newToken}`;
        return client(originalRequest);
      } catch (err) {
        processQueue(err, null);
        setAccessToken(null);
        // We do not redirect to login here to keep the API client decoupled from the React router/context
        // The AuthContext will catch this failure and clear its state.
        return Promise.reject(err);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);
