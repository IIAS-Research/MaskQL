<script setup lang="ts">
import axios from "axios";
import Dialog from "primevue/dialog";
import { computed, onMounted, ref, watch } from "vue";
import { useToast } from "primevue/usetoast";
import type {
  Catalog,
  CatalogPreviewDataset,
  CatalogSchemaEntry,
  CatalogTablePreview,
} from "../types/catalog";
import { CatalogAPI } from "../types/catalog";
import type { Rule } from "../types/rule";
import { RuleAPI } from "../types/rule";
import RuleScopePanel from "./RuleScopePanel.vue";

const props = defineProps<{ userId: number }>();
const toast = useToast();

type Status = "allow" | "deny" | "inherit";

type ScopeItem = {
  key: string;
  label: string;
  hint?: string;
  removable?: boolean;
};

type TableConfigScope = {
  catalogId: number;
  schema: string;
  table: string;
};

type TableColumnIndicator = {
  label: string;
  status: "allow" | "deny";
  hint?: string;
  masked: boolean;
};

type TableCardColumnDisplay = {
  allow: TableColumnIndicator[];
  deny: TableColumnIndicator[];
  extraAllow: number;
  extraDeny: number;
};

type EffectiveAccess = {
  status: "allow" | "deny";
  inherited: boolean;
  sourceLabel: string;
};

const loading = ref(true);
const loadingSchema = ref(false);
const syncingSchema = ref(false);
const mutatingSchemaEntry = ref(false);

const catalogs = ref<Catalog[]>([]);
const rules = ref<Rule[]>([]);
const schemaEntriesByCatalog = ref(new Map<number, CatalogSchemaEntry[]>());

const selectedCatalogId = ref<number | null>(null);
const selectedSchema = ref<string | null>(null);
const selectedTable = ref<string | null>(null);
const draftSchemaName = ref("");
const draftTableName = ref("");
const draftColumnName = ref("");

const tableConfigVisible = ref(false);
const tableConfig = ref<TableConfigScope | null>(null);
const preview = ref<CatalogTablePreview | null>(null);
const previewLoading = ref(false);
const previewRequestError = ref("");

const missingPathHint = "Possibly not present in the database";

const keyFor = (
  userId: number,
  cId: number,
  schema = "",
  table = "",
  column = "",
) => `${userId}||${cId}||${schema}||${table}||${column}`;

const ruleMap = ref(new Map<string, Rule>());

const schemasByCatalog = ref(new Map<number, Set<string>>());
const tablesByScope = ref(new Map<string, Set<string>>());
const colsByScope = ref(new Map<string, Set<string>>());

const effectDrafts = ref(new Map<string, string>());
const effectTimers = ref(new Map<string, number>());

const fileInputRef = ref<HTMLInputElement | null>(null);
const busyImport = ref(false);

let previewTimer: number | null = null;
let previewRequestSequence = 0;

const TABLE_CARD_COLUMN_LIMIT_PER_STATUS = 6;

function ensureSet<K>(map: Map<K, Set<string>>, key: K) {
  if (!map.has(key)) map.set(key, new Set());
  return map.get(key)!;
}

function badgeClass(status: Status) {
  if (status === "allow") return "text-green-700 bg-green-50 border-green-200";
  if (status === "deny") return "text-red-700 bg-red-50 border-red-200";
  return "text-gray-600 bg-gray-50 border-gray-200";
}

function subtleCardClass(status: "allow" | "deny") {
  return status === "allow"
    ? "border border-green-100 border-l-4 border-l-green-400 bg-green-50/10 hover:bg-green-50/25"
    : "border border-red-100 border-l-4 border-l-red-400 bg-red-50/10 hover:bg-red-50/25";
}

function columnPillClass(status: "allow" | "deny") {
  return status === "allow"
    ? "border border-green-200 bg-green-100 text-green-800"
    : "border border-red-200 bg-red-100 text-red-800";
}

function segBtn(active: boolean) {
  return `px-2 py-1 text-xs leading-none ${
    active
      ? "bg-gray-800 text-white"
      : "bg-white text-gray-700 hover:bg-gray-50"
  }`;
}

function getRule(cId: number, schema = "", table = "", column = "") {
  return ruleMap.value.get(keyFor(props.userId, cId, schema, table, column));
}

function getSchemaEntry(cId: number, schema = "", table = "", column = "") {
  const entries = schemaEntriesByCatalog.value.get(cId) ?? [];
  return entries.find(
    (entry) =>
      entry.schema_name === schema &&
      (entry.table_name ?? "") === table &&
      (entry.column_name ?? "") === column,
  );
}

function statusOf(cId: number, schema = "", table = "", column = ""): Status {
  const rule = getRule(cId, schema, table, column);
  if (!rule) return "inherit";
  return rule.allow ? "allow" : "deny";
}

function catalogLabel(cId: number) {
  const catalog = catalogs.value.find((item) => item.id === cId);
  return catalog ? `database ${catalog.name}` : `database ${cId}`;
}

function sourceLabelForScope(cId: number, schema = "", table = "") {
  if (table) return `table ${schema}.${table}`;
  if (schema) return `schema ${schema}`;
  return catalogLabel(cId);
}

function resolveEffectiveAccess(
  cId: number,
  schema = "",
  table = "",
  column = "",
): EffectiveAccess {
  const directRule = getRule(cId, schema, table, column);
  if (directRule) {
    return {
      status: directRule.allow ? "allow" : "deny",
      inherited: false,
      sourceLabel: sourceLabelForScope(cId, schema, table),
    };
  }

  if (column) {
    const tableRule = getRule(cId, schema, table);
    if (tableRule) {
      return {
        status: tableRule.allow ? "allow" : "deny",
        inherited: true,
        sourceLabel: sourceLabelForScope(cId, schema, table),
      };
    }
  }

  if (table || column) {
    const schemaRule = getRule(cId, schema);
    if (schemaRule) {
      return {
        status: schemaRule.allow ? "allow" : "deny",
        inherited: true,
        sourceLabel: sourceLabelForScope(cId, schema),
      };
    }
  }

  if (schema || table || column) {
    const catalogRule = getRule(cId);
    if (catalogRule) {
      return {
        status: catalogRule.allow ? "allow" : "deny",
        inherited: true,
        sourceLabel: sourceLabelForScope(cId),
      };
    }
  }

  return {
    status: "deny",
    inherited: true,
    sourceLabel: "default policy",
  };
}

function effectiveStatusOf(
  cId: number,
  schema = "",
  table = "",
  column = "",
): "allow" | "deny" {
  return resolveEffectiveAccess(cId, schema, table, column).status;
}

function badgeLabelOf(cId: number, schema = "", table = "", column = "") {
  const directStatus = statusOf(cId, schema, table, column);
  if (directStatus !== "inherit") return directStatus;

  const resolved = resolveEffectiveAccess(cId, schema, table, column);
  return `inherited: ${resolved.status === "allow" ? "allowed" : "denied"} by ${
    resolved.sourceLabel
  }`;
}

function cardClassOf(cId: number, schema = "", table = "", column = "") {
  return subtleCardClass(effectiveStatusOf(cId, schema, table, column));
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
        ensureSet(nextTablesByScope, `${catalogId}|${entry.schema_name}`).add(
          entry.table_name,
        );
      }
      if (entry.table_name && entry.column_name) {
        ensureSet(
          nextColsByScope,
          `${catalogId}|${entry.schema_name}|${entry.table_name}`,
        ).add(entry.column_name);
      }
    }
  }

  for (const rule of rules.value) {
    if (!rule.schema_name) continue;

    ensureSet(nextSchemasByCatalog, rule.catalog_id).add(rule.schema_name);

    if (rule.table_name) {
      ensureSet(
        nextTablesByScope,
        `${rule.catalog_id}|${rule.schema_name}`,
      ).add(rule.table_name);
    }

    if (rule.table_name && rule.column_name) {
      ensureSet(
        nextColsByScope,
        `${rule.catalog_id}|${rule.schema_name}|${rule.table_name}`,
      ).add(rule.column_name);
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
  } catch (error) {
    console.error(error);
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

function previewMatchesScope(catalogId: number, schema = "", table = "") {
  const scope = tableConfig.value;
  return (
    !!scope &&
    scope.catalogId === catalogId &&
    scope.schema === schema &&
    scope.table === table
  );
}

function queuePreviewRefresh(delay = 250) {
  if (!tableConfig.value) return;

  if (previewTimer != null) {
    window.clearTimeout(previewTimer);
  }

  previewTimer = window.setTimeout(() => {
    previewTimer = null;
    void refreshTablePreview();
  }, delay);
}

async function refreshTablePreview() {
  const scope = tableConfig.value;
  if (!scope) return;

  const requestId = ++previewRequestSequence;
  previewLoading.value = true;
  previewRequestError.value = "";

  try {
    const data = await CatalogAPI.previewTable(scope.catalogId, {
      user_id: props.userId,
      schema_name: scope.schema,
      table_name: scope.table,
      limit: 5,
    });

    if (requestId !== previewRequestSequence) return;
    preview.value = data;
  } catch (error) {
    if (requestId !== previewRequestSequence) return;
    preview.value = null;
    previewRequestError.value = axios.isAxiosError(error)
      ? error.response?.data?.detail || "Unable to load preview"
      : "Unable to load preview";
  } finally {
    if (requestId === previewRequestSequence) {
      previewLoading.value = false;
    }
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
      rebuildSchemaTree();
      if (previewMatchesScope(cId, schema, table)) queuePreviewRefresh();
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
    rebuildSchemaTree();
    if (previewMatchesScope(cId, schema, table)) queuePreviewRefresh();
    return created;
  } catch (error) {
    console.error(error);
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
    rebuildSchemaTree();
    if (previewMatchesScope(cId, schema, table)) queuePreviewRefresh();
  } catch (error) {
    console.error(error);
    toast.add({
      severity: "error",
      summary: "Error",
      detail: "Unable to delete",
      life: 3000,
    });
  }
}

const setAllow = (cId: number, schema = "", table = "", column = "") =>
  upsertRule(cId, schema, table, column, { allow: true });
const setDeny = (cId: number, schema = "", table = "", column = "") =>
  upsertRule(cId, schema, table, column, { allow: false });

async function setInherit(cId: number, schema = "", table = "", column = "") {
  const hadRule = !!getRule(cId, schema, table, column);
  await deleteRule(cId, schema, table, column);
  if (!hadRule) {
    await deleteManualSchemaEntry(cId, schema, table, column);
  }
}

function getEffectScope(cId: number, schema = "", table = "", column = "") {
  const key = keyFor(props.userId, cId, schema, table, column);
  if (effectDrafts.value.has(key)) return effectDrafts.value.get(key)!;
  return getRule(cId, schema, table, column)?.effect ?? "";
}

function setEffectScope(
  cId: number,
  schema = "",
  table = "",
  column = "",
  value = "",
) {
  const key = keyFor(props.userId, cId, schema, table, column);
  effectDrafts.value.set(key, value);

  if (effectTimers.value.has(key)) {
    window.clearTimeout(effectTimers.value.get(key));
  }

  const timer = window.setTimeout(async () => {
    effectTimers.value.delete(key);
    await upsertRule(cId, schema, table, column, { effect: value });
    toast.add({
      severity: "success",
      summary: "Saved",
      detail: "Effect updated",
      life: 1000,
    });
  }, 600);

  effectTimers.value.set(key, timer);
}

function hasScannedPath(
  catalogId: number,
  schema = "",
  table = "",
  column = "",
) {
  return (
    getSchemaEntry(catalogId, schema, table, column)?.present_in_database ??
    false
  );
}

function hintForPath(catalogId: number, schema = "", table = "", column = "") {
  return hasScannedPath(catalogId, schema, table, column)
    ? undefined
    : missingPathHint;
}

function canRemoveMissingPath(
  catalogId: number,
  schema = "",
  table = "",
  column = "",
) {
  if (hasScannedPath(catalogId, schema, table, column)) return false;
  return (
    !!getRule(catalogId, schema, table, column) ||
    !!getSchemaEntry(catalogId, schema, table, column)
  );
}

async function refreshCatalogSchema(catalogId: number) {
  await loadCatalogSchema(catalogId, true);
}

async function createManualSchemaEntry(
  catalogId: number,
  schema = "",
  table = "",
  column = "",
) {
  mutatingSchemaEntry.value = true;
  try {
    const entry = await CatalogAPI.createSchemaEntry(catalogId, {
      schema_name: schema,
      table_name: table || null,
      column_name: column || null,
    });
    await refreshCatalogSchema(catalogId);
    if (previewMatchesScope(catalogId, schema, table)) queuePreviewRefresh();
    return entry;
  } catch (error) {
    console.error(error);
    let detail = "Unable to add schema entry";
    if (axios.isAxiosError(error)) {
      detail = error.response?.data?.detail || detail;
    }
    toast.add({ severity: "error", summary: "Error", detail, life: 4000 });
  } finally {
    mutatingSchemaEntry.value = false;
  }
}

async function deleteManualSchemaEntry(
  catalogId: number,
  schema = "",
  table = "",
  column = "",
) {
  const entry = getSchemaEntry(catalogId, schema, table, column);
  if (!entry?.manually_added) return false;

  mutatingSchemaEntry.value = true;
  try {
    await CatalogAPI.deleteSchemaEntry(catalogId, entry.id);
    await refreshCatalogSchema(catalogId);
    if (previewMatchesScope(catalogId, schema, table)) queuePreviewRefresh();
    return true;
  } catch (error) {
    console.error(error);
    let detail = "Unable to remove manual schema entry";
    if (axios.isAxiosError(error)) {
      detail = error.response?.data?.detail || detail;
    }
    toast.add({ severity: "error", summary: "Error", detail, life: 4000 });
    return false;
  } finally {
    mutatingSchemaEntry.value = false;
  }
}

async function removeMissingPath(
  catalogId: number,
  schema = "",
  table = "",
  column = "",
) {
  const hadRule = !!getRule(catalogId, schema, table, column);
  const hadManualEntry = !!getSchemaEntry(catalogId, schema, table, column)
    ?.manually_added;

  if (!hadRule && !hadManualEntry) return;

  if (hadRule) {
    await deleteRule(catalogId, schema, table, column);
  }
  if (hadManualEntry) {
    await deleteManualSchemaEntry(catalogId, schema, table, column);
  }
}

function closeTableConfig() {
  tableConfigVisible.value = false;
  tableConfig.value = null;
  preview.value = null;
  previewLoading.value = false;
  previewRequestError.value = "";
  draftColumnName.value = "";
  previewRequestSequence += 1;

  if (previewTimer != null) {
    window.clearTimeout(previewTimer);
    previewTimer = null;
  }
}

function openTableConfig(key: string) {
  const [, rawCatalogId, schema, table] = key.split(":");
  const catalogId = Number(rawCatalogId);

  selectedCatalogId.value = catalogId;
  selectedSchema.value = schema;
  selectedTable.value = table;

  tableConfig.value = { catalogId, schema, table };
  tableConfigVisible.value = true;
  preview.value = null;
  previewRequestError.value = "";
  void refreshTablePreview();
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
  draftSchemaName.value = "";
  draftTableName.value = "";
  draftColumnName.value = "";
  effectDrafts.value.clear();
  effectTimers.value.forEach((timer) => window.clearTimeout(timer));
  effectTimers.value.clear();
  loadingSchema.value = false;
  syncingSchema.value = false;
  mutatingSchemaEntry.value = false;
  closeTableConfig();
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
    rebuildSchemaTree();

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
  } catch (error) {
    console.error(error);
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
    if (
      tableConfig.value &&
      tableConfig.value.catalogId === selectedCatalogId.value
    ) {
      queuePreviewRefresh();
    }
    toast.add({
      severity: "success",
      summary: "Schema synchronized",
      detail: `${summary.schemas} schema(s), ${summary.tables} table(s), ${summary.columns} column(s)`,
      life: 3000,
    });
  } catch (error) {
    console.error(error);
    let detail = "Unable to synchronize schema";
    if (axios.isAxiosError(error)) {
      detail = error.response?.data?.detail || detail;
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
  catalogs.value.map((catalog) => ({
    key: `cat:${catalog.id}`,
    label: catalog.name,
  })),
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

function badgeLabelOfCatalogKey(key: string) {
  const [, id] = key.split(":");
  return badgeLabelOf(Number(id));
}

function badgeToneOfCatalogKey(key: string) {
  const [, id] = key.split(":");
  return effectiveStatusOf(Number(id));
}

function cardClassOfCatalogKey(key: string) {
  const [, id] = key.split(":");
  return cardClassOf(Number(id));
}

const allowCatalogKey = (key: string) => setAllow(Number(key.split(":")[1]));
const denyCatalogKey = (key: string) => setDeny(Number(key.split(":")[1]));
const inheritCatalogKey = (key: string) =>
  setInherit(Number(key.split(":")[1]));

const schemaItems = computed<ScopeItem[]>(() => {
  if (!selectedCatalogId.value) return [];
  const catalogId = selectedCatalogId.value;
  const schemas = Array.from(ensureSet(schemasByCatalog.value, catalogId)).sort(
    (a, b) => a.localeCompare(b),
  );
  return schemas.map((schema) => ({
    key: `sch:${catalogId}:${schema}`,
    label: schema,
    hint: hintForPath(catalogId, schema),
    removable: canRemoveMissingPath(catalogId, schema),
  }));
});

const selectedSchemaKey = computed(() =>
  selectedCatalogId.value && selectedSchema.value
    ? `sch:${selectedCatalogId.value}:${selectedSchema.value}`
    : null,
);

function selectSchema(key: string) {
  if (key === "__add__") {
    void addManualSchema();
    return;
  }
  const [, cId, schema] = key.split(":");
  selectedCatalogId.value = Number(cId);
  selectedSchema.value = schema;
}

function statusOfSchemaKey(key: string) {
  const [, cId, schema] = key.split(":");
  return statusOf(Number(cId), schema);
}

function badgeLabelOfSchemaKey(key: string) {
  const [, cId, schema] = key.split(":");
  return badgeLabelOf(Number(cId), schema);
}

function badgeToneOfSchemaKey(key: string) {
  const [, cId, schema] = key.split(":");
  return effectiveStatusOf(Number(cId), schema);
}

function cardClassOfSchemaKey(key: string) {
  const [, cId, schema] = key.split(":");
  return cardClassOf(Number(cId), schema);
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
const removeSchemaKey = (key: string) => {
  const [, cId, schema] = key.split(":");
  return removeMissingPath(Number(cId), schema);
};

const tableItems = computed<ScopeItem[]>(() => {
  if (!selectedCatalogId.value || !selectedSchema.value) return [];
  const catalogId = selectedCatalogId.value;
  const schema = selectedSchema.value;
  const tables = Array.from(
    ensureSet(tablesByScope.value, `${catalogId}|${schema}`),
  ).sort((a, b) => a.localeCompare(b));
  return tables.map((table) => ({
    key: `tbl:${catalogId}:${schema}:${table}`,
    label: table,
    hint: hintForPath(catalogId, schema, table),
    removable: canRemoveMissingPath(catalogId, schema, table),
  }));
});

const selectedTableKey = computed(() =>
  selectedCatalogId.value && selectedSchema.value && selectedTable.value
    ? `tbl:${selectedCatalogId.value}:${selectedSchema.value}:${selectedTable.value}`
    : null,
);

function selectTable(key: string) {
  if (key === "__add__") {
    void addManualTable();
    return;
  }
  const [, cId, schema, table] = key.split(":");
  selectedCatalogId.value = Number(cId);
  selectedSchema.value = schema;
  selectedTable.value = table;
}

function statusOfTableKey(key: string) {
  const [, cId, schema, table] = key.split(":");
  return statusOf(Number(cId), schema, table);
}

function badgeLabelOfTableKey(key: string) {
  const [, cId, schema, table] = key.split(":");
  return badgeLabelOf(Number(cId), schema, table);
}

function effectiveStatusOfTableKey(key: string) {
  const [, cId, schema, table] = key.split(":");
  return effectiveStatusOf(Number(cId), schema, table);
}

function cardClassOfTableKey(key: string) {
  const [, cId, schema, table] = key.split(":");
  return cardClassOf(Number(cId), schema, table);
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
const removeTableKey = (key: string) => {
  const [, cId, schema, table] = key.split(":");
  return removeMissingPath(Number(cId), schema, table);
};

function getColumnsForTable(catalogId: number, schema: string, table: string) {
  const columns = Array.from(
    ensureSet(colsByScope.value, `${catalogId}|${schema}|${table}`),
  ).sort((a, b) => a.localeCompare(b));

  return columns.map((column) => ({
    key: `col:${catalogId}:${schema}:${table}:${column}`,
    label: column,
    hint: hintForPath(catalogId, schema, table, column),
    removable: canRemoveMissingPath(catalogId, schema, table, column),
  }));
}

const tableColumnIndicators = computed(() => {
  const next = new Map<string, TableColumnIndicator[]>();

  for (const item of tableItems.value) {
    const [, rawCatalogId, schema, table] = item.key.split(":");
    const catalogId = Number(rawCatalogId);
    const indicators: TableColumnIndicator[] = [];

    for (const column of getColumnsForTable(catalogId, schema, table)) {
      const columnRule = getRule(catalogId, schema, table, column.label);
      const masked = !!columnRule?.effect?.trim();
      const status = effectiveStatusOf(catalogId, schema, table, column.label);

      indicators.push({
        label: column.label,
        hint: column.hint,
        status,
        masked: status === "allow" && masked,
      });
    }

    next.set(item.key, indicators);
  }

  return next;
});

function columnsForTableKey(key: string): TableColumnIndicator[] {
  return tableColumnIndicators.value.get(key) ?? [];
}

const tableCardColumnDisplays = computed(() => {
  const next = new Map<string, TableCardColumnDisplay>();

  for (const [key, indicators] of tableColumnIndicators.value.entries()) {
    const allow = indicators.filter((column) => column.status === "allow");
    const deny = indicators.filter((column) => column.status === "deny");

    next.set(key, {
      allow: allow.slice(0, TABLE_CARD_COLUMN_LIMIT_PER_STATUS),
      deny: deny.slice(0, TABLE_CARD_COLUMN_LIMIT_PER_STATUS),
      extraAllow: Math.max(
        0,
        allow.length - TABLE_CARD_COLUMN_LIMIT_PER_STATUS,
      ),
      extraDeny: Math.max(0, deny.length - TABLE_CARD_COLUMN_LIMIT_PER_STATUS),
    });
  }

  return next;
});

function tableCardColumnsForKey(key: string): TableCardColumnDisplay {
  return (
    tableCardColumnDisplays.value.get(key) ?? {
      allow: [],
      deny: [],
      extraAllow: 0,
      extraDeny: 0,
    }
  );
}

const activeColumnItems = computed<ScopeItem[]>(() => {
  const scope = tableConfig.value;
  if (!scope) return [];
  return getColumnsForTable(scope.catalogId, scope.schema, scope.table);
});

const activeTableLabel = computed(() =>
  tableConfig.value
    ? `${tableConfig.value.schema}.${tableConfig.value.table}`
    : "",
);

async function addManualSchema() {
  if (!selectedCatalogId.value) return;
  const schema = draftSchemaName.value.trim();
  if (!schema) return;

  const created = await createManualSchemaEntry(
    selectedCatalogId.value,
    schema,
  );
  if (!created) return;

  draftSchemaName.value = "";
  selectedSchema.value = schema;
  toast.add({
    severity: "success",
    summary: "Added",
    detail: `Manual schema ${schema} added`,
    life: 2000,
  });
}

async function addManualTable() {
  if (!selectedCatalogId.value || !selectedSchema.value) return;
  const table = draftTableName.value.trim();
  if (!table) return;

  const created = await createManualSchemaEntry(
    selectedCatalogId.value,
    selectedSchema.value,
    table,
  );
  if (!created) return;

  draftTableName.value = "";
  selectedTable.value = table;
  toast.add({
    severity: "success",
    summary: "Added",
    detail: `Manual table ${table} added`,
    life: 2000,
  });
}

async function addManualColumn() {
  const scope = tableConfig.value;
  if (!scope) return;

  const column = draftColumnName.value.trim();
  if (!column) return;

  const created = await createManualSchemaEntry(
    scope.catalogId,
    scope.schema,
    scope.table,
    column,
  );
  if (!created) return;

  draftColumnName.value = "";
  toast.add({
    severity: "success",
    summary: "Added",
    detail: `Manual column ${column} added`,
    life: 2000,
  });
}

function statusOfColumnKey(key: string) {
  const [, cId, schema, table, column] = key.split(":");
  return statusOf(Number(cId), schema, table, column);
}

function badgeLabelOfColumnKey(key: string) {
  const [, cId, schema, table, column] = key.split(":");
  return badgeLabelOf(Number(cId), schema, table, column);
}

function effectiveStatusOfColumnKey(key: string) {
  const [, cId, schema, table, column] = key.split(":");
  return effectiveStatusOf(Number(cId), schema, table, column);
}

function cardClassOfColumnKey(key: string) {
  const [, cId, schema, table, column] = key.split(":");
  return cardClassOf(Number(cId), schema, table, column);
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
const removeColumnKey = (key: string) => {
  const [, cId, schema, table, column] = key.split(":");
  return removeMissingPath(Number(cId), schema, table, column);
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
    for (const raw of json.rules as ExportRule[]) {
      const schema = (raw.schema_name ?? "").trim();
      const table = (raw.table_name ?? "").trim();
      const column = (raw.column_name ?? "").trim();
      const allow = !!raw.allow;
      const effect = table || column ? raw.effect ?? "" : "";

      const existed = !!getRule(catalogId, schema, table, column);
      await upsertRule(catalogId, schema, table, column, { allow, effect });
      if (existed) updated++;
      else created++;
    }

    await loadAll();

    toast.add({
      severity: "success",
      summary: "Import terminé",
      detail: `${created} créé(e)s, ${updated} mis(e)s à jour`,
      life: 3000,
    });
  } catch (error: unknown) {
    console.error(error);
    toast.add({
      severity: "error",
      summary: "Import échoué",
      detail: error instanceof Error ? error.message : "Erreur inconnue",
      life: 3000,
    });
  } finally {
    busyImport.value = false;
  }
}

function formatPreviewCell(value: unknown) {
  if (value === null) return "null";
  if (value === undefined) return "";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean")
    return String(value);
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

function datasetColumns(dataset?: CatalogPreviewDataset) {
  return dataset?.columns ?? [];
}

function datasetRows(dataset?: CatalogPreviewDataset) {
  return (dataset?.rows ?? []).slice(0, 5);
}
</script>

<template>
  <div class="space-y-3">
    <div class="flex items-center justify-end gap-2">
      <button
        class="px-3 py-2 text-sm border rounded-lg hover:bg-gray-50 disabled:opacity-50"
        :disabled="
          !selectedCatalogId || loading || loadingSchema || syncingSchema
        "
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

    <div v-else class="grid grid-cols-1 gap-3 xl:grid-cols-4">
      <RuleScopePanel
        title="Databases"
        :items="catalogItems"
        :selected-key="selectedCatalogKey"
        :status-of="statusOfCatalogKey"
        :badge-label-of="badgeLabelOfCatalogKey"
        :badge-tone-of="badgeToneOfCatalogKey"
        :card-class-of="cardClassOfCatalogKey"
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
        :badge-label-of="badgeLabelOfSchemaKey"
        :badge-tone-of="badgeToneOfSchemaKey"
        :card-class-of="cardClassOfSchemaKey"
        :on-allow="allowSchemaKey"
        :on-deny="denySchemaKey"
        :on-inherit="inheritSchemaKey"
        :on-remove="removeSchemaKey"
        :show-add="true"
        :add-model="draftSchemaName"
        add-placeholder="Add manual schema"
        remove-title="Remove missing schema item"
        :add-disabled="
          !selectedCatalogId ||
          loading ||
          loadingSchema ||
          syncingSchema ||
          mutatingSchemaEntry
        "
        @update:add-model="(value) => (draftSchemaName = value)"
        @select="selectSchema"
      />

      <div
        class="bg-white rounded-2xl shadow p-3 h-full flex flex-col xl:col-span-2"
      >
        <div class="mb-3">
          <h2 class="font-semibold text-sm">Tables</h2>
        </div>

        <ul class="space-y-2 pr-1 flex-1 min-h-0 mb-5 overflow-auto">
          <li
            v-for="it in tableItems"
            :key="it.key"
            class="rounded-xl p-3 cursor-pointer transition-colors"
            :class="cardClassOfTableKey(it.key)"
            @click="selectTable(it.key)"
          >
            <div class="flex items-start justify-between gap-3">
              <div class="min-w-0">
                <div class="flex items-center gap-2 min-w-0">
                  <div class="text-sm font-medium truncate">{{ it.label }}</div>
                  <i
                    v-if="it.hint"
                    class="pi pi-exclamation-triangle text-[11px] text-amber-500 shrink-0"
                    :title="it.hint"
                    :aria-label="it.hint"
                  ></i>
                </div>
              </div>

              <div class="flex flex-col items-end gap-2 shrink-0">
                <div class="flex items-center gap-2">
                  <div class="inline-flex border rounded-lg">
                    <button
                      :class="segBtn(statusOfTableKey(it.key) === 'allow')"
                      @click.stop="allowTableKey(it.key)"
                      title="Autoriser"
                    >
                      <i class="pi pi-check text-xs"></i>
                    </button>
                    <button
                      :class="segBtn(statusOfTableKey(it.key) === 'deny')"
                      @click.stop="denyTableKey(it.key)"
                      title="Refuser"
                    >
                      <i class="pi pi-ban text-xs"></i>
                    </button>
                    <button
                      :class="segBtn(statusOfTableKey(it.key) === 'inherit')"
                      @click.stop="inheritTableKey(it.key)"
                      title="Hériter"
                    >
                      <i class="pi pi-undo text-xs"></i>
                    </button>
                  </div>

                  <button
                    class="inline-flex items-center justify-center h-8 w-8 border rounded-lg text-gray-700 hover:bg-gray-100"
                    title="Configure table"
                    @click.stop="openTableConfig(it.key)"
                  >
                    <i class="pi pi-cog text-sm"></i>
                  </button>
                </div>

                <div class="flex items-center gap-2">
                  <button
                    v-if="it.removable"
                    class="inline-flex items-center justify-center h-8 w-8 border rounded-lg text-amber-600 hover:bg-amber-50"
                    title="Remove missing table item"
                    @click.stop="removeTableKey(it.key)"
                  >
                    <i class="pi pi-trash text-xs"></i>
                  </button>
                </div>
              </div>
            </div>

            <div class="flex items-center gap-2 flex-wrap">
              <span
                class="text-[10px] px-1.5 py-0.5 border rounded whitespace-normal break-words"
                :class="badgeClass(effectiveStatusOfTableKey(it.key))"
              >
                {{ badgeLabelOfTableKey(it.key) }}
              </span>
            </div>

            <div
              class="mt-3 rounded-xl border border-slate-200/80 bg-white/80 p-3"
            >
              <div
                class="text-[10px] font-medium uppercase tracking-wide text-slate-500"
              >
                Columns
              </div>
              <div
                v-if="columnsForTableKey(it.key).length"
                class="mt-2 flex flex-wrap gap-1.5"
              >
                <span
                  v-for="column in tableCardColumnsForKey(it.key).allow"
                  :key="`${it.key}-${column.label}`"
                  class="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] border"
                  :class="columnPillClass(column.status)"
                  :title="
                    column.masked
                      ? `${
                          column.hint ? `${column.hint} • ` : ''
                        }Available but masked`
                      : column.hint
                  "
                >
                  {{ column.label }}
                  <i
                    v-if="column.masked"
                    class="pi pi-eye-slash text-[10px]"
                    aria-label="Masked column"
                  ></i>
                </span>
                <span
                  v-if="tableCardColumnsForKey(it.key).extraAllow > 0"
                  class="inline-flex items-center rounded-full px-2 py-0.5 text-[11px] border"
                  :class="columnPillClass('allow')"
                >
                  + {{ tableCardColumnsForKey(it.key).extraAllow }} others
                </span>
                <span
                  v-for="column in tableCardColumnsForKey(it.key).deny"
                  :key="`${it.key}-${column.label}`"
                  class="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] border"
                  :class="columnPillClass(column.status)"
                  :title="column.hint"
                >
                  {{ column.label }}
                </span>
                <span
                  v-if="tableCardColumnsForKey(it.key).extraDeny > 0"
                  class="inline-flex items-center rounded-full px-2 py-0.5 text-[11px] border"
                  :class="columnPillClass('deny')"
                >
                  + {{ tableCardColumnsForKey(it.key).extraDeny }} others
                </span>
              </div>
              <div v-else class="mt-2 text-xs text-slate-500">No columns</div>
            </div>
          </li>
        </ul>

        <div class="space-y-2 border-t pt-3 mt-auto">
          <input
            :value="draftTableName"
            @input="draftTableName = ($event.target as HTMLInputElement).value"
            placeholder="Add manual table"
            class="px-2 py-1 h-8 text-sm border rounded-lg w-full"
            :disabled="
              !selectedCatalogId ||
              !selectedSchema ||
              loading ||
              loadingSchema ||
              syncingSchema ||
              mutatingSchemaEntry
            "
          />
          <button
            class="h-8 px-2 text-sm border rounded-lg hover:bg-gray-50 text-gray-700 disabled:opacity-50 w-full"
            :disabled="
              !selectedCatalogId ||
              !selectedSchema ||
              !draftTableName.trim() ||
              loading ||
              loadingSchema ||
              syncingSchema ||
              mutatingSchemaEntry
            "
            @click="addManualTable"
          >
            Add
          </button>
        </div>
      </div>
    </div>

    <Dialog
      v-model:visible="tableConfigVisible"
      modal
      header="Configure table"
      :style="{ width: 'min(1280px, 96vw)' }"
      @hide="closeTableConfig"
    >
      <div v-if="tableConfig" class="space-y-4">
        <div class="rounded-2xl border border-slate-200 bg-slate-50 p-4">
          <div class="flex items-start justify-between gap-3">
            <div>
              <div class="text-xs uppercase tracking-[0.2em] text-slate-500">
                Table
              </div>
              <h3 class="text-lg font-semibold text-slate-900">
                {{ activeTableLabel }}
              </h3>
              <p class="mt-1 text-sm text-slate-600">
                Changes are saved automatically and the preview refreshes after
                each update.
              </p>
            </div>

            <div class="flex flex-col items-end gap-2 shrink-0">
              <div class="inline-flex border rounded-lg">
                <button
                  :class="
                    segBtn(
                      statusOf(
                        tableConfig.catalogId,
                        tableConfig.schema,
                        tableConfig.table,
                      ) === 'allow',
                    )
                  "
                  @click="
                    setAllow(
                      tableConfig.catalogId,
                      tableConfig.schema,
                      tableConfig.table,
                    )
                  "
                  title="Autoriser"
                >
                  <i class="pi pi-check text-xs"></i>
                </button>
                <button
                  :class="
                    segBtn(
                      statusOf(
                        tableConfig.catalogId,
                        tableConfig.schema,
                        tableConfig.table,
                      ) === 'deny',
                    )
                  "
                  @click="
                    setDeny(
                      tableConfig.catalogId,
                      tableConfig.schema,
                      tableConfig.table,
                    )
                  "
                  title="Refuser"
                >
                  <i class="pi pi-ban text-xs"></i>
                </button>
                <button
                  :class="
                    segBtn(
                      statusOf(
                        tableConfig.catalogId,
                        tableConfig.schema,
                        tableConfig.table,
                      ) === 'inherit',
                    )
                  "
                  @click="
                    setInherit(
                      tableConfig.catalogId,
                      tableConfig.schema,
                      tableConfig.table,
                    )
                  "
                  title="Hériter"
                >
                  <i class="pi pi-undo text-xs"></i>
                </button>
              </div>

              <div
                v-if="
                  !hasScannedPath(
                    tableConfig.catalogId,
                    tableConfig.schema,
                    tableConfig.table,
                  )
                "
                class="inline-flex items-center gap-2 rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-xs text-amber-700"
              >
                <i class="pi pi-exclamation-triangle text-[11px]"></i>
                Missing from scanned schema
              </div>
            </div>
          </div>

          <div class="mt-4 flex items-center gap-2 flex-wrap">
            <span
              class="text-[10px] px-1.5 py-0.5 border rounded whitespace-normal break-words"
              :class="
                badgeClass(
                  effectiveStatusOf(
                    tableConfig.catalogId,
                    tableConfig.schema,
                    tableConfig.table,
                  ),
                )
              "
            >
              {{
                badgeLabelOf(
                  tableConfig.catalogId,
                  tableConfig.schema,
                  tableConfig.table,
                )
              }}
            </span>
          </div>

          <div class="mt-4">
            <label class="block text-sm font-medium text-slate-700">
              Row filter
            </label>
            <textarea
              :value="
                getEffectScope(
                  tableConfig.catalogId,
                  tableConfig.schema,
                  tableConfig.table,
                )
              "
              @input="
                setEffectScope(
                  tableConfig.catalogId,
                  tableConfig.schema,
                  tableConfig.table,
                  '',
                  ($event.target as HTMLTextAreaElement).value,
                )
              "
              rows="3"
              class="mt-2 w-full rounded-xl border px-3 py-2 text-sm"
              placeholder="country = 'FR'"
            ></textarea>
            <p class="mt-1 text-xs text-slate-500">
              SQL WHERE clause applied by MaskQL on this table.
            </p>
          </div>
        </div>

        <div
          class="grid gap-4 xl:grid-cols-[minmax(0,1.05fr)_minmax(0,1.35fr)]"
        >
          <section class="rounded-2xl border bg-white p-4">
            <div class="flex items-center justify-between gap-3">
              <div>
                <h4 class="text-sm font-semibold text-gray-900">Columns</h4>
                <p class="text-xs text-gray-500">
                  {{ activeColumnItems.length }} column(s) on this table
                </p>
              </div>
            </div>

            <div class="mt-4 space-y-2 max-h-[32rem] overflow-auto pr-1">
              <div
                v-if="!activeColumnItems.length"
                class="rounded-xl border border-dashed p-4 text-sm text-gray-500"
              >
                No columns available for this table.
              </div>

              <div
                v-for="it in activeColumnItems"
                :key="it.key"
                class="rounded-xl p-2 transition-colors"
                :class="cardClassOfColumnKey(it.key)"
              >
                <div class="flex items-start justify-between gap-2">
                  <div class="min-w-0 flex-1">
                    <div class="flex items-center gap-2 min-w-0">
                      <div class="text-sm font-medium truncate">
                        {{ it.label }}
                      </div>
                      <i
                        v-if="it.hint"
                        class="pi pi-exclamation-triangle text-[11px] text-amber-500 shrink-0"
                        :title="it.hint"
                        :aria-label="it.hint"
                      ></i>
                    </div>

                    <div class="mt-1.5 flex items-center gap-1.5 flex-wrap">
                      <span
                        class="text-[10px] px-1.5 py-0.5 border rounded whitespace-normal break-words"
                        :class="badgeClass(effectiveStatusOfColumnKey(it.key))"
                      >
                        {{ badgeLabelOfColumnKey(it.key) }}
                      </span>
                    </div>
                  </div>

                  <div class="flex flex-col items-end gap-1.5 shrink-0">
                    <div class="inline-flex border rounded-lg">
                      <button
                        :class="segBtn(statusOfColumnKey(it.key) === 'allow')"
                        @click="allowColumnKey(it.key)"
                        title="Autoriser"
                      >
                        <i class="pi pi-check text-xs"></i>
                      </button>
                      <button
                        :class="segBtn(statusOfColumnKey(it.key) === 'deny')"
                        @click="denyColumnKey(it.key)"
                        title="Refuser"
                      >
                        <i class="pi pi-ban text-xs"></i>
                      </button>
                      <button
                        :class="segBtn(statusOfColumnKey(it.key) === 'inherit')"
                        @click="inheritColumnKey(it.key)"
                        title="Hériter"
                      >
                        <i class="pi pi-undo text-xs"></i>
                      </button>
                    </div>

                    <button
                      v-if="it.removable"
                      class="inline-flex items-center justify-center h-7 w-7 border rounded-lg text-amber-600 hover:bg-amber-50"
                      title="Remove missing column item"
                      @click="removeColumnKey(it.key)"
                    >
                      <i class="pi pi-trash text-xs"></i>
                    </button>
                  </div>
                </div>

                <div class="mt-2">
                  <label
                    class="block text-[10px] font-medium uppercase tracking-wide text-gray-500"
                  >
                    Mask / transform
                  </label>
                  <input
                    :value="getEffectColumnKey(it.key)"
                    @input="
                      setEffectColumnKey(
                        it.key,
                        ($event.target as HTMLInputElement).value,
                      )
                    "
                    class="mt-1.5 h-8 w-full px-2 py-1 text-sm border rounded-lg"
                    placeholder="lower(my_column)"
                  />
                </div>
              </div>
            </div>

            <div class="space-y-2 border-t pt-3 mt-4">
              <input
                :value="draftColumnName"
                @input="
                  draftColumnName = ($event.target as HTMLInputElement).value
                "
                placeholder="Add manual column"
                class="px-2 py-1 h-8 text-sm border rounded-lg w-full"
                :disabled="
                  loading ||
                  loadingSchema ||
                  syncingSchema ||
                  mutatingSchemaEntry
                "
              />
              <button
                class="h-8 px-2 text-sm border rounded-lg hover:bg-gray-50 text-gray-700 disabled:opacity-50 w-full"
                :disabled="
                  !draftColumnName.trim() ||
                  loading ||
                  loadingSchema ||
                  syncingSchema ||
                  mutatingSchemaEntry
                "
                @click="addManualColumn"
              >
                Add manual column
              </button>
            </div>
          </section>

          <section class="space-y-4">
            <div class="flex items-center justify-between gap-3">
              <div>
                <h4 class="text-sm font-semibold text-gray-900">Preview</h4>
                <p class="text-xs text-gray-500">
                  First 5 rows before and after MaskQL.
                </p>
              </div>

              <button
                class="px-3 py-2 text-sm border rounded-lg hover:bg-gray-50 disabled:opacity-50"
                :disabled="previewLoading"
                @click="refreshTablePreview"
              >
                <i class="pi pi-refresh mr-2 text-xs"></i>
                Refresh preview
              </button>
            </div>

            <div
              v-if="previewRequestError"
              class="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700"
            >
              {{ previewRequestError }}
            </div>

            <div
              v-if="previewLoading"
              class="rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-500"
            >
              <div class="flex items-center gap-3">
                <span
                  class="inline-block h-4 w-4 rounded-full border-2 border-slate-300 border-t-slate-600 animate-spin"
                  aria-hidden="true"
                ></span>
                <span class="animate-pulse">Refreshing preview...</span>
              </div>
            </div>

            <div class="space-y-4">
              <div class="rounded-2xl border bg-white overflow-hidden">
                <div class="border-b px-4 py-3">
                  <h5 class="text-sm font-semibold text-gray-900">
                    Before MaskQL
                  </h5>
                  <p class="text-xs text-gray-500">Without filters or masks.</p>
                </div>

                <div
                  v-if="preview?.before_maskql.error"
                  class="p-4 text-sm text-red-700"
                >
                  {{ preview.before_maskql.error }}
                </div>

                <div
                  v-else-if="!datasetColumns(preview?.before_maskql).length"
                  class="p-4 text-sm text-gray-500"
                >
                  No preview available.
                </div>

                <div v-else class="overflow-auto">
                  <table class="min-w-full text-sm">
                    <thead class="bg-slate-50">
                      <tr>
                        <th
                          v-for="column in datasetColumns(
                            preview?.before_maskql,
                          )"
                          :key="`before-head-${column}`"
                          class="px-3 py-2 text-left font-medium text-slate-600 whitespace-nowrap"
                        >
                          {{ column }}
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr
                        v-if="!datasetRows(preview?.before_maskql).length"
                        class="border-t"
                      >
                        <td
                          :colspan="
                            datasetColumns(preview?.before_maskql).length
                          "
                          class="px-3 py-6 text-center text-gray-500"
                        >
                          No rows
                        </td>
                      </tr>
                      <tr
                        v-for="(row, rowIndex) in datasetRows(
                          preview?.before_maskql,
                        )"
                        :key="`before-row-${rowIndex}`"
                        class="border-t align-top"
                      >
                        <td
                          v-for="column in datasetColumns(
                            preview?.before_maskql,
                          )"
                          :key="`before-cell-${rowIndex}-${column}`"
                          class="px-3 py-2 text-gray-700 whitespace-nowrap"
                        >
                          {{ formatPreviewCell(row[column]) }}
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>

              <div class="rounded-2xl border bg-white overflow-hidden">
                <div class="border-b px-4 py-3">
                  <h5 class="text-sm font-semibold text-gray-900">
                    After MaskQL
                  </h5>
                  <p class="text-xs text-gray-500">
                    With current access rules, row filters and masks.
                  </p>
                </div>

                <div
                  v-if="preview?.after_maskql.error"
                  class="p-4 text-sm text-red-700"
                >
                  {{ preview.after_maskql.error }}
                </div>

                <div
                  v-else-if="!datasetColumns(preview?.after_maskql).length"
                  class="p-4 text-sm text-gray-500"
                >
                  No preview available.
                </div>

                <div v-else class="overflow-auto">
                  <table class="min-w-full text-sm">
                    <thead class="bg-slate-50">
                      <tr>
                        <th
                          v-for="column in datasetColumns(
                            preview?.after_maskql,
                          )"
                          :key="`after-head-${column}`"
                          class="px-3 py-2 text-left font-medium text-slate-600 whitespace-nowrap"
                        >
                          {{ column }}
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr
                        v-if="!datasetRows(preview?.after_maskql).length"
                        class="border-t"
                      >
                        <td
                          :colspan="
                            datasetColumns(preview?.after_maskql).length
                          "
                          class="px-3 py-6 text-center text-gray-500"
                        >
                          No rows
                        </td>
                      </tr>
                      <tr
                        v-for="(row, rowIndex) in datasetRows(
                          preview?.after_maskql,
                        )"
                        :key="`after-row-${rowIndex}`"
                        class="border-t align-top"
                      >
                        <td
                          v-for="column in datasetColumns(
                            preview?.after_maskql,
                          )"
                          :key="`after-cell-${rowIndex}-${column}`"
                          class="px-3 py-2 text-gray-700 whitespace-nowrap"
                        >
                          {{ formatPreviewCell(row[column]) }}
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </section>
        </div>
      </div>
    </Dialog>
  </div>
</template>
