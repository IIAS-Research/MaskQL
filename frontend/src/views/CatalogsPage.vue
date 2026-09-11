<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { RouterLink, useRouter } from "vue-router";
import { useToast } from "primevue/usetoast";
import Menu from "primevue/menu";
import type { MenuItem } from "primevue/menuitem";
import { CatalogAPI, type Catalog, type CatalogConnectionStatus } from "../types/catalog";
import { getTrinoDbmsLabel } from "../constants/trinoDbms";
import ConnectionStatusBadge from "../components/ConnectionStatusBadge.vue";
import { useDeleteConfirmation } from "../composables/useDeleteConfirmation";
import "../assets/directory.css";

const router = useRouter();
const toast = useToast();
const confirmDelete = useDeleteConfirmation();
const loading = ref(true);
const loadingStatuses = ref(false);
const loadError = ref(false);
const statusError = ref(false);
const pending = ref<{ id: number; action: "sync" | "duplicate" | "delete" } | null>(null);
const catalogs = ref<Catalog[]>([]);
const statusByCatalogId = ref<Record<number, CatalogConnectionStatus>>({});
const q = ref("");
const actionsMenu = ref<InstanceType<typeof Menu> | null>(null);
const menuItems = ref<MenuItem[]>([]);
const menuCatalogId = ref<number | null>(null);

const filtered = computed(() => {
  const term = q.value.trim().toLowerCase();
  return catalogs.value.filter(c =>
    [c.name, c.url, c.sgbd, getTrinoDbmsLabel(c.sgbd), connectionStatusLabel(c.id), c.username]
      .some(value => (value || "").toLowerCase().includes(term)),
  );
});

async function fetchCatalogStatuses() {
  if (loadingStatuses.value) return;
  statusByCatalogId.value = {};
  statusError.value = false;
  if (!catalogs.value.length) return;
  loadingStatuses.value = true;
  try {
    const statuses = await CatalogAPI.listStatuses();
    statusByCatalogId.value = Object.fromEntries(statuses.map(status => [status.catalog_id, status]));
  } catch {
    statusError.value = true;
  } finally {
    loadingStatuses.value = false;
  }
}

async function fetchCatalogs() {
  loading.value = true;
  loadError.value = false;
  try {
    catalogs.value = await CatalogAPI.list();
    void fetchCatalogStatuses();
  } catch {
    catalogs.value = [];
    loadError.value = true;
  } finally {
    loading.value = false;
  }
}

async function removeCatalog(catalog: Catalog) {
  if (pending.value) return;
  pending.value = { id: catalog.id, action: "delete" };
  try {
    await CatalogAPI.remove(catalog.id);
    catalogs.value = catalogs.value.filter(c => c.id !== catalog.id);
    delete statusByCatalogId.value[catalog.id];
    toast.add({ severity: "success", summary: "Deleted", detail: "Database connection deleted", life: 2000 });
  } catch {
    toast.add({ severity: "error", summary: "Unable to delete connection", detail: "Please try again.", life: 4000 });
  } finally {
    pending.value = null;
  }
}

async function syncCatalogSchema(id: number) {
  if (pending.value) return;
  pending.value = { id, action: "sync" };
  try {
    const summary = await CatalogAPI.syncSchema(id);
    toast.add({
      severity: "success", summary: "Schema synchronized",
      detail: `${summary.schemas} schema(s), ${summary.tables} table(s), ${summary.columns} column(s)`, life: 3000,
    });
    void fetchCatalogStatuses();
  } catch (error: any) {
    toast.add({ severity: "error", summary: "Unable to synchronize schema", detail: error?.response?.data?.detail || "Please try again.", life: 4000 });
  } finally {
    pending.value = null;
  }
}

async function duplicateCatalog(catalog: Catalog) {
  if (pending.value) return;
  pending.value = { id: catalog.id, action: "duplicate" };
  try {
    const duplicate = await CatalogAPI.duplicate(catalog.id);
    catalogs.value = [...catalogs.value, duplicate].sort((a, b) => a.name.localeCompare(b.name));
    toast.add({ severity: "success", summary: "Duplicated", detail: `Database connection copied as ${duplicate.name}`, life: 3000 });
    router.push({ name: "catalog", params: { id: duplicate.id } });
  } catch (error: any) {
    toast.add({ severity: "error", summary: "Unable to duplicate connection", detail: error?.response?.data?.detail || "Please try again.", life: 4000 });
  } finally {
    pending.value = null;
  }
}

function openActions(event: Event, catalog: Catalog) {
  const target = event.currentTarget as HTMLElement;
  menuCatalogId.value = catalog.id;
  menuItems.value = [
    { label: "Duplicate connection", icon: "pi pi-copy", command: () => duplicateCatalog(catalog) },
    { separator: true },
    {
      label: "Delete connection", icon: "pi pi-trash", class: "catalog-delete-action",
      command: () => confirmDelete({
        header: "Delete connection?",
        message: `The connection "${catalog.name}" and its rules will be deleted. The source database will stay unchanged.`,
        acceptLabel: "Delete connection",
        target,
        accept: () => removeCatalog(catalog),
      }),
    },
  ];
  actionsMenu.value?.toggle(event);
}
function connectionStatusLabel(id: number) {
  const status = statusByCatalogId.value[id];
  if (!status) return loadingStatuses.value ? "Checking" : "Unknown";
  return status.state === "ok" ? "Connected" : "Failed";
}

onMounted(fetchCatalogs);
</script>

<template>
  <main class="directory-page" aria-labelledby="databases-title">
    <header class="directory-header">
      <div>
        <h1 id="databases-title" class="directory-title">Databases</h1>
        <p class="directory-subtitle">Manage your connections and keep their schemas up to date.</p>
      </div>
      <RouterLink :to="{ name: 'catalog-new' }" class="directory-primary"><i class="pi pi-plus text-xs" aria-hidden="true"></i>Connect database</RouterLink>
    </header>

    <section class="directory-panel" aria-label="Database connections" :aria-busy="loading">
      <div class="directory-toolbar">
        <div class="directory-search">
          <i class="pi pi-search" aria-hidden="true"></i>
          <input v-model="q" type="search" placeholder="Search databases" aria-label="Search databases" />
        </div>
        <div class="flex flex-wrap items-center gap-4">
          <span v-if="!loading && !loadError" class="directory-count" role="status">{{ q.trim() ? `${filtered.length} of ${catalogs.length}` : catalogs.length }} {{ catalogs.length === 1 ? 'connection' : 'connections' }}</span>
          <button v-if="catalogs.length" type="button" class="directory-secondary" :disabled="loadingStatuses || loading" @click="fetchCatalogStatuses">
            <i class="pi pi-refresh text-xs" :class="{ 'pi-spin': loadingStatuses }" aria-hidden="true"></i>{{ loadingStatuses ? 'Checking...' : 'Refresh status' }}
          </button>
        </div>
      </div>

      <div v-if="loading" class="directory-empty" role="status"><i class="pi pi-spinner pi-spin mb-3 text-xl text-indigo-500" aria-hidden="true"></i>Loading databases...</div>
      <div v-else-if="loadError" class="directory-empty">
        <i class="pi pi-exclamation-circle mb-4 text-2xl text-amber-500" aria-hidden="true"></i>
        <h2 class="text-base font-semibold text-slate-900" role="alert">Unable to load databases</h2>
        <p class="mt-2">Please try loading your connections again.</p>
        <button type="button" class="directory-secondary mt-5" @click="fetchCatalogs">Try again</button>
      </div>
      <div v-else-if="!catalogs.length" class="directory-empty">
        <span class="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-indigo-50 text-indigo-500"><i class="pi pi-database text-2xl" aria-hidden="true"></i></span>
        <h2 class="text-base font-semibold text-slate-900">Connect your first database</h2>
        <p class="mt-2 max-w-sm leading-relaxed">Add a connection to make its schemas and tables available for access rules.</p>
        <RouterLink :to="{ name: 'catalog-new' }" class="directory-primary mt-5"><i class="pi pi-plus" aria-hidden="true"></i>Connect database</RouterLink>
      </div>
      <template v-else>
        <div v-if="statusError" role="alert" class="directory-error mx-5 mt-5 sm:mx-6">Connection checks are unavailable. Use Refresh status to try again.</div>
        <div v-if="!filtered.length" class="directory-empty">
          <i class="pi pi-search mb-4 text-2xl text-slate-300" aria-hidden="true"></i>
          <h2 class="text-base font-semibold text-slate-900">No matching databases</h2>
          <p class="mt-2">Try another name, database type or connection status.</p>
          <button type="button" class="directory-link mt-4" @click="q = ''">Clear search</button>
        </div>
        <ul v-else class="divide-y divide-slate-100">
          <li v-for="catalog in filtered" :key="catalog.id" class="grid items-start gap-5 p-5 sm:p-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.5fr)_auto]">
            <div class="flex min-w-0 items-start gap-3">
              <span class="directory-avatar"><i class="pi pi-database text-lg" aria-hidden="true"></i></span>
              <div class="min-w-0">
                <RouterLink :to="{ name: 'catalog', params: { id: catalog.id } }" class="directory-name">{{ catalog.name }}</RouterLink>
                <p class="mt-1 text-xs text-slate-500">{{ getTrinoDbmsLabel(catalog.sgbd) }}</p>
              </div>
            </div>
            <dl class="min-w-0 space-y-3">
              <div><dt class="text-xs text-slate-500">Connection URL</dt><dd class="mt-1 break-all font-mono text-xs leading-relaxed text-slate-700">{{ catalog.url }}</dd></div>
              <div class="flex flex-wrap items-baseline gap-x-2 gap-y-1"><dt class="text-xs text-slate-500">Username</dt><dd class="break-all text-sm text-slate-700">{{ catalog.username || 'Not set' }}</dd></div>
            </dl>
            <div class="flex flex-col items-start gap-4 lg:items-end">
              <ConnectionStatusBadge :status="statusByCatalogId[catalog.id]" :checking="loadingStatuses" />
              <div class="flex flex-wrap items-center gap-2">
                <RouterLink :to="{ name: 'catalog', params: { id: catalog.id } }" class="directory-secondary" :aria-label="`Edit connection ${catalog.name}`"><i class="pi pi-pencil text-xs" aria-hidden="true"></i>Edit</RouterLink>
                <button type="button" class="directory-secondary catalog-sync" :disabled="pending !== null" :aria-label="`Sync schema for ${catalog.name}`" @click="syncCatalogSchema(catalog.id)">
                  <i class="pi text-xs" :class="pending?.id === catalog.id && pending.action === 'sync' ? 'pi-spinner pi-spin' : 'pi-sync'" aria-hidden="true"></i>{{ pending?.id === catalog.id && pending.action === 'sync' ? 'Syncing...' : 'Sync schema' }}
                </button>
                <button type="button" class="directory-icon" :disabled="pending !== null" :aria-label="`More actions for ${catalog.name}`" aria-haspopup="menu" aria-controls="database-actions" :aria-expanded="menuCatalogId === catalog.id" v-tooltip.top="'More actions'" @click="openActions($event, catalog)">
                  <i class="pi" :class="pending?.id === catalog.id && pending.action !== 'sync' ? 'pi-spinner pi-spin' : 'pi-ellipsis-h'" aria-hidden="true"></i>
                </button>
              </div>
            </div>
          </li>
        </ul>
      </template>
    </section>
    <Menu ref="actionsMenu" id="database-actions" :model="menuItems" popup class="catalog-actions-menu" @hide="menuCatalogId = null" />
  </main>
</template>

<style>
.catalog-sync { @apply gap-1.5 px-2.5 text-[13px] sm:gap-2 sm:px-3 sm:text-sm; }
.catalog-actions-menu.p-menu { @apply w-56 max-w-[calc(100vw-1rem)] rounded-xl border border-slate-200 p-1 shadow-lg; }
.catalog-actions-menu .p-menuitem-link { @apply gap-2 px-3 py-2.5 text-sm; }
.catalog-actions-menu .p-menuitem-content { @apply rounded-lg; }
#database-actions .catalog-delete-action .p-menuitem-text,
#database-actions .catalog-delete-action .p-menuitem-icon { @apply text-red-600; }
</style>
