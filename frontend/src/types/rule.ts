import { BaseResource } from "./base";

export interface Rule {
    id: number;
    schema_name: string;
    table_name: string;
    column_name: string;
    allow: boolean;
    effect: string; 
    catalog_id: number;
    user_id: number;
}

export type RuleCreate = Omit<Rule, "id">;
export type RuleUpdate = Partial<Omit<Rule, "id">>;

export class Rules extends BaseResource<Rule, RuleCreate, RuleUpdate> {
    constructor() {
        super("/rules");
    }

    async listByCatalog(catalogId: number): Promise<Rule[]> {
        return this.list({ catalog_id: catalogId });
    }
    async listByUser(userId: number): Promise<Rule[]> {
        return this.list({ user_id: userId });
    }
}

export const RuleAPI = new Rules();
