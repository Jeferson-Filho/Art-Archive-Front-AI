import axios from "axios";

const axiosInstance = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL,
  timeout: 10000
});

/**
 * For the AI-generated Insight Card endpoints (doc 99, Decision 6). A first
 * visit may spend up to 60s generating (RNF-002), after the backend's own
 * checks — database up to 8s, Harvard up to 10s. The 10s limit above would
 * abort nearly every first visit; 90s lets the backend answer first,
 * including with its own 504 GENERATION_TIMEOUT.
 */
export const aiAxiosInstance = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL,
  timeout: 90000
});

export default axiosInstance;
