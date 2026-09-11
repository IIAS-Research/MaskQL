<script setup lang="ts">
import { ref, onMounted } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";
import { useToast } from "primevue/usetoast";
import type { Catalog, CatalogCreate, CatalogUpdate } from "../types/catalog";
import { CatalogAPI } from "../types/catalog";
import { getTrinoDbmsLabel } from "../constants/trinoDbms";
import CatalogForm from "../components/CatalogForm.vue";
import "../assets/directory.css";
import "../assets/settings.css";

const route = useRoute();
const router = useRouter();
const toast = useToast();
const id = Number(route.params.id);
const loading = ref(true);
const saving = ref(false);
const loadError = ref(false);
const saveError = ref("");
const model = ref<Catalog | null>(null);
const savedName = ref("");
const savedDbms = ref("");

async function load() {
  loading.value = true;
  loadError.value = false;
  try {
    const catalog = await CatalogAPI.getById(id);
    model.value = { ...catalog, password: "" };
    savedName.value = catalog.name;
    savedDbms.value = getTrinoDbmsLabel(catalog.sgbd);
  } catch {
    loadError.value = true;
  } finally {
    loading.value = false;
  }
}
async function handleSubmit(payload: CatalogCreate) {
  if (saving.value) return;
  saving.value = true;
  saveError.value = "";
  try {
    const { name, url, sgbd, username, password } = payload;
    const update: CatalogUpdate = { name, url, sgbd, username };
    if (password && password.trim() !== "") update.password = password;
    await CatalogAPI.update(id, update);
    toast.add({ severity: "success", summary: "Saved", detail: "Database connection updated", life: 2000 });
    router.push({ name: "catalogs" });
  } catch {
    saveError.value = "Changes were not saved. Please try again.";
  } finally {
    saving.value = false;
  }
}
onMounted(load);
</script>

<template>
  <main class="settings-page" aria-labelledby="connection-title">
    <nav class="settings-breadcrumb" aria-label="Breadcrumb">
      <RouterLink :to="{ name: 'catalogs' }">Databases</RouterLink><i class="pi pi-angle-right text-[10px]" aria-hidden="true"></i><span aria-current="page">Edit connection</span>
    </nav>
    <header class="settings-header">
      <div class="settings-identity">
        <span class="settings-avatar settings-avatar-accent" aria-hidden="true"><i class="pi pi-database text-2xl"></i></span>
        <div class="min-w-0">
          <h1 id="connection-title" class="directory-title break-all">{{ savedName || 'Edit connection' }}</h1>
          <p class="directory-subtitle">{{ savedDbms ? `${savedDbms} connection` : 'Database connection settings' }}</p>
        </div>
      </div>
    </header>
    <div v-if="loading" class="directory-panel directory-empty" role="status"><i class="pi pi-spinner pi-spin mb-3 text-xl text-brand-500" aria-hidden="true"></i>Loading connection...</div>
    <div v-else-if="loadError" class="directory-panel directory-empty">
      <i class="pi pi-exclamation-circle mb-3 text-2xl text-amber-500" aria-hidden="true"></i>
      <p class="font-medium text-slate-900" role="alert">Unable to load this connection.</p>
      <button type="button" class="directory-secondary mt-4" @click="load">Retry</button>
    </div>
    <CatalogForm v-else-if="model" v-model="model" :saving="saving" :error="saveError" mode="edit" @submit="handleSubmit" @cancel="router.back()" />
  </main>
</template>
