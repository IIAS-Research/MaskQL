<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import { useToast } from "primevue/usetoast";
import type { Catalog, CatalogConnectionStatus } from "../types/catalog";
import { CatalogAPI } from "../types/catalog";
import { getTrinoDbmsLabel } from "../constants/trinoDbms";

const router = useRouter();
const toast = useToast();

const loading = ref(false);
const loadingStatuses = ref(false);
const syncingCatalogId = ref<number | null>(null);
const catalogs = ref<Catalog[]>([]);
const statusByCatalogId = ref<Record<number, CatalogConnectionStatus>>({});
const q = ref("");

const filtered = computed(() => {
  const term = q.value.trim().toLowerCase();
  if (!term) return catalogs.value;
  return catalogs.value.filter((c) =>
    [
      c.name,
      c.url,
      c.sgbd,
      getTrinoDbmsLabel(c.sgbd),
      connectionStatusLabel(c.id),
      c.username,
    ].some((v) => (v || "").toLowerCase().includes(term)),
  );
});

async function fetchCatalogStatuses(items: Catalog[]) {
  statusByCatalogId.value = {};
  if (!items.length) return;

  loadingStatuses.value = true;
  try {
    const statuses = await CatalogAPI.listStatuses();
    statusByCatalogId.value = Object.fromEntries(
      statuses.map((status) => [status.catalog_id, status]),
    );
  } catch (e) {
    console.error(e);
  } finally {
    loadingStatuses.value = false;
  }
}

async function fetchCatalogs() {
  loading.value = true;
  try {
    catalogs.value = await CatalogAPI.list();
    void fetchCatalogStatuses(catalogs.value);
  } catch (e) {
    console.error(e);
    toast.add({
      severity: "error",
      summary: "Error",
      detail: "Unable to load databases",
      life: 3000,
    });
  } finally {
    loading.value = false;
  }
}

async function removeCatalog(id: number) {
  const ok = window.confirm("Delete database connection ?");
  if (!ok) return;

  try {
    await CatalogAPI.remove(id);
    toast.add({
      severity: "success",
      summary: "Deletec",
      detail: "Database connection deleted",
      life: 2000,
    });
    // refresh
    catalogs.value = catalogs.value.filter((c) => c.id !== id);
    const { [id]: _removed, ...rest } = statusByCatalogId.value;
    statusByCatalogId.value = rest;
  } catch (e) {
    console.error(e);
    toast.add({
      severity: "error",
      summary: "Error",
      detail: "Unable to delete database connection",
      life: 3000,
    });
  }
}

async function syncCatalogSchema(id: number) {
  syncingCatalogId.value = id;
  try {
    const summary = await CatalogAPI.syncSchema(id);
    toast.add({
      severity: "success",
      summary: "Schema synchronized",
      detail: `${summary.schemas} schema(s), ${summary.tables} table(s), ${summary.columns} column(s)`,
      life: 3000,
    });
    void fetchCatalogStatuses(catalogs.value);
  } catch (e: any) {
    console.error(e);
    toast.add({
      severity: "error",
      summary: "Error",
      detail: e?.response?.data?.detail || "Unable to synchronize schema",
      life: 4000,
    });
  } finally {
    syncingCatalogId.value = null;
  }
}

function connectionStatusLabel(catalogId: number) {
  const status = statusByCatalogId.value[catalogId];
  if (!status) return loadingStatuses.value ? "Checking" : "Unknown";
  return status.state === "ok" ? "Connected" : "Failed";
}

function connectionStatusTone(catalogId: number) {
  const status = statusByCatalogId.value[catalogId];
  if (!status) return loadingStatuses.value ? "bg-amber-400" : "bg-slate-400";
  return status.state === "ok" ? "bg-emerald-500" : "bg-red-500";
}

function connectionStatusTitle(catalogId: number) {
  const status = statusByCatalogId.value[catalogId];
  if (!status)
    return loadingStatuses.value
      ? "Checking database connection"
      : "Status unavailable";
  return status.message;
}

function goEdit(id: number) {
  router.push({ name: "catalog", params: { id } });
}

onMounted(fetchCatalogs);
</script>

<template>
  <div class="p-6 max-w-6xl mx-auto">
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-bold text-gray-800">Database connections</h1>
      <div class="flex gap-2">
        <input
          v-model="q"
          type="search"
          placeholder="Search"
          class="px-3 py-2 border rounded-lg focus:ring focus:outline-none"
        />
        <RouterLink
          to="/catalogs/new"
          class="px-3 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
          >Create database</RouterLink
        >
      </div>
    </div>

    <div class="overflow-x-auto bg-white rounded-2xl shadow">
      <table class="min-w-full text-sm">
        <thead>
          <tr class="text-left border-b">
            <th class="px-4 py-3">Name</th>
            <th class="px-4 py-3">URL</th>
            <th class="px-4 py-3">SGBD</th>
            <th class="px-4 py-3">Status</th>
            <th class="px-4 py-3">Username</th>
            <th class="px-4 py-3 w-40">Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading">
            <td class="px-4 py-4 text-gray-500" colspan="6">Loading...</td>
          </tr>

          <tr v-else-if="!filtered.length">
            <td class="px-4 py-4 text-gray-500" colspan="6">No result.</td>
          </tr>

          <tr
            v-for="c in filtered"
            :key="c.id"
            class="border-b hover:bg-gray-50"
          >
            <td class="px-4 py-3 font-medium">{{ c.name }}</td>
            <td class="px-4 py-3">
              <a
                :href="c.url"
                target="_blank"
                rel="noopener"
                class="text-indigo-600 hover:underline"
                >{{ c.url }}</a
              >
            </td>
            <td class="px-4 py-3">{{ getTrinoDbmsLabel(c.sgbd) }}</td>
            <td class="px-4 py-3">
              <span
                class="inline-flex items-center gap-2 text-sm text-gray-700"
                :title="connectionStatusTitle(c.id)"
              >
                <span
                  class="h-2.5 w-2.5 rounded-full"
                  :class="connectionStatusTone(c.id)"
                />
                {{ connectionStatusLabel(c.id) }}
              </span>
            </td>
            <td class="px-4 py-3">{{ c.username }}</td>
            <td class="px-4 py-3">
              <div class="flex gap-2">
                <button
                  class="px-3 py-1 rounded-lg bg-gray-800 text-white hover:bg-gray-700"
                  @click="goEdit(c.id)"
                  title="Edit"
                >
                  Edit
                </button>
                <button
                  class="px-3 py-1 rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50"
                  :disabled="syncingCatalogId === c.id"
                  @click="syncCatalogSchema(c.id)"
                  title="Sync schema"
                >
                  {{ syncingCatalogId === c.id ? "Syncing..." : "Sync schema" }}
                </button>
                <button
                  class="px-3 py-1 rounded-lg bg-red-600 text-white hover:bg-red-700"
                  @click="removeCatalog(c.id)"
                  title="Deleted"
                >
                  Delete
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped></style>
