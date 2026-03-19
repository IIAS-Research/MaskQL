<script setup lang="ts">
import axios from "axios";
import { computed, onMounted, ref, watch } from "vue";
import { useToast } from "primevue/usetoast";
import type { Catalog, CatalogSchemaEntry } from "../types/catalog";
import { CatalogAPI } from "../types/catalog";
import type { Rule } from "../types/rule";
import { RuleAPI } from "../types/rule";
import RuleScopePanel from "./RuleScopePanel.vue";

const props = defineProps<{ userId: number }>();
const toast = useToast();

const loading = ref(true);
const loadingSchema = ref(false);
const syncingSchema = ref(false);

const catalogs = ref<Catalog[]>([]);
const rules = ref<Rule[]>([]);
const schemaEntriesByCatalog = ref(new Map<number, CatalogSchemaEntry[]>());

const selectedCatalogId = ref<number | null>(null);
const selectedSchema = ref<string | null>(null);
const selectedTable = ref<string | null>(null);

const keyFor = (userId: number, cId: number, schema = "", table = "", column = "") =>
  `${userId}||${cId}||${schema}||${table}||${column}`;

const ruleMap = ref(new Map<string, Rule>());

const schemasByCatalog = ref(new Map<number, Set<string>>());
const tablesByScope = ref(new Map<string, Set<string>>());
const colsByScope = ref(new Map<string, Set<string>>());

function ensureSet<K>(map: Map<K, Set<string>>, key: K) {
  if (!map.has(key)) map.set(key, new Set());
  return map.get(key)!;
}

function getRule(cId: number, schema = "", table = "", column = "") {
  return ruleMap.value.get(keyFor(props.userId, cId, schema, table, column));
}

function statusOf(
  cId: number,
  schema = "",
  table = "",
  column = "",
): "allow" | "deny" | "inherit" {
  const rule = getRule(cId, schema, table, column);
  if (!rule) return "inherit";
  return rule.allow ? "allow" : "deny";
}

function rebuildRuleMap() {
  ruleMap.value.clear();
  for (const rule of rules.value) {
    ruleMap.value.set(
      keyFor(
        props.userId,
        rule.catalog_id,
        rule.schema_name || "",
        rule.table_name || "",
        rule.column_name || "",
      ),
      rule,
    );
  }
}

function rebuildSchemaTree() {
  const nextSchemasByCatalog = new Map<number, Set<string>>();
  const nextTablesByScope = new Map<string, Set<string>>();
  const nextColsByScope = new Map<string, Set<string>>();

  for (const [catalogId, entries] of schemaEntriesByCatalog.value.entries()) {
    for (const entry of entries) {
      ensureSet(nextSchemasByCatalog, catalogId).add(entry.schema_name);
      if (entry.table_name) {
        ensureSet(
          nextTablesByScope,
          `${catalogId}|${entry.schema_name}`,
        ).add(entry.table_name);
      }
      if (entry.table_name && entry.column_name) {
        ensureSet(
          nextColsByScope,
          `${catalogId}|${entry.schema_name}|${entry.table_name}`,
        ).add(entry.column_name);
      }
    }
  }

  schemasByCatalog.value = nextSchemasByCatalog;
  tablesByScope.value = nextTablesByScope;
  colsByScope.value = nextColsByScope;

  if (selectedCatalogId.value == null) return;

  const knownSchemas =
    schemasByCatalog.value.get(selectedCatalogId.value) ?? new Set<string>();
  if (selectedSchema.value && !knownSchemas.has(selectedSchema.value)) {
    selectedSchema.value = null;
  }

  if (!selectedSchema.value) {
    selectedTable.value = null;
    return;
  }

  const knownTables =
    tablesByScope.value.get(
      `${selectedCatalogId.value}|${selectedSchema.value}`,
    ) ?? new Set<string>();
  if (selectedTable.value && !knownTables.has(selectedTable.value)) {
    selectedTable.value = null;
  }
}

async function loadCatalogSchema(catalogId: number, force = false) {
  if (!force && schemaEntriesByCatalog.value.has(catalogId)) return;

  loadingSchema.value = true;
  try {
    const entries = await CatalogAPI.listSchema(catalogId);
    const next = new Map(schemaEntriesByCatalog.value);
    next.set(catalogId, entries);
    schemaEntriesByCatalog.value = next;
    rebuildSchemaTree();
  } catch (e) {
    console.error(e);
    toast.add({
      severity: "error",
      summary: "Error",
      detail: "Unable to load scanned schema",
      life: 3000,
    });
  } finally {
    loadingSchema.value = false;
  }
}

async function upsertRule(
  cId: number,
  schema = "",
  table = "",
  column = "",
  patch: Partial<Pick<Rule, "allow" | "effect">>,
) {
  const key = keyFor(props.userId, cId, schema, table, column);
  const existing = ruleMap.value.get(key);

  const sanitized: Partial<Pick<Rule, "allow" | "effect">> = { ...patch };
  if (!table && !column && "effect" in sanitized) delete sanitized.effect;

  try {
    if (existing) {
      if (Object.keys(sanitized).length === 0) return existing;
      const updated = await RuleAPI.update(existing.id, sanitized);
      ruleMap.value.set(key, updated);
      const idx = rules.value.findIndex((rule) => rule.id === existing.id);
      if (idx !== -1) rules.value[idx] = updated;
      return updated;
    }

    const allow = sanitized.allow ?? (sanitized.effect ? true : undefined);
    if (allow === undefined) return;

    const created = await RuleAPI.create({
      user_id: props.userId,
      catalog_id: cId,
      schema_name: schema || "",
      table_name: table || "",
      column_name: column || "",
      allow,
      effect: sanitized.effect ?? "",
    });
    ruleMap.value.set(key, created);
    rules.value.push(created);
    return created;
  } catch (e) {
    console.error(e);
    toast.add({
      severity: "error",
      summary: "Error",
      detail: "Unable to save rule.",
      life: 3000,
    });
  }
}

async function deleteRule(cId: number, schema = "", table = "", column = "") {
  const key = keyFor(props.userId, cId, schema, table, column);
  const existing = ruleMap.value.get(key);
  if (!existing) return;
  try {
    await RuleAPI.remove(existing.id);
    ruleMap.value.delete(key);
    const idx = rules.value.findIndex((rule) => rule.id === existing.id);
    if (idx !== -1) rules.value.splice(idx, 1);
  } catch (e) {
    console.error(e);
    toast.add({
      severity: "error",
      summary: "Error",
      detail: "Unable to delete",
      life: 3000,
    });
  }
}

const setAllow = (c: number, s = "", t = "", col = "") =>
  upsertRule(c, s, t, col, { allow: true });
const setDeny = (c: number, s = "", t = "", col = "") =>
  upsertRule(c, s, t, col, { allow: false });
const setInherit = (c: number, s = "", t = "", col = "") =>
  deleteRule(c, s, t, col);

const effectOpen = ref(new Set<string>());
const effectDrafts = ref(new Map<string, string>());
const effectTimers = ref(new Map<string, number>());

function openKey(cId: number, s = "", t = "", c = "") {
  return keyFor(props.userId, cId, s, t, c);
}

function toggleEffectScope(cId: number, s = "", t = "", c = "") {
  const key = openKey(cId, s, t, c);
  if (effectOpen.value.has(key)) effectOpen.value.delete(key);
  else effectOpen.value.add(key);
}

function isEffectOpenScope(cId: number, s = "", t = "", c = "") {
  return effectOpen.value.has(openKey(cId, s, t, c));
}

function getEffectScope(cId: number, s = "", t = "", c = "") {
  const key = keyFor(props.userId, cId, s, t, c);
  if (effectDrafts.value.has(key)) return effectDrafts.value.get(key)!;
  return getRule(cId, s, t, c)?.effect ?? "";
}

function setEffectScope(cId: number, s = "", t = "", c = "", value = "") {
  const key = keyFor(props.userId, cId, s, t, c);
  effectDrafts.value.set(key, value);

  if (effectTimers.value.has(key)) {
    window.clearTimeout(effectTimers.value.get(key));
  }

  const timer = window.setTimeout(async () => {
    effectTimers.value.delete(key);
    await upsertRule(cId, s, t, c, { effect: value });
    toast.add({
      severity: "success",
      summary: "Saved",
      detail: "Effect updated",
      life: 1000,
    });
  }, 600);

  effectTimers.value.set(key, timer);
}

function hasScannedPath(catId: number, schema = "", table = "", column = "") {
  const entries = schemaEntriesByCatalog.value.get(catId) ?? [];
  return entries.some(
    (entry) =>
      entry.schema_name === schema &&
      (entry.table_name ?? "") === table &&
      (entry.column_name ?? "") === column,
  );
}

function resetState() {
  catalogs.value = [];
  rules.value = [];
  schemaEntriesByCatalog.value.clear();
  ruleMap.value.clear();
  schemasByCatalog.value.clear();
  tablesByScope.value.clear();
  colsByScope.value.clear();
  selectedCatalogId.value = null;
  selectedSchema.value = null;
  selectedTable.value = null;
  effectDrafts.value.clear();
  effectOpen.value.clear();
  effectTimers.value.forEach((timer) => window.clearTimeout(timer));
  effectTimers.value.clear();
  loadingSchema.value = false;
  syncingSchema.value = false;
}

async function loadAll() {
  loading.value = true;
  try {
    const [nextCatalogs, nextRules] = await Promise.all([
      CatalogAPI.list(),
      RuleAPI.listByUser(props.userId),
    ]);

    catalogs.value = nextCatalogs;
    rules.value = nextRules;
    rebuildRuleMap();

    if (
      selectedCatalogId.value != null &&
      !catalogs.value.some((catalog) => catalog.id === selectedCatalogId.value)
    ) {
      selectedCatalogId.value = null;
    }

    if (catalogs.value.length && selectedCatalogId.value == null) {
      selectedCatalogId.value = catalogs.value[0].id;
    }

    if (selectedCatalogId.value == null) {
      rebuildSchemaTree();
    }
  } catch (e) {
    console.error(e);
    toast.add({
      severity: "error",
      summary: "Error",
      detail: "Unable to load data",
      life: 3000,
    });
  } finally {
    loading.value = false;
  }
}

async function syncSelectedCatalogSchema() {
  if (!selectedCatalogId.value) return;

  syncingSchema.value = true;
  try {
    const summary = await CatalogAPI.syncSchema(selectedCatalogId.value);
    rules.value = await RuleAPI.listByUser(props.userId);
    rebuildRuleMap();
    await loadCatalogSchema(selectedCatalogId.value, true);
    toast.add({
      severity: "success",
      summary: "Schema synchronized",
      detail: `${summary.schemas} schema(s), ${summary.tables} table(s), ${summary.columns} column(s)`,
      life: 3000,
    });
  } catch (e) {
    console.error(e);
    let detail = "Unable to synchronize schema";
    if (axios.isAxiosError(e)) {
      detail = e.response?.data?.detail || detail;
    }
    toast.add({ severity: "error", summary: "Error", detail, life: 4000 });
  } finally {
    syncingSchema.value = false;
  }
}

onMounted(loadAll);

watch(
  () => props.userId,
  async () => {
    resetState();
    await loadAll();
  },
);

watch(selectedCatalogId, async (catalogId) => {
  selectedSchema.value = null;
  selectedTable.value = null;
  if (catalogId != null) {
    await loadCatalogSchema(catalogId);
  }
});

watch(selectedSchema, () => {
  selectedTable.value = null;
});

const catalogItems = computed(() =>
  catalogs.value.map((catalog) => ({ key: `cat:${catalog.id}`, label: catalog.name })),
);

const selectedCatalogKey = computed(() =>
  selectedCatalogId.value != null ? `cat:${selectedCatalogId.value}` : null,
);

function selectCatalog(key: string) {
  if (key === "__add__") return;
  const [, id] = key.split(":");
  selectedCatalogId.value = Number(id);
}

function statusOfCatalogKey(key: string) {
  const [, id] = key.split(":");
  return statusOf(Number(id));
}

const allowCatalogKey = (key: string) =>
  setAllow(Number(key.split(":")[1]));
const denyCatalogKey = (key: string) => setDeny(Number(key.split(":")[1]));
const inheritCatalogKey = (key: string) =>
  setInherit(Number(key.split(":")[1]));

const schemaItems = computed(() => {
  if (!selectedCatalogId.value) return [];
  const schemas = Array.from(
    ensureSet(schemasByCatalog.value, selectedCatalogId.value),
  ).sort((a, b) => a.localeCompare(b));
  return schemas.map((schema) => ({
    key: `sch:${selectedCatalogId.value}:${schema}`,
    label: schema,
  }));
});

const selectedSchemaKey = computed(() =>
  selectedCatalogId.value && selectedSchema.value
    ? `sch:${selectedCatalogId.value}:${selectedSchema.value}`
    : null,
);

function selectSchema(key: string) {
  const [, cId, schema] = key.split(":");
  selectedCatalogId.value = Number(cId);
  selectedSchema.value = schema;
}

function statusOfSchemaKey(key: string) {
  const [, cId, schema] = key.split(":");
  return statusOf(Number(cId), schema);
}

const allowSchemaKey = (key: string) => {
  const [, cId, schema] = key.split(":");
  return setAllow(Number(cId), schema);
};
const denySchemaKey = (key: string) => {
  const [, cId, schema] = key.split(":");
  return setDeny(Number(cId), schema);
};
const inheritSchemaKey = (key: string) => {
  const [, cId, schema] = key.split(":");
  return setInherit(Number(cId), schema);
};

const tableItems = computed(() => {
  if (!selectedCatalogId.value || !selectedSchema.value) return [];
  const tables = Array.from(
    ensureSet(
      tablesByScope.value,
      `${selectedCatalogId.value}|${selectedSchema.value}`,
    ),
  ).sort((a, b) => a.localeCompare(b));
  return tables.map((table) => ({
    key: `tbl:${selectedCatalogId.value}:${selectedSchema.value}:${table}`,
    label: table,
  }));
});

const selectedTableKey = computed(() =>
  selectedCatalogId.value && selectedSchema.value && selectedTable.value
    ? `tbl:${selectedCatalogId.value}:${selectedSchema.value}:${selectedTable.value}`
    : null,
);

function selectTable(key: string) {
  const [, cId, schema, table] = key.split(":");
  selectedCatalogId.value = Number(cId);
  selectedSchema.value = schema;
  selectedTable.value = table;
}

function statusOfTableKey(key: string) {
  const [, cId, schema, table] = key.split(":");
  return statusOf(Number(cId), schema, table);
}

const allowTableKey = (key: string) => {
  const [, cId, schema, table] = key.split(":");
  return setAllow(Number(cId), schema, table);
};
const denyTableKey = (key: string) => {
  const [, cId, schema, table] = key.split(":");
  return setDeny(Number(cId), schema, table);
};
const inheritTableKey = (key: string) => {
  const [, cId, schema, table] = key.split(":");
  return setInherit(Number(cId), schema, table);
};

const isEffectOpenTableKey = (key: string) => {
  const [, cId, schema, table] = key.split(":");
  return isEffectOpenScope(Number(cId), schema, table);
};
const toggleEffectTableKey = (key: string) => {
  const [, cId, schema, table] = key.split(":");
  return toggleEffectScope(Number(cId), schema, table);
};
const getEffectTableKey = (key: string) => {
  const [, cId, schema, table] = key.split(":");
  return getEffectScope(Number(cId), schema, table);
};
const setEffectTableKey = (key: string, value: string) => {
  const [, cId, schema, table] = key.split(":");
  return setEffectScope(Number(cId), schema, table, "", value);
};

const columnItems = computed(() => {
  if (!selectedCatalogId.value || !selectedSchema.value || !selectedTable.value) {
    return [];
  }
  const columns = Array.from(
    ensureSet(
      colsByScope.value,
      `${selectedCatalogId.value}|${selectedSchema.value}|${selectedTable.value}`,
    ),
  ).sort((a, b) => a.localeCompare(b));
  return columns.map((column) => ({
    key: `col:${selectedCatalogId.value}:${selectedSchema.value}:${selectedTable.value}:${column}`,
    label: column,
  }));
});

const selectedColumnKey = computed(() => null);

function selectColumn(_key: string) {
  return;
}

function statusOfColumnKey(key: string) {
  const [, cId, schema, table, column] = key.split(":");
  return statusOf(Number(cId), schema, table, column);
}

const allowColumnKey = (key: string) => {
  const [, cId, schema, table, column] = key.split(":");
  return setAllow(Number(cId), schema, table, column);
};
const denyColumnKey = (key: string) => {
  const [, cId, schema, table, column] = key.split(":");
  return setDeny(Number(cId), schema, table, column);
};
const inheritColumnKey = (key: string) => {
  const [, cId, schema, table, column] = key.split(":");
  return setInherit(Number(cId), schema, table, column);
};

const isEffectOpenColumnKey = (key: string) => {
  const [, cId, schema, table, column] = key.split(":");
  return isEffectOpenScope(Number(cId), schema, table, column);
};
const toggleEffectColumnKey = (key: string) => {
  const [, cId, schema, table, column] = key.split(":");
  return toggleEffectScope(Number(cId), schema, table, column);
};
const getEffectColumnKey = (key: string) => {
  const [, cId, schema, table, column] = key.split(":");
  return getEffectScope(Number(cId), schema, table, column);
};
const setEffectColumnKey = (key: string, value: string) => {
  const [, cId, schema, table, column] = key.split(":");
  return setEffectScope(Number(cId), schema, table, column, value);
};

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
  const catalogId = selectedCatalogId.value;

  const toExport: ExportRule[] = rules.value
    .filter((rule) => rule.catalog_id === catalogId)
    .map((rule) => ({
      schema_name: rule.schema_name || "",
      table_name: rule.table_name || "",
      column_name: rule.column_name || "",
      allow: !!rule.allow,
      effect: rule.effect || "",
    }));

  const bundle: ExportBundle = {
    version: 1,
    user_id: props.userId,
    catalog_id: catalogId,
    exported_at: new Date().toISOString(),
    rules: toExport,
  };

  const blob = new Blob([JSON.stringify(bundle, null, 2)], {
    type: "application/json",
  });
  const filename = `rules_user_${props.userId}_catalog_${catalogId}.json`;

  const anchor = document.createElement("a");
  anchor.href = URL.createObjectURL(blob);
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(anchor.href);
  toast.add({
    severity: "success",
    summary: "Exporté",
    detail: `${toExport.length} règle(s)`,
    life: 1800,
  });
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

    if (!selectedCatalogId.value) {
      throw new Error("Sélectionne d'abord un catalog.");
    }
    if (!json || typeof json !== "object" || !Array.isArray(json.rules)) {
      throw new Error(
        "Fichier invalide : format attendu { version, user_id, catalog_id, rules: [] }",
      );
    }

    const catalogId = selectedCatalogId.value;
    let created = 0;
    let updated = 0;
    let skipped = 0;

    for (const raw of json.rules as ExportRule[]) {
      const schema = (raw.schema_name ?? "").trim();
      const table = (raw.table_name ?? "").trim();
      const column = (raw.column_name ?? "").trim();
      const allow = !!raw.allow;
      const effect = table || column ? (raw.effect ?? "") : "";

      if (schema && !hasScannedPath(catalogId, schema, table, column)) {
        skipped++;
        continue;
      }

      const existed = !!getRule(catalogId, schema, table, column);
      await upsertRule(catalogId, schema, table, column, { allow, effect });
      if (existed) updated++;
      else created++;
    }

    await loadAll();

    toast.add({
      severity: "success",
      summary: "Import terminé",
      detail: `${created} créé(e)s, ${updated} mis(e)s à jour, ${skipped} ignoré(e)s`,
      life: 3000,
    });
  } catch (e: any) {
    console.error(e);
    toast.add({
      severity: "error",
      summary: "Import échoué",
      detail: e?.message ?? "Erreur inconnue",
      life: 3000,
    });
  } finally {
    busyImport.value = false;
  }
}
</script>

<template>
  <div class="space-y-3">
    <div class="flex items-center justify-end gap-2">
      <button
        class="px-3 py-2 text-sm border rounded-lg hover:bg-gray-50 disabled:opacity-50"
        :disabled="!selectedCatalogId || loading || loadingSchema || syncingSchema"
        @click="syncSelectedCatalogSchema"
        title="Synchronize scanned schema of selected database"
      >
        <i class="pi pi-refresh mr-2 text-xs"></i>
        <span v-if="syncingSchema">Syncing...</span>
        <span v-else>Sync schema</span>
      </button>

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
    <div v-else-if="loadingSchema" class="text-gray-500 text-sm">
      Loading scanned schema...
    </div>

    <div v-else class="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
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

      <RuleScopePanel
        title="Schemas"
        :items="schemaItems"
        :selected-key="selectedSchemaKey"
        :status-of="statusOfSchemaKey"
        :on-allow="allowSchemaKey"
        :on-deny="denySchemaKey"
        :on-inherit="inheritSchemaKey"
        @select="selectSchema"
      />

      <RuleScopePanel
        title="Tables"
        :items="tableItems"
        :selected-key="selectedTableKey"
        :status-of="statusOfTableKey"
        :on-allow="allowTableKey"
        :on-deny="denyTableKey"
        :on-inherit="inheritTableKey"
        :show-effect="true"
        :get-effect="getEffectTableKey"
        :set-effect="setEffectTableKey"
        @select="selectTable"
      />

      <RuleScopePanel
        title="Columns"
        :items="columnItems"
        :selected-key="selectedColumnKey"
        :status-of="statusOfColumnKey"
        :on-allow="allowColumnKey"
        :on-deny="denyColumnKey"
        :on-inherit="inheritColumnKey"
        :show-effect="true"
        :get-effect="getEffectColumnKey"
        :set-effect="setEffectColumnKey"
        :is-column="true"
        @select="selectColumn"
      />
    </div>
  </div>
</template>
