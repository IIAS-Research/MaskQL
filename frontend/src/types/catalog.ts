import { BaseResource } from "./base";

export interface Catalog {
    id: number;
    name: string;
    url: string;
    sgbd: string;
    username: string;
    password: string;
}

export type CatalogCreate = Omit<Catalog, "id">;
export type CatalogUpdate = Partial<Omit<Catalog, "id">>;


export class Catalogs extends BaseResource<Catalog, CatalogCreate, CatalogUpdate> {
    constructor() {
        super("/catalogs");
    }
}

export const CatalogAPI = new Catalogs();
