<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { useToast } from "primevue/usetoast";
import type { CatalogCreate } from "../types/catalog";
import { CatalogAPI } from "../types/catalog";
import CatalogForm from "../components/CatalogForm.vue";
import "../assets/directory.css";

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
    toast.add({ severity: "success", summary: "Created", detail: "Database connection added", life: 2000 });
    router.push({ name: "catalogs" });
  } catch (e) {
    console.error(e);
    toast.add({ severity: "error", summary: "Error", detail: "Unable to add database connection", life: 3000 });
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <div class="directory-form-page">
    <div class="directory-header">
      <h1 class="directory-title">Connect database</h1>
      <button type="button" class="directory-secondary shrink-0" @click="$router.back()"><i class="pi pi-angle-left" aria-hidden="true"></i>Back</button>
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
