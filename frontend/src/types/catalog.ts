import http from "../http";
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

export interface CatalogConnectionStatus {
  catalog_id: number;
  state: "ok" | "error";
  message: string;
}

export class Catalogs extends BaseResource<
  Catalog,
  CatalogCreate,
  CatalogUpdate
> {
  constructor() {
    super("/catalogs");
  }

  async listStatuses(): Promise<CatalogConnectionStatus[]> {
    const { data } = await http.get<CatalogConnectionStatus[]>(
      `${this.endpoint}/status`,
    );
    return data;
  }
}

export const CatalogAPI = new Catalogs();
