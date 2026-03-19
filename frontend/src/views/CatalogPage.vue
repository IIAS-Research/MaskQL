<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useToast } from "primevue/usetoast";
import type { Catalog, CatalogUpdate } from "../types/catalog";
import { CatalogAPI } from "../types/catalog";
import CatalogForm from "../components/CatalogForm.vue";

const route = useRoute();
const router = useRouter();
const toast = useToast();

const id = Number(route.params.id);
const loading = ref(true);
const saving = ref(false);
const model = ref<Catalog | null>(null);

async function load() {
  try {
    const catalog = await CatalogAPI.getById(id);
    model.value = { ...catalog, password: "" } as Catalog;
  } catch (e) {
    console.error(e);
    toast.add({ severity: "error", summary: "Erreur", detail: "Enable to load database", life: 3000 });
    router.push({ name: "catalogs" });
    return;
  } finally {
    loading.value = false;
  }
}

async function handleSubmit(payload: Catalog | CatalogUpdate) {
  if (!("id" in payload) || payload.id == null) return;
  saving.value = true;
  try {
    const { id: payloadId, name, url, sgbd, username, password } = payload;
    const update: CatalogUpdate = { name, url, sgbd, username };
    if (password && password.trim() !== "") {
      update.password = password;
    }
    await CatalogAPI.update(Number(payloadId), update);
    toast.add({ severity: "success", summary: "Saved", detail: "Database updated", life: 2000 });
    router.push({ name: "catalogs" });
  } catch (e) {
    console.error(e);
    toast.add({ severity: "error", summary: "Error", detail: "Unable to update", life: 3000 });
  } finally {
    saving.value = false;
  }
}

onMounted(load);
</script>

<template>
  <div class="p-6 max-w-2xl mx-auto">
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-bold text-gray-800">Edit database</h1>
      <button class="px-3 py-2 rounded-lg border hover:bg-gray-50" @click="$router.back()">Back</button>
    </div>

    <div v-if="loading" class="text-gray-500">Loading...</div>

    <CatalogForm
      v-else-if="model"
      v-model="model"
      :saving="saving"
      mode="edit"
      @submit="handleSubmit"
      @cancel="$router.back()"
    />
  </div>
</template>

<style scoped></style>
