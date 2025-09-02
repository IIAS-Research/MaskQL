<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { useToast } from "primevue/usetoast";
import type { CatalogCreate } from "../types/catalog";
import { CatalogAPI } from "../types/catalog";
import CatalogForm from "../components/CatalogForm.vue";

const router = useRouter();
const toast = useToast();

const saving = ref(false);
const model = ref<CatalogCreate>({
  name: "",
  url: "",
  sgbd: "",
  username: "",
  password: ""
});

async function handleSubmit(payload: CatalogCreate) {
  saving.value = true;
  try {
    await CatalogAPI.create(payload);
    toast.add({ severity: "success", summary: "Créé", detail: "Le catalog a été ajouté.", life: 2000 });
    router.push({ name: "catalogs" });
  } catch (e) {
    console.error(e);
    toast.add({ severity: "error", summary: "Erreur", detail: "Création impossible.", life: 3000 });
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <div class="p-6 max-w-2xl mx-auto">
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-bold text-gray-800">New database connection</h1>
      <button class="px-3 py-2 rounded-lg border hover:bg-gray-50" @click="$router.back()">Back</button>
    </div>

    <CatalogForm
      v-model="model"
      :saving="saving"
      mode="create"
      @submit="handleSubmit"
      @cancel="$router.back()"
    />
  </div>
</template>

<style scoped></style>
