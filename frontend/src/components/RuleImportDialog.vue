<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from "vue";
import Dialog from "primevue/dialog";
import { CatalogAPI } from "../types/catalog";
import { RuleAPI, type Rule } from "../types/rule";

const props = defineProps<{
  destination: {
    catalogId: number;
    catalogName: string;
    userId: number;
    userName: string;
  };
}>();
const emit = defineEmits<{
  (event: "close"): void;
  (event: "imported", rules: Rule[]): void;
}>();

type FileRule = {
  schema_name: string;
  table_name: string;
  column_name: string;
  allow: boolean;
  effect: string;
};
type ImportFile = {
  catalog_id?: number;
  catalog_name?: string;
  user_id?: number;
  user_name?: string;
  rules: FileRule[];
};
type PreviewRule = FileRule & {
  existing?: Rule;
  present: boolean | null;
  result?: "created" | "updated" | "rejected" | "skipped";
  error?: string;
};

const fileName = ref("");
const fileInput = ref<HTMLInputElement | null>(null);
const source = ref<ImportFile | null>(null);
const rows = ref<PreviewRule[]>([]);
const loading = ref(false);
const importing = ref(false);
const finished = ref(false);
const error = ref("");
const schemaWarning = ref("");
const confirmTransfer = ref(false);
const includeMissing = ref(false);
let requestId = 0;
let closed = false;
onBeforeUnmount(() => {
  closed = true;
  requestId++;
});

const pathKey = (rule: FileRule | Rule) =>
  JSON.stringify([
    rule.schema_name || "",
    rule.table_name || "",
    rule.column_name || "",
  ]);
const pathLabel = (rule: FileRule) =>
  [rule.schema_name, rule.table_name, rule.column_name]
    .filter(Boolean)
    .join(".") || "Toute la base";

function parseFile(value: unknown): ImportFile {
  if (!value || typeof value !== "object" || Array.isArray(value))
    throw new Error("Le fichier doit contenir un export de règles MaskQL.");
  const file = value as Record<string, unknown>;
  if (file.version !== undefined && file.version !== 1)
    throw new Error("Cette version du fichier n’est pas prise en charge.");
  if (!Array.isArray(file.rules) || !file.rules.length)
    throw new Error("Le fichier ne contient aucune règle.");
  for (const key of ["catalog_id", "user_id"]) {
    if (
      file[key] !== undefined &&
      (!Number.isInteger(file[key]) || Number(file[key]) < 1)
    )
      throw new Error(`Le champ ${key} du fichier est invalide.`);
  }
  for (const key of ["catalog_name", "user_name"]) {
    if (file[key] !== undefined && typeof file[key] !== "string")
      throw new Error(`Le champ ${key} du fichier est invalide.`);
  }
  const paths = new Set<string>();
  const rules = file.rules.map((raw: unknown, index: number) => {
    const fail = (message: string): never => {
      throw new Error(`Règle ${index + 1} : ${message}`);
    };
    if (!raw || typeof raw !== "object" || Array.isArray(raw))
      return fail("format invalide.");
    const row = raw as Record<string, unknown>;
    if (typeof row.allow !== "boolean")
      return fail("l’accès doit être true ou false.");
    const text = (key: string) => {
      if (row[key] == null) return "";
      if (typeof row[key] !== "string")
        return fail(`le champ ${key} doit être du texte.`);
      return (row[key] as string).trim();
    };
    const rule = {
      schema_name: text("schema_name"),
      table_name: text("table_name"),
      column_name: text("column_name"),
      allow: row.allow,
      effect: text("effect"),
    };
    if (
      (rule.table_name && !rule.schema_name) ||
      (rule.column_name && !rule.table_name)
    )
      return fail(
        "le chemin doit préciser le schéma, puis la table, puis la colonne.",
      );
    if (!rule.table_name) rule.effect = "";
    const key = pathKey(rule);
    if (paths.has(key))
      return fail(`le chemin « ${pathLabel(rule)} » apparaît plusieurs fois.`);
    paths.add(key);
    return rule;
  });
  return {
    catalog_id: file.catalog_id as number | undefined,
    catalog_name: (file.catalog_name as string | undefined)?.trim(),
    user_id: file.user_id as number | undefined,
    user_name: (file.user_name as string | undefined)?.trim(),
    rules,
  };
}

const warnings = computed(() => {
  const file = source.value;
  if (!file) return [];
  const messages: string[] = [];
  if (!file.catalog_name) {
    messages.push(
      "Le fichier ne précise pas le nom de la base source. Son identifiant seul ne permet pas de confirmer la destination.",
    );
  } else if (
    file.catalog_name !== props.destination.catalogName ||
    (file.catalog_id !== undefined &&
      file.catalog_id !== props.destination.catalogId)
  ) {
    messages.push(
      "Le nom ou l’identifiant de la base source ne correspond pas à la destination sélectionnée.",
    );
  }
  if (file.user_id === undefined && !file.user_name) {
    messages.push("L’utilisateur source n’est pas indiqué dans le fichier.");
  } else if (
    (file.user_id !== undefined && file.user_id !== props.destination.userId) ||
    (file.user_name && file.user_name !== props.destination.userName)
  ) {
    messages.push(
      "Le nom ou l’identifiant de l’utilisateur source ne correspond pas à la destination.",
    );
  }
  return messages;
});
const uncertainCount = computed(
  () => rows.value.filter((row) => row.present !== true).length,
);
const selectedRows = computed(() =>
  rows.value.filter((row) => row.present === true || includeMissing.value),
);
const canImport = computed(
  () =>
    source.value &&
    selectedRows.value.length > 0 &&
    !loading.value &&
    !importing.value &&
    !finished.value &&
    (!warnings.value.length || confirmTransfer.value),
);
const resultCount = (result: PreviewRule["result"]) =>
  rows.value.filter((row) => row.result === result).length;

async function chooseFile(event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  input.value = "";
  if (!file) return;
  const currentRequest = ++requestId;
  fileName.value = file.name;
  source.value = null;
  rows.value = [];
  error.value = "";
  schemaWarning.value = "";
  confirmTransfer.value = false;
  includeMissing.value = false;
  finished.value = false;
  loading.value = true;
  try {
    const parsed = parseFile(JSON.parse(await file.text()));
    const target = props.destination;
    const [rulesResult, schemaResult] = await Promise.allSettled([
      RuleAPI.list({ user_id: target.userId, catalog_id: target.catalogId }),
      CatalogAPI.inspectSchema(target.catalogId),
    ]);
    if (closed || currentRequest !== requestId) return;
    if (rulesResult.status === "rejected")
      throw new Error(
        "Impossible de lire les règles de destination. Réessaie avant d’importer.",
      );
    const existing = new Map(
      rulesResult.value.map((rule) => [pathKey(rule), rule]),
    );
    const paths =
      schemaResult.status === "fulfilled"
        ? new Set(
            schemaResult.value.map((path) =>
              JSON.stringify([
                path.schema_name,
                path.table_name || "",
                path.column_name || "",
              ]),
            ),
          )
        : null;
    if (!paths)
      schemaWarning.value =
        "La base cible n’a pas pu être vérifiée. Les chemins sont signalés comme non vérifiés.";
    source.value = parsed;
    rows.value = parsed.rules.map((rule) => ({
      ...rule,
      existing: existing.get(pathKey(rule)),
      present: !rule.schema_name
        ? true
        : paths
        ? paths.has(pathKey(rule))
        : null,
    }));
  } catch (cause) {
    if (closed || currentRequest !== requestId) return;
    error.value =
      cause instanceof SyntaxError
        ? "Le fichier n’est pas un JSON valide."
        : cause instanceof Error
        ? cause.message
        : "Impossible de préparer cet import.";
  } finally {
    if (currentRequest === requestId) loading.value = false;
  }
}

async function applyImport() {
  if (!canImport.value) return;
  importing.value = true;
  const target = { ...props.destination };
  const saved: Rule[] = [];
  try {
    for (const row of rows.value) {
      if (closed) break;
      if (row.present !== true && !includeMissing.value) {
        row.result = "skipped";
        continue;
      }
      try {
        const payload = {
          schema_name: row.schema_name,
          table_name: row.table_name,
          column_name: row.column_name,
          allow: row.allow,
          effect: row.effect,
        };
        const rule = row.existing
          ? await RuleAPI.update(row.existing.id, {
              allow: row.allow,
              effect: row.effect,
            })
          : await RuleAPI.create({
              ...payload,
              user_id: target.userId,
              catalog_id: target.catalogId,
            });
        saved.push(rule);
        row.result = row.existing ? "updated" : "created";
      } catch {
        row.result = "rejected";
        row.error =
          "Non importée. Vérifie l’expression et l’accès à ce chemin.";
      }
    }
    finished.value = true;
    emit("imported", saved);
  } finally {
    importing.value = false;
  }
}
</script>

<template>
  <Dialog
    :visible="true"
    modal
    header="Importer des règles"
    :closable="!importing"
    :close-on-escape="!importing"
    :style="{ width: 'min(1080px, 95vw)' }"
    @update:visible="!importing && emit('close')"
  >
    <div class="space-y-4">
      <div class="rounded-xl border border-accent-200 bg-accent-50 p-4">
        <p class="text-xs font-medium uppercase tracking-wide text-accent-700">
          Destination de l’import
        </p>
        <div class="mt-2 flex flex-wrap gap-x-10 gap-y-2">
          <div>
            <span class="text-sm text-slate-600">Base</span>
            <p class="text-lg font-semibold text-slate-900">
              {{ destination.catalogName }}
            </p>
            <p class="text-xs text-slate-500">
              Identifiant {{ destination.catalogId }}
            </p>
          </div>
          <div>
            <span class="text-sm text-slate-600">Utilisateur</span>
            <p class="text-lg font-semibold text-slate-900">
              {{ destination.userName }}
            </p>
            <p class="text-xs text-slate-500">
              Identifiant {{ destination.userId }}
            </p>
          </div>
        </div>
        <p class="mt-2 text-xs text-slate-600">
          Les règles aux mêmes chemins seront mises à jour. Les autres règles
          seront conservées.
        </p>
      </div>

      <div v-if="!finished">
        <p class="text-sm font-medium">Fichier de règles</p>
        <div class="mt-2 flex flex-wrap items-center gap-3">
          <button
            type="button"
            class="rounded-lg border px-3 py-2 text-sm hover:bg-slate-50 disabled:opacity-50"
            :disabled="loading || importing"
            @click="fileInput?.click()"
          >
            {{ fileName ? "Changer de fichier" : "Choisir un fichier JSON" }}
          </button>
          <span v-if="fileName" class="text-sm text-slate-600">{{
            fileName
          }}</span>
        </div>
        <input
          ref="fileInput"
          id="rule-import-file"
          type="file"
          accept="application/json,.json"
          class="hidden"
          :disabled="loading || importing"
          @change="chooseFile"
        />
      </div>
      <p v-if="loading" role="status" class="text-sm text-slate-600">
        Préparation de l’aperçu et vérification des chemins…
      </p>
      <p
        v-if="error"
        role="alert"
        class="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700"
      >
        {{ error }}
      </p>

      <template v-if="source">
        <div class="rounded-lg border p-3 text-sm">
          <p class="font-medium">Origine indiquée dans le fichier</p>
          <p class="mt-1">
            Base : {{ source.catalog_name || "nom non renseigné" }}
            <span v-if="source.catalog_id !== undefined" class="text-slate-500"
              >(identifiant {{ source.catalog_id }})</span
            >
          </p>
          <p>
            Utilisateur : {{ source.user_name || "nom non renseigné" }}
            <span v-if="source.user_id !== undefined" class="text-slate-500"
              >(identifiant {{ source.user_id }})</span
            >
          </p>
        </div>
        <div
          v-if="warnings.length"
          class="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900"
        >
          <p v-for="warning in warnings" :key="warning">{{ warning }}</p>
          <label
            v-if="!finished"
            class="mt-3 flex items-start gap-2 font-medium"
          >
            <input
              v-model="confirmTransfer"
              type="checkbox"
              class="mt-1"
              :disabled="importing"
            />
            <span
              >Je souhaite importer ces règles dans «
              {{ destination.catalogName }} » pour
              {{ destination.userName }}.</span
            >
          </label>
        </div>
        <p v-if="schemaWarning" class="text-sm text-amber-800">
          {{ schemaWarning }}
        </p>
        <label
          v-if="uncertainCount && !finished"
          class="flex items-start gap-2 rounded-lg border border-amber-200 p-3 text-sm"
        >
          <input
            v-model="includeMissing"
            type="checkbox"
            class="mt-1"
            :disabled="importing"
          />
          <span
            >Inclure aussi les chemins absents ou non vérifiés ({{
              uncertainCount
            }}). Leurs expressions devront être acceptées lors de
            l’enregistrement.</span
          >
        </label>

        <div class="max-h-80 overflow-auto rounded-lg border">
          <table class="w-full text-left text-sm">
            <thead class="sticky top-0 bg-slate-50">
              <tr>
                <th class="p-2">Chemin</th>
                <th class="p-2">Accès</th>
                <th class="p-2">Expression</th>
                <th class="p-2">Chemin cible</th>
                <th class="p-2">Action</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="row in rows"
                :key="pathKey(row)"
                class="border-t align-top"
                :class="{ 'bg-amber-50/50': row.present !== true }"
              >
                <td class="p-2 break-words">{{ pathLabel(row) }}</td>
                <td class="p-2">
                  {{ row.allow ? "Autoriser" : "Refuser" }}
                  <p
                    v-if="row.existing && row.existing.allow !== row.allow"
                    class="mt-1 text-xs text-slate-500"
                  >
                    Avant : {{ row.existing.allow ? "Autoriser" : "Refuser" }}
                  </p>
                </td>
                <td class="max-w-xs p-2">
                  <code class="whitespace-pre-wrap break-words">{{
                    row.effect || "—"
                  }}</code>
                  <p
                    v-if="
                      row.existing && (row.existing.effect || '') !== row.effect
                    "
                    class="mt-1 text-xs text-slate-500"
                  >
                    Avant : {{ row.existing.effect || "aucune expression" }}
                  </p>
                </td>
                <td
                  class="p-2"
                  :class="
                    row.present === true ? 'text-green-700' : 'text-amber-800'
                  "
                >
                  {{
                    row.present === true
                      ? "Présent"
                      : row.present === false
                      ? "Absent"
                      : "Non vérifié"
                  }}
                </td>
                <td class="p-2">
                  <span v-if="row.result === 'created'" class="text-green-700"
                    >Créée</span
                  >
                  <span
                    v-else-if="row.result === 'updated'"
                    class="text-green-700"
                    >Mise à jour</span
                  >
                  <span
                    v-else-if="row.result === 'rejected'"
                    class="text-red-700"
                    >{{ row.error }}</span
                  >
                  <span
                    v-else-if="
                      row.result === 'skipped' ||
                      (row.present !== true && !includeMissing)
                    "
                    >Exclue</span
                  >
                  <span v-else>{{
                    row.existing ? "Mettre à jour" : "Créer"
                  }}</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <p
          v-if="finished"
          role="status"
          class="rounded-lg border bg-slate-50 p-3 text-sm"
        >
          Import terminé : {{ resultCount("created") }} créée(s),
          {{ resultCount("updated") }} mise(s) à jour,
          {{ resultCount("rejected") }} refusée(s),
          {{ resultCount("skipped") }} exclue(s).
        </p>
      </template>
    </div>
    <template #footer>
      <button
        type="button"
        class="rounded-lg border px-3 py-2 text-sm disabled:opacity-50"
        :disabled="importing"
        @click="emit('close')"
      >
        {{ finished ? "Fermer" : "Annuler" }}
      </button>
      <button
        v-if="!finished"
        type="button"
        class="ml-2 rounded-lg bg-brand-600 px-3 py-2 text-sm text-white hover:bg-brand-700 disabled:opacity-50"
        :disabled="!canImport"
        @click="applyImport"
      >
        {{
          importing
            ? "Import en cours…"
            : `Importer ${selectedRows.length} règle(s) dans « ${destination.catalogName} »`
        }}
      </button>
    </template>
  </Dialog>
</template>
