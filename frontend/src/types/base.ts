import http from "../http";

export abstract class BaseResource<T extends { id?: number | string }, C = Partial<T>, U = Partial<T>> {
    protected endpoint: string;

    constructor(endpoint: string) {
        this.endpoint = endpoint.replace(/\/+$/, ""); // sans slash final
    }

    async list(params?: Record<string, unknown>): Promise<T[]> {
        const { data } = await http.get<T[]>(this.endpoint, { params });
        return data;
    }

    async getById(id: number | string): Promise<T> {
        const { data } = await http.get<T>(`${this.endpoint}/${id}`);
        return data;
    }

    async create(payload: C): Promise<T> {
        const { data } = await http.post<T>(this.endpoint, payload);
        return data;
    }

    async update(id: number | string, payload: U): Promise<T> {
        const { data } = await http.patch<T>(`${this.endpoint}/${id}`, payload);
        return data;
    }

    async remove(id: number | string): Promise<void> {
        await http.delete(`${this.endpoint}/${id}`);
    }
}
