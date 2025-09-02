import axios from "axios";

const http = axios.create({
    baseURL: import.meta.env.VITE_API_BASE ?? "/api",
    withCredentials: true,
    headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
    },
});

// ➜ Interceptor 401/403 : redirect to /login
http.interceptors.response.use(
    (r) => r,
    (err) => {
        const status = err?.response?.status;
        if (status === 401 || status === 403) {
        const url = new URL(window.location.href);
        
        if (!url.pathname.startsWith("/login")) {
            window.location.assign(
            `/login?redirect=${encodeURIComponent(url.pathname + url.search)}`
            );
        }
        }
        return Promise.reject(err);
    }
);

export default http;
