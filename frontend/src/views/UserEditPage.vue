<script setup lang="ts">
import { ref, onMounted } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";
import { useToast } from "primevue/usetoast";
import type { UserCreate, UserUpdate } from "../types/user";
import { UserAPI } from "../types/user";
import UserForm from "../components/UserForm.vue";
import ManageAccessLink from "../components/ManageAccessLink.vue";
import "../assets/directory.css";
import "../assets/settings.css";

const route = useRoute();
const router = useRouter();
const toast = useToast();

const id = Number(route.params.id);
const loading = ref(true);
const saving = ref(false);
const username = ref("");
const model = ref<UserCreate | null>(null);
const loadError = ref("");
const saveError = ref("");

async function load() {
  loading.value = true;
  loadError.value = "";
  try {
    const user = await UserAPI.getById(id);
    username.value = user.username;
    model.value = { username: user.username, password: "" };
  } catch {
    loadError.value = "Unable to load this user. Please try again.";
  } finally {
    loading.value = false;
  }
}

async function handleSubmit(payload: UserCreate) {
  if (saving.value) return;
  saving.value = true;
  saveError.value = "";
  try {
    const update: UserUpdate = { username: payload.username };
    if (payload.password.trim() !== "") update.password = payload.password;
    await UserAPI.update(id, update);
    toast.add({ severity: "success", summary: "Saved", detail: "User updated", life: 2000 });
    router.push({ name: "users" });
  } catch {
    saveError.value = "Changes were not saved. Please try again.";
  } finally {
    saving.value = false;
  }
}

onMounted(load);
</script>

<template>
  <main class="settings-page" aria-labelledby="user-title">
    <nav class="settings-breadcrumb" aria-label="Breadcrumb">
      <RouterLink :to="{ name: 'users' }">Users</RouterLink>
      <i class="pi pi-angle-right text-[10px]" aria-hidden="true"></i>
      <span aria-current="page">Edit user</span>
    </nav>

    <header class="settings-header">
      <div class="settings-identity">
        <span class="settings-avatar" aria-hidden="true">
          <template v-if="username">{{ username.slice(0, 2).toUpperCase() }}</template>
          <i v-else class="pi pi-user"></i>
        </span>
        <div class="min-w-0">
          <h1 id="user-title" class="directory-title break-words">{{ username || 'Edit user' }}</h1>
          <p class="directory-subtitle">Manage this user’s sign-in details.</p>
        </div>
      </div>
      <ManageAccessLink v-if="model" :user-id="id" :username="username" />
    </header>

    <div v-if="loading" class="directory-panel directory-empty" role="status"><i class="pi pi-spinner pi-spin mb-3 text-xl text-brand-500" aria-hidden="true"></i>Loading user...</div>
    <div v-else-if="loadError" class="directory-panel directory-empty">
      <i class="pi pi-exclamation-circle mb-3 text-2xl text-amber-500" aria-hidden="true"></i>
      <p class="font-medium text-slate-900" role="alert">{{ loadError }}</p>
      <button type="button" class="directory-secondary mt-4" @click="load">Retry</button>
    </div>
    <UserForm
      v-else-if="model"
      v-model="model"
      :saving="saving"
      :error="saveError"
      mode="edit"
      @submit="handleSubmit"
      @cancel="router.back()"
    />
  </main>
</template>
