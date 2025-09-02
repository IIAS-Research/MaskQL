import http from "./http";

export function adminLogin(username: string, password: string) {
    return http.post("/admin/login", {}, { auth: { username, password } });
}

export function adminLogout() {
    return http.post("/admin/logout", {});
}

export function getAdminHealth() {
    return http.get("/admin/health");
}
