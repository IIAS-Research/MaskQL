<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { RouterLink } from "vue-router";
import { useToast } from "primevue/usetoast";
import { UserAPI, type User } from "../types/user";
import { RuleAPI, type Rule } from "../types/rule";
import ManageAccessLink from "../components/ManageAccessLink.vue";
import { useDeleteConfirmation } from "../composables/useDeleteConfirmation";
import "../assets/directory.css";

const toast = useToast();
const confirmDelete = useDeleteConfirmation();
const users = ref<User[] | null>(null);
const rules = ref<Rule[] | null>(null);
const loading = ref(true);
const loadingRules = ref(true);
const deleting = ref<number | null>(null);
const deleteError = ref("");
const q = ref("");

const filtered = computed(() => {
  const term = q.value.trim().toLowerCase();
  return (users.value ?? []).filter(user => user.username.toLowerCase().includes(term));
});
const userRules = computed(() => {
  const summaries = new Map<number, { count: number; catalogs: Set<number> }>();
  for (const rule of rules.value ?? []) {
    const summary = summaries.get(rule.user_id) ?? { count: 0, catalogs: new Set<number>() };
    summary.count += 1;
    summary.catalogs.add(rule.catalog_id);
    summaries.set(rule.user_id, summary);
  }
  return summaries;
});

function initials(username: string) {
  return username.slice(0, 2).toUpperCase();
}
function ruleSummary(userId: number) {
  if (loadingRules.value) return "Loading rule counts...";
  if (rules.value === null) return "Rule counts unavailable";
  const summary = userRules.value.get(userId);
  if (!summary) return "No rules configured";
  return `${summary.count} saved ${summary.count === 1 ? "rule" : "rules"} across ${summary.catalogs.size} ${summary.catalogs.size === 1 ? "database" : "databases"}`;
}
async function fetchUsers() {
  loading.value = true;
  try {
    users.value = await UserAPI.list();
  } catch {
    users.value = null;
  } finally {
    loading.value = false;
  }
}
async function fetchRules() {
  loadingRules.value = true;
  try {
    rules.value = await RuleAPI.list();
  } catch {
    rules.value = null;
  } finally {
    loadingRules.value = false;
  }
}
function confirmRemoveUser(user: User, event: MouseEvent) {
  if (deleting.value !== null) return;
  confirmDelete({
    header: "Delete user?",
    message: `The user "${user.username}" and their rules will be permanently deleted.`,
    acceptLabel: "Delete user",
    target: event.currentTarget as HTMLElement,
    accept: () => removeUser(user),
  });
}
async function removeUser(user: User) {
  if (deleting.value !== null) return;
  deleting.value = user.id;
  deleteError.value = "";
  try {
    await UserAPI.remove(user.id);
    users.value = (users.value ?? []).filter(item => item.id !== user.id);
    toast.add({ severity: "success", summary: "User deleted", detail: user.username, life: 2000 });
  } catch {
    deleteError.value = `Unable to delete ${user.username}. Please try again.`;
  } finally {
    deleting.value = null;
  }
}
onMounted(() => {
  void fetchUsers();
  void fetchRules();
});
</script>

<template>
  <main class="directory-page" aria-labelledby="users-title">
    <header class="directory-header">
      <div>
        <h1 id="users-title" class="directory-title">Users</h1>
        <p class="directory-subtitle">Manage accounts and configure access for each user.</p>
      </div>
      <RouterLink :to="{ name: 'user-new' }" class="directory-primary">
        <i class="pi pi-plus" aria-hidden="true"></i>Create user
      </RouterLink>
    </header>

    <p v-if="deleteError" class="directory-error mb-5" role="alert">{{ deleteError }}</p>

    <section class="directory-panel" aria-label="User directory" :aria-busy="loading">
      <div class="directory-toolbar">
        <div class="directory-search">
          <i class="pi pi-search" aria-hidden="true"></i>
          <input v-model="q" type="search" placeholder="Search users" aria-label="Search users" />
        </div>
        <span class="directory-count" aria-live="polite">
          <template v-if="loading">Loading users...</template>
          <template v-else-if="users === null">User count unavailable</template>
          <template v-else-if="q.trim()">{{ filtered.length }} of {{ users.length }} users</template>
          <template v-else>{{ users.length }} {{ users.length === 1 ? 'user' : 'users' }}</template>
        </span>
      </div>

      <div v-if="users?.length && !loadingRules && rules === null" class="directory-error mx-4 mt-4 flex flex-wrap items-center justify-between gap-2 sm:mx-6" role="alert">
        <span>Unable to load rule counts.</span>
        <button type="button" class="directory-link" @click="fetchRules">Retry rule counts</button>
      </div>

      <div v-if="loading" class="directory-empty" role="status">
        <i class="pi pi-spinner pi-spin mb-3 text-xl text-brand-500" aria-hidden="true"></i>
        <p class="text-sm text-slate-500">Loading users...</p>
      </div>
      <div v-else-if="users === null" class="directory-empty" role="alert">
        <i class="pi pi-exclamation-circle mb-3 text-2xl text-amber-600" aria-hidden="true"></i>
        <h2 class="font-semibold text-slate-900">Unable to load users</h2>
        <p class="mt-2 text-sm text-slate-500">Try again to see your accounts.</p>
        <button type="button" class="directory-secondary mt-5" @click="fetchUsers">Retry</button>
      </div>
      <div v-else-if="!users.length" class="directory-empty">
        <div class="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-brand-50 text-brand-600"><i class="pi pi-users text-xl" aria-hidden="true"></i></div>
        <h2 class="font-semibold text-slate-900">Your first user starts here</h2>
        <p class="mx-auto mt-2 max-w-sm text-sm leading-relaxed text-slate-500">Create an account, then choose which data they can access.</p>
        <RouterLink :to="{ name: 'user-new' }" class="directory-primary mt-5"><i class="pi pi-plus" aria-hidden="true"></i>Create user</RouterLink>
      </div>
      <div v-else-if="!filtered.length" class="directory-empty">
        <i class="pi pi-search mb-3 text-2xl text-slate-400" aria-hidden="true"></i>
        <h2 class="font-semibold text-slate-900">No matching users</h2>
        <p class="mt-2 text-sm text-slate-500">Try another name or clear your search.</p>
        <button type="button" class="directory-secondary mt-5" @click="q = ''">Clear search</button>
      </div>
      <ul v-else class="divide-y divide-slate-100">
        <li v-for="user in filtered" :key="user.id" class="flex flex-col justify-between gap-4 px-4 py-5 transition-colors last:rounded-b-2xl hover:bg-slate-50/70 sm:flex-row sm:items-center sm:px-6">
          <div class="flex min-w-0 items-center gap-3">
            <span class="directory-avatar shrink-0" aria-hidden="true">{{ initials(user.username) }}</span>
            <div class="min-w-0">
              <RouterLink :to="{ name: 'user-rules', params: { id: user.id } }" class="directory-name">{{ user.username }}</RouterLink>
              <p class="mt-1 text-xs leading-relaxed text-slate-500">{{ ruleSummary(user.id) }}</p>
            </div>
          </div>
          <div class="flex flex-wrap items-center gap-2 sm:shrink-0">
            <ManageAccessLink :user-id="user.id" :username="user.username" />
            <div class="ml-auto flex items-center gap-1 sm:ml-1">
              <RouterLink :to="{ name: 'user', params: { id: user.id } }" class="directory-icon" :aria-label="`Edit ${user.username}`" :title="`Edit ${user.username}`"><i class="pi pi-pencil" aria-hidden="true"></i></RouterLink>
              <button type="button" class="directory-icon user-delete-button" :disabled="deleting !== null" :aria-label="deleting === user.id ? `Deleting ${user.username}` : `Delete ${user.username}`" :title="`Delete ${user.username}`" @click="confirmRemoveUser(user, $event)"><i :class="deleting === user.id ? 'pi pi-spinner pi-spin' : 'pi pi-trash'" aria-hidden="true"></i></button>
            </div>
          </div>
        </li>
      </ul>
    </section>
  </main>
</template>

<style scoped>
.user-delete-button { @apply hover:bg-red-50 hover:text-red-600 disabled:cursor-wait disabled:opacity-50; }
</style>
