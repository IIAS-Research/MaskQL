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

export interface CatalogSchemaEntry {
  id: number;
  catalog_id: number;
  schema_name: string;
  table_name: string | null;
  column_name: string | null;
  manually_added: boolean;
  present_in_database: boolean;
}

export interface CatalogSchemaEntryCreate {
  schema_name: string;
  table_name?: string | null;
  column_name?: string | null;
}

export interface CatalogSchemaSyncResult {
  catalog_id: number;
  schemas: number;
  tables: number;
  columns: number;
  created_entries: number;
  deleted_entries: number;
  deleted_rules: number;
}

export interface CatalogTablePreviewRequest {
  user_id: number;
  schema_name: string;
  table_name: string;
  limit?: number;
}

export interface CatalogPreviewDataset {
  columns: string[];
  rows: Record<string, unknown>[];
  error?: string | null;
}

export interface CatalogTablePreview {
  catalog_id: number;
  schema_name: string;
  table_name: string;
  limit: number;
  before_maskql: CatalogPreviewDataset;
  after_maskql: CatalogPreviewDataset;
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

  async listSchema(catalogId: number): Promise<CatalogSchemaEntry[]> {
    const { data } = await http.get<CatalogSchemaEntry[]>(
      `${this.endpoint}/${catalogId}/schema`,
    );
    return data;
  }

  async createSchemaEntry(
    catalogId: number,
    payload: CatalogSchemaEntryCreate,
  ): Promise<CatalogSchemaEntry> {
    const { data } = await http.post<CatalogSchemaEntry>(
      `${this.endpoint}/${catalogId}/schema`,
      payload,
    );
    return data;
  }

  async deleteSchemaEntry(catalogId: number, entryId: number): Promise<void> {
    await http.delete(`${this.endpoint}/${catalogId}/schema/${entryId}`);
  }

  async syncSchema(catalogId: number): Promise<CatalogSchemaSyncResult> {
    const { data } = await http.post<CatalogSchemaSyncResult>(
      `${this.endpoint}/${catalogId}/schema/sync`,
    );
    return data;
  }

  async previewTable(
    catalogId: number,
    payload: CatalogTablePreviewRequest,
  ): Promise<CatalogTablePreview> {
    const { data } = await http.post<CatalogTablePreview>(
      `${this.endpoint}/${catalogId}/schema/preview`,
      payload,
    );
    return data;
  }
}

export const CatalogAPI = new Catalogs();
