<script setup lang="ts">
import { ref, computed, onMounted, watch } from "vue";
import { useToast } from "primevue/usetoast";
import type { Catalog } from "../types/catalog";
import { CatalogAPI } from "../types/catalog";
import type { Rule } from "../types/rule";
import { RuleAPI } from "../types/rule";
import RuleScopePanel from "./RuleScopePanel.vue";

const props = defineProps<{ userId: number }>();
const toast = useToast();

// States
const loading = ref(true);
const catalogs = ref<Catalog[]>([]);
const rules = ref<Rule[]>([]);

const selectedCatalogId = ref<number | null>(null);
const selectedSchema = ref<string | null>(null);
const selectedTable = ref<string | null>(null);

// Unique key
const keyFor = (userId: number, cId: number, schema = "", table = "", column = "") =>
    `${userId}||${cId}||${schema}||${table}||${column}`;

const ruleMap = ref(new Map<string, Rule>());

// Tree
const schemasByCatalog = ref(new Map<number, Set<string>>());
const tablesByScope = ref(new Map<string, Set<string>>());   // key: cId|schema
const colsByScope   = ref(new Map<string, Set<string>>());   // key: cId|schema|table

function ensureSet<K>(map: Map<K, Set<string>>, key: K) {
    if (!map.has(key)) map.set(key, new Set());
    return map.get(key)!;
}

// Inputs "Add"
const newSchema = ref("");
const newTable = ref("");
const newColumn = ref("");

// Helpers Rules (avoid duplicates)
function getRule(cId: number, schema = "", table = "", column = "") {
    return ruleMap.value.get(keyFor(props.userId, cId, schema, table, column));
}
function statusOf(cId: number, schema = "", table = "", column = ""): "allow"|"deny"|"inherit" {
    const r = getRule(cId, schema, table, column);
    if (!r) return "inherit";
    return r.allow ? "allow" : "deny";
}

async function upsertRule(
    cId: number,
    schema = "",
    table = "",
    column = "",
    patch: Partial<Pick<Rule, "allow" | "effect">>
) {
    const k = keyFor(props.userId, cId, schema, table, column);
    const existing = ruleMap.value.get(k);

    // No effect for DB and schema
    const sanitized: Partial<Pick<Rule, "allow" | "effect">> = { ...patch };
    if (!table && !column && "effect" in sanitized) delete sanitized.effect;

    try {
        if (existing) {
        if (Object.keys(sanitized).length === 0) return existing;
        const updated = await RuleAPI.update(existing.id, sanitized);
        ruleMap.value.set(k, updated);
        const idx = rules.value.findIndex(r => r.id === existing.id);
        if (idx !== -1) rules.value[idx] = updated;
        return updated;
        } else {
        const allow = sanitized.allow ?? (sanitized.effect ? true : undefined);
        if (allow === undefined) return;
        const created = await RuleAPI.create({
            user_id: props.userId,
            catalog_id: cId,
            schema_name: schema || "",
            table_name: table || "",
            column_name: column || "",
            allow,
            effect: sanitized.effect ?? ""
        });
        ruleMap.value.set(k, created);
        rules.value.push(created);
        return created;
        }
    } catch (e) {
        console.error(e);
        toast.add({ severity: "error", summary: "Error", detail: "Unable to save rule.", life: 3000 });
    }
}

async function deleteRule(cId: number, schema = "", table = "", column = "") {
    const k = keyFor(props.userId, cId, schema, table, column);
    const existing = ruleMap.value.get(k);
    if (!existing) return;
    try {
        await RuleAPI.remove(existing.id);
        ruleMap.value.delete(k);
        const i = rules.value.findIndex(r => r.id === existing.id);
        if (i !== -1) rules.value.splice(i, 1);
    } catch (e) {
        console.error(e);
        toast.add({ severity: "error", summary: "Error", detail: "Unable to delete", life: 3000 });
    }
}

// Status actions
const setAllow = (c: number, s = "", t = "", col = "") => upsertRule(c, s, t, col, { allow: true });
const setDeny  = (c: number, s = "", t = "", col = "") => upsertRule(c, s, t, col, { allow: false });
const setInherit = (c: number, s = "", t = "", col = "") => deleteRule(c, s, t, col);

// Effect
const effectOpen = ref(new Set<string>());
const effectDrafts = ref(new Map<string, string>());
const effectTimers = ref(new Map<string, number>());

function openKey(cId: number, s = "", t = "", c = "") { return keyFor(props.userId, cId, s, t, c); }
function toggleEffectScope(cId: number, s = "", t = "", c = "") {
    const k = openKey(cId, s, t, c);
    if (effectOpen.value.has(k)) effectOpen.value.delete(k);
    else effectOpen.value.add(k);
}
function isEffectOpenScope(cId: number, s = "", t = "", c = "") {
    return effectOpen.value.has(openKey(cId, s, t, c));
}
function getEffectScope(cId: number, s = "", t = "", c = "") {
    const k = keyFor(props.userId, cId, s, t, c);
    if (effectDrafts.value.has(k)) return effectDrafts.value.get(k)!;
    return getRule(cId, s, t, c)?.effect ?? "";
}
function setEffectScope(cId: number, s = "", t = "", c = "", val = "") {
    const k = keyFor(props.userId, cId, s, t, c);
    effectDrafts.value.set(k, val);
    if (effectTimers.value.has(k)) window.clearTimeout(effectTimers.value.get(k));
    const tmr: number = window.setTimeout(async () => {
        effectTimers.value.delete(k);
        await upsertRule(cId, s, t, c, { effect: val });
        toast.add({ severity: "success", summary: "Saved", detail: "Effect updated", life: 1000 });
    }, 600);
    effectTimers.value.set(k, tmr);
}

// Reset if userId change
function resetState() {
    catalogs.value = [];
    rules.value = [];
    ruleMap.value.clear();
    schemasByCatalog.value.clear();
    tablesByScope.value.clear();
    colsByScope.value.clear();
    selectedCatalogId.value = null;
    selectedSchema.value = null;
    selectedTable.value = null;
    newSchema.value = "";
    newTable.value = "";
    newColumn.value = "";
    effectDrafts.value.clear();
    effectOpen.value.clear();
    effectTimers.value.forEach(t => window.clearTimeout(t));
    effectTimers.value.clear();
}

// Loading
async function loadAll() {
    loading.value = true;
    try {
        const [cats, userRules] = await Promise.all([
        CatalogAPI.list(),
        RuleAPI.listByUser(props.userId),
        ]);
        catalogs.value = cats;
        rules.value = userRules;

        ruleMap.value.clear();
        schemasByCatalog.value.clear();
        tablesByScope.value.clear();
        colsByScope.value.clear();

        for (const r of userRules) {
        const k = keyFor(props.userId, r.catalog_id, r.schema_name || "", r.table_name || "", r.column_name || "");
        ruleMap.value.set(k, r);

        if (r.schema_name) ensureSet(schemasByCatalog.value, r.catalog_id).add(r.schema_name);
        if (r.table_name && r.schema_name) ensureSet(tablesByScope.value, `${r.catalog_id}|${r.schema_name}`).add(r.table_name);
        if (r.column_name && r.table_name && r.schema_name) ensureSet(colsByScope.value, `${r.catalog_id}|${r.schema_name}|${r.table_name}`).add(r.column_name);
        }

        if (catalogs.value.length && selectedCatalogId.value == null) {
        selectedCatalogId.value = catalogs.value[0].id;
        }
    } catch (e) {
        console.error(e);
        toast.add({ severity: "error", summary: "Error", detail: "Unable to load data", life: 3000 });
    } finally {
        loading.value = false;
    }
}

// Mount
onMounted(loadAll);
watch(() => props.userId, async () => { resetState(); await loadAll(); });
watch(selectedCatalogId, () => { selectedSchema.value = null; selectedTable.value = null; });
watch(selectedSchema, () => { selectedTable.value = null; });

// Mapping items & handlers
// -> Catalog
const catalogItems = computed(() =>
    catalogs.value.map(c => ({ key: `cat:${c.id}`, label: c.name }))
);
const selectedCatalogKey = computed(() =>
    selectedCatalogId.value != null ? `cat:${selectedCatalogId.value}` : null
);
function selectCatalog(key: string) {
    if (key === "__add__") return; // No DB add here
    const [, id] = key.split(":");
    selectedCatalogId.value = Number(id);
}
function statusOfCatalogKey(key: string) {
    const [, id] = key.split(":");
    return statusOf(Number(id));
}
const allowCatalogKey = (key: string) => setAllow(Number(key.split(":")[1]));
const denyCatalogKey =  (key: string) => setDeny(Number(key.split(":")[1]));
const inheritCatalogKey = (key: string) => setInherit(Number(key.split(":")[1]));

// -> Schema
const schemaItems = computed(() => {
    if (!selectedCatalogId.value) return [];
    const arr = Array.from(ensureSet(schemasByCatalog.value, selectedCatalogId.value));
    return arr.map(s => ({ key: `sch:${selectedCatalogId.value}:${s}`, label: s }));
});
const selectedSchemaKey = computed(() =>
    selectedCatalogId.value && selectedSchema.value
        ? `sch:${selectedCatalogId.value}:${selectedSchema.value}` : null
);
function selectSchema(key: string) {
    if (key === "__add__") {
        if (!selectedCatalogId.value || !newSchema.value.trim()) return;
        ensureSet(schemasByCatalog.value, selectedCatalogId.value).add(newSchema.value.trim());
        newSchema.value = "";
        return;
    }
    const [, cId, s] = key.split(":");
    selectedCatalogId.value = Number(cId);
    selectedSchema.value = s;
}
function statusOfSchemaKey(key: string) {
    const [, cId, s] = key.split(":");
    return statusOf(Number(cId), s);
}
const allowSchemaKey   = (key: string) => { const [, cId, s] = key.split(":"); return setAllow(Number(cId), s); };
const denySchemaKey    = (key: string) => { const [, cId, s] = key.split(":"); return setDeny(Number(cId), s); };
const inheritSchemaKey = (key: string) => { const [, cId, s] = key.split(":"); return setInherit(Number(cId), s); };

// -> Tables
const tableItems = computed(() => {
    if (!selectedCatalogId.value || !selectedSchema.value) return [];
    const arr = Array.from(ensureSet(tablesByScope.value, `${selectedCatalogId.value}|${selectedSchema.value}`));
    return arr.map(t => ({ key: `tbl:${selectedCatalogId.value}:${selectedSchema.value}:${t}`, label: t }));
});
const selectedTableKey = computed(() =>
    selectedCatalogId.value && selectedSchema.value && selectedTable.value
        ? `tbl:${selectedCatalogId.value}:${selectedSchema.value}:${selectedTable.value}` : null
);
function selectTable(key: string) {
    if (key === "__add__") {
        if (!selectedCatalogId.value || !selectedSchema.value || !newTable.value.trim()) return;
        ensureSet(tablesByScope.value, `${selectedCatalogId.value}|${selectedSchema.value}`).add(newTable.value.trim());
        newTable.value = "";
        return;
    }
    const [, cId, s, t] = key.split(":");
    selectedCatalogId.value = Number(cId);
    selectedSchema.value = s;
    selectedTable.value = t;
}
function statusOfTableKey(key: string) {
    const [, cId, s, t] = key.split(":");
    return statusOf(Number(cId), s, t);
}
const allowTableKey   = (key: string) => { const [, cId, s, t] = key.split(":"); return setAllow(Number(cId), s, t); };
const denyTableKey    = (key: string) => { const [, cId, s, t] = key.split(":"); return setDeny(Number(cId), s, t); };
const inheritTableKey = (key: string) => { const [, cId, s, t] = key.split(":"); return setInherit(Number(cId), s, t); };

const isEffectOpenTableKey = (key: string) => { const [, cId, s, t] = key.split(":"); return isEffectOpenScope(Number(cId), s, t); };
const toggleEffectTableKey = (key: string) => { const [, cId, s, t] = key.split(":"); return toggleEffectScope(Number(cId), s, t); };
const getEffectTableKey    = (key: string) => { const [, cId, s, t] = key.split(":"); return getEffectScope(Number(cId), s, t); };
const setEffectTableKey    = (key: string, v: string) => { const [, cId, s, t] = key.split(":"); return setEffectScope(Number(cId), s, t, "", v); };

// -> Column
const columnItems = computed(() => {
    if (!selectedCatalogId.value || !selectedSchema.value || !selectedTable.value) return [];
    const arr = Array.from(ensureSet(colsByScope.value, `${selectedCatalogId.value}|${selectedSchema.value}|${selectedTable.value}`));
    return arr.map(c => ({ key: `col:${selectedCatalogId.value}:${selectedSchema.value}:${selectedTable.value}:${c}`, label: c }));
});
const selectedColumnKey = computed(() =>
    selectedCatalogId.value && selectedSchema.value && selectedTable.value
        ? null : null
);
function selectColumn(key: string) {
    if (key === "__add__") {
        if (!selectedCatalogId.value || !selectedSchema.value || !selectedTable.value || !newColumn.value.trim()) return;
        ensureSet(colsByScope.value, `${selectedCatalogId.value}|${selectedSchema.value}|${selectedTable.value}`).add(newColumn.value.trim());
        newColumn.value = "";
        return;
    }
}
function statusOfColumnKey(key: string) {
    const [, cId, s, t, c] = key.split(":");
    return statusOf(Number(cId), s, t, c);
}
const allowColumnKey   = (key: string) => { const [, cId, s, t, c] = key.split(":"); return setAllow(Number(cId), s, t, c); };
const denyColumnKey    = (key: string) => { const [, cId, s, t, c] = key.split(":"); return setDeny(Number(cId), s, t, c); };
const inheritColumnKey = (key: string) => { const [, cId, s, t, c] = key.split(":"); return setInherit(Number(cId), s, t, c); };

const isEffectOpenColumnKey = (key: string) => { const [, cId, s, t, c] = key.split(":"); return isEffectOpenScope(Number(cId), s, t, c); };
const toggleEffectColumnKey = (key: string) => { const [, cId, s, t, c] = key.split(":"); return toggleEffectScope(Number(cId), s, t, c); };
const getEffectColumnKey    = (key: string) => { const [, cId, s, t, c] = key.split(":"); return getEffectScope(Number(cId), s, t, c); };
const setEffectColumnKey    = (key: string, v: string) => { const [, cId, s, t, c] = key.split(":"); return setEffectScope(Number(cId), s, t, c, v); };

// EXPORT / IMPORT (JSON
type ExportRule = {
    schema_name?: string;
    table_name?: string;
    column_name?: string;
    allow: boolean;
    effect?: string;
};
type ExportBundle = {
    version: 1;
    user_id: number;
    catalog_id: number;
    exported_at: string;
    rules: ExportRule[];
};

const fileInputRef = ref<HTMLInputElement | null>(null);
const busyImport = ref(false);

function exportSelectedCatalog() {
    if (!selectedCatalogId.value) return;
    const catId = selectedCatalogId.value;
    
    const toExport: ExportRule[] = rules.value
        .filter(r => r.catalog_id === catId)
        .map(r => ({
        schema_name: r.schema_name || "",
        table_name: r.table_name || "",
        column_name: r.column_name || "",
        allow: !!r.allow,
        effect: r.effect || ""
        }));

    const bundle: ExportBundle = {
        version: 1,
        user_id: props.userId,
        catalog_id: catId,
        exported_at: new Date().toISOString(),
        rules: toExport,
    };

    const blob = new Blob([JSON.stringify(bundle, null, 2)], { type: "application/json" });
    const filename = `rules_user_${props.userId}_catalog_${catId}.json`;

    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(a.href);
    toast.add({ severity: "success", summary: "Exporté", detail: `${toExport.length} règle(s)`, life: 1800 });
    }

function openImportDialog() {
    fileInputRef.value?.click();
}

async function handleImportFile(evt: Event) {
    const input = evt.target as HTMLInputElement;
    const file = input.files?.[0];
    input.value = "";
    if (!file) return;

    busyImport.value = true;
    try {
        const text = await file.text();
        const json = JSON.parse(text);

        if (!selectedCatalogId.value) throw new Error("Sélectionne d'abord un catalog.");
        if (!json || typeof json !== "object" || !Array.isArray(json.rules)) {
        throw new Error("Fichier invalide : format attendu { version, user_id, catalog_id, rules: [] }");
        }

        const catId = selectedCatalogId.value;
        let created = 0, updated = 0;

        for (const raw of json.rules as ExportRule[]) {
        const schema = (raw.schema_name ?? "").trim();
        const table  = (raw.table_name  ?? "").trim();
        const col    = (raw.column_name ?? "").trim();
        const allow  = !!raw.allow;
        const effect = (table || col) ? (raw.effect ?? "") : "";

        const existed = !!getRule(catId, schema, table, col);

        await upsertRule(catId, schema, table, col, { allow, effect });

        if (schema) ensureSet(schemasByCatalog.value, catId).add(schema);
        if (table && schema) ensureSet(tablesByScope.value, `${catId}|${schema}`).add(table);
        if (col && table && schema) ensureSet(colsByScope.value, `${catId}|${schema}|${table}`).add(col);

        if (existed) updated++; else created++;
        }

        await loadAll();

        toast.add({
        severity: "success",
        summary: "Import terminé",
        detail: `${created} créé(e)s, ${updated} mis(e)s à jour`,
        life: 3000
        });
    } catch (e: any) {
        console.error(e);
        toast.add({ severity: "error", summary: "Import échoué", detail: e?.message ?? "Erreur inconnue", life: 3000 });
    } finally {
        busyImport.value = false;
    }
}
</script>

<template>
    <div class="space-y-3">
        <!-- Toolbar Export / Import -->
        <div class="flex items-center justify-end gap-2">
        <button
            class="px-3 py-2 text-sm border rounded-lg hover:bg-gray-50 disabled:opacity-50"
            :disabled="!selectedCatalogId || loading"
            @click="exportSelectedCatalog"
            title="Export rules of selected database"
        >
            <i class="pi pi-download mr-2 text-xs"></i> Export
        </button>

        <button
            class="px-3 py-2 text-sm border rounded-lg hover:bg-gray-50 disabled:opacity-50"
            :disabled="!selectedCatalogId || loading || busyImport"
            @click="openImportDialog"
            title="Import rules from file (JSON) into selected database"
        >
            <i class="pi pi-upload mr-2 text-xs"></i> Import
        </button>

        <input
            ref="fileInputRef"
            type="file"
            accept="application/json"
            class="hidden"
            @change="handleImportFile"
        />
        </div>
        <div v-if="loading" class="text-gray-500 text-sm">Loading...</div>

        <div v-else class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3">
        <!-- Panel DB -->
        <RuleScopePanel
            title="Databases"
            :items="catalogItems"
            :selected-key="selectedCatalogKey"
            :status-of="statusOfCatalogKey"
            :on-allow="allowCatalogKey"
            :on-deny="denyCatalogKey"
            :on-inherit="inheritCatalogKey"
            @select="selectCatalog"
        />

        <!-- Panel Schemas -->
        <RuleScopePanel
            title="Schemas"
            :items="schemaItems"
            :selected-key="selectedSchemaKey"
            :status-of="statusOfSchemaKey"
            :on-allow="allowSchemaKey"
            :on-deny="denySchemaKey"
            :on-inherit="inheritSchemaKey"
            :show-add="true"
            v-model:addModel="newSchema"
            add-placeholder="Schema's name"
            :add-disabled="!selectedCatalogId"
            @select="selectSchema"
        />

        <!-- Panel Tables -->
        <RuleScopePanel
            title="Tables"
            :items="tableItems"
            :selected-key="selectedTableKey"
            :status-of="statusOfTableKey"
            :on-allow="allowTableKey"
            :on-deny="denyTableKey"
            :on-inherit="inheritTableKey"
            :show-effect="true"
            :is-effect-open="isEffectOpenTableKey"
            :toggle-effect="toggleEffectTableKey"
            :get-effect="getEffectTableKey"
            :set-effect="setEffectTableKey"
            :show-add="true"
            v-model:addModel="newTable"
            add-placeholder="Table's name"
            :add-disabled="!selectedCatalogId || !selectedSchema"
            @select="selectTable"
        />

        <!-- Panel Columns -->
        <RuleScopePanel
            title="Columns"
            :items="columnItems"
            :selected-key="selectedColumnKey"
            :status-of="statusOfColumnKey"
            :on-allow="allowColumnKey"
            :on-deny="denyColumnKey"
            :on-inherit="inheritColumnKey"
            :show-effect="true"
            :is-effect-open="isEffectOpenColumnKey"
            :toggle-effect="toggleEffectColumnKey"
            :get-effect="getEffectColumnKey"
            :set-effect="setEffectColumnKey"
            :show-add="true"
            :is-column="true"
            v-model:addModel="newColumn"
            add-placeholder="Column's name"
            :add-disabled="!selectedCatalogId || !selectedSchema || !selectedTable"
            @select="selectColumn"
        />
        </div>
    </div>
</template>
