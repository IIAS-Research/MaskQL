<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { RouterLink } from "vue-router";
import { UserAPI, type User } from "../types/user";
import { CatalogAPI, type Catalog, type CatalogConnectionStatus } from "../types/catalog";
import { RuleAPI, type Rule } from "../types/rule";
import { getTrinoDbmsLabel } from "../constants/trinoDbms";
import ManageAccessLink from "../components/ManageAccessLink.vue";
import ConnectionStatusBadge from "../components/ConnectionStatusBadge.vue";
import "../assets/directory.css";

const users = ref<User[] | null>(null);
const catalogs = ref<Catalog[] | null>(null);
const rules = ref<Rule[] | null>(null);
const statuses = ref<Record<number, CatalogConnectionStatus>>({});
const loading = ref(false);
const checking = ref(false);
const loadError = ref("");
const statusError = ref(false);
const checkedAt = ref("");
const search = ref("");

const userRules = computed(() => {
  const summary = new Map<number, { count: number; catalogs: Set<number> }>();
  for (const rule of rules.value ?? []) {
    const entry = summary.get(rule.user_id) ?? { count: 0, catalogs: new Set<number>() };
    entry.count += 1;
    entry.catalogs.add(rule.catalog_id);
    summary.set(rule.user_id, entry);
  }
  return summary;
});
const configuredUsers = computed(() => users.value?.filter(user => userRules.value.has(user.id)).length ?? 0);
const matchingUsers = computed(() => {
  const term = search.value.trim().toLowerCase();
  return (users.value ?? []).filter(user => user.username.toLowerCase().includes(term));
});
const visibleCatalogs = computed(() => [...(catalogs.value ?? [])].sort((a, b) => {
  const aFailed = statuses.value[a.id]?.state === "error" ? 1 : 0;
  const bFailed = statuses.value[b.id]?.state === "error" ? 1 : 0;
  return bFailed - aFailed || a.name.localeCompare(b.name);
}).slice(0, 4));
const failedConnections = computed(() => (catalogs.value ?? []).filter(catalog => statuses.value[catalog.id]?.state === "error").length);
const ruleKinds = computed(() => {
  let filters = 0;
  let transformations = 0;
  for (const rule of rules.value ?? []) {
    if (!rule.effect?.trim()) continue;
    if (rule.column_name && rule.allow) transformations += 1;
    else if (rule.table_name && !rule.column_name) filters += 1;
  }
  return [
    { label: "Access only", count: (rules.value?.length ?? 0) - filters - transformations, color: "bg-slate-400" },
    { label: "Row filters", count: filters, color: "bg-sky-500" },
    { label: "Column transformations", count: transformations, color: "bg-indigo-500" },
  ];
});

async function loadOverview() {
  loading.value = true;
  loadError.value = "";
  users.value = null;
  catalogs.value = null;
  rules.value = null;
  const [userResult, catalogResult, ruleResult] = await Promise.allSettled([
    UserAPI.list(), CatalogAPI.list(), RuleAPI.list(),
  ]);
  users.value = userResult.status === "fulfilled" ? userResult.value : null;
  catalogs.value = catalogResult.status === "fulfilled" ? catalogResult.value : null;
  rules.value = ruleResult.status === "fulfilled" ? ruleResult.value : null;
  loadError.value = [
    userResult.status === "rejected" ? "users" : "",
    catalogResult.status === "rejected" ? "databases" : "",
    ruleResult.status === "rejected" ? "rules" : "",
  ].filter(Boolean).join(", ");
  loading.value = false;
}
async function checkConnections() {
  checking.value = true;
  statusError.value = false;
  statuses.value = {};
  checkedAt.value = "";
  try {
    const result = await CatalogAPI.listStatuses();
    statuses.value = Object.fromEntries(result.map(status => [status.catalog_id, status]));
    checkedAt.value = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  } catch {
    statusError.value = true;
  } finally {
    checking.value = false;
  }
}
function refresh() {
  if (loading.value || checking.value) return;
  void loadOverview();
  void checkConnections();
}
function ruleSummary(userId: number) {
  if (loading.value) return "Loading rule counts...";
  if (rules.value === null) return "Rule counts unavailable";
  const entry = userRules.value.get(userId);
  if (!entry) return "No rules configured";
  return `${entry.count} saved ${entry.count === 1 ? "rule" : "rules"} across ${entry.catalogs.size} ${entry.catalogs.size === 1 ? "database" : "databases"}`;
}
onMounted(refresh);
</script>

<template>
  <main class="mx-auto max-w-6xl px-5 pb-12 pt-8 sm:px-8 sm:pt-10" aria-labelledby="home-title">
    <header class="flex flex-wrap items-center justify-between gap-4">
      <div>
        <h1 id="home-title" class="directory-title">Overview</h1>
        <p class="directory-subtitle">Your users, database connections and configured rules.</p>
      </div>
      <div class="flex flex-wrap items-center gap-3">
        <button type="button" class="directory-secondary" :disabled="loading || checking" @click="refresh"><i class="pi pi-refresh text-xs" :class="{ 'pi-spin': loading || checking }" aria-hidden="true"></i>Refresh</button>
        <RouterLink :to="{ name: 'users' }" class="directory-primary"><i class="pi pi-users" aria-hidden="true"></i>View users</RouterLink>
      </div>
    </header>

    <p v-if="loadError" role="alert" class="mt-5 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
      Unable to load {{ loadError }}. Use Refresh to try again.
    </p>

    <dl class="mt-6 grid grid-cols-3 divide-x divide-slate-200 rounded-2xl border border-slate-200 bg-white" :aria-busy="loading">
      <div class="min-w-0 px-2 py-3 sm:p-5">
        <dt class="text-[11px] font-medium text-slate-500 sm:text-sm">Users</dt>
        <dd class="mt-2 break-words font-semibold tabular-nums text-slate-900" :class="users === null ? 'text-xs sm:text-sm' : 'text-2xl sm:text-3xl'">{{ loading ? 'Loading...' : users?.length ?? 'Unavailable' }}</dd>
        <dd v-if="users !== null && rules !== null" class="mt-2 hidden text-xs text-slate-500 sm:block">{{ configuredUsers }} with saved rules</dd>
      </div>
      <div class="min-w-0 px-2 py-3 sm:p-5">
        <dt class="text-[11px] font-medium text-slate-500 sm:text-sm">Databases</dt>
        <dd class="mt-2 break-words font-semibold tabular-nums text-slate-900" :class="catalogs === null ? 'text-xs sm:text-sm' : 'text-2xl sm:text-3xl'">{{ loading ? 'Loading...' : catalogs?.length ?? 'Unavailable' }}</dd>
        <dd v-if="catalogs !== null" class="mt-2 hidden text-xs text-slate-500 sm:block">Configured connections</dd>
      </div>
      <div class="min-w-0 px-2 py-3 sm:p-5">
        <dt class="text-[11px] font-medium text-slate-500 sm:text-sm">Rules</dt>
        <dd class="mt-2 break-words font-semibold tabular-nums text-slate-900" :class="rules === null ? 'text-xs sm:text-sm' : 'text-2xl sm:text-3xl'">{{ loading ? 'Loading...' : rules?.length ?? 'Unavailable' }}</dd>
        <dd v-if="rules !== null" class="mt-2 hidden text-xs text-slate-500 sm:block">Saved across all users</dd>
      </div>
    </dl>

    <div class="mt-6 grid items-start gap-6 lg:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)]">
      <section class="min-w-0 rounded-2xl border border-slate-200 bg-white" aria-labelledby="users-title" :aria-busy="loading">
        <div class="p-5 sm:p-6">
          <div class="flex flex-wrap items-center justify-between gap-2">
            <h2 id="users-title" class="text-lg font-semibold text-slate-900">User access</h2>
            <RouterLink :to="{ name: 'user-new' }" class="directory-text-button"><i class="pi pi-plus text-xs" aria-hidden="true"></i>Create user</RouterLink>
          </div>
          <p class="mt-1 text-xs text-slate-500">Rules are configured separately for each user.</p>
          <div v-if="users?.length" class="directory-search mt-4 sm:max-w-none">
            <i class="pi pi-search" aria-hidden="true"></i>
            <input v-model="search" type="search" aria-label="Search users" placeholder="Search users" />
          </div>
        </div>
        <p v-if="loading" role="status" class="px-5 pb-6 text-sm text-slate-500 sm:px-6">Loading users...</p>
        <p v-else-if="users === null" class="px-5 pb-6 text-sm text-slate-500 sm:px-6">User list unavailable.</p>
        <div v-else-if="!users.length" class="px-5 pb-6 sm:px-6">
          <p class="text-sm text-slate-600">No users yet. Create one to start configuring access.</p>
          <RouterLink :to="{ name: 'user-new' }" class="directory-primary mt-4"><i class="pi pi-plus" aria-hidden="true"></i>Create user</RouterLink>
        </div>
        <p v-else-if="!matchingUsers.length" class="px-5 pb-6 text-sm text-slate-500 sm:px-6">No users match your search.</p>
        <ul v-else class="divide-y divide-slate-100 border-t border-slate-100">
          <li v-for="user in matchingUsers.slice(0, 5)" :key="user.id" class="flex flex-col items-start justify-between gap-x-4 gap-y-2 px-5 py-4 sm:flex-row sm:items-center sm:px-6">
            <div class="flex min-w-0 items-center gap-3 sm:flex-1">
              <span class="directory-avatar" aria-hidden="true">{{ user.username.slice(0, 2).toUpperCase() }}</span>
              <div class="min-w-0">
                <RouterLink :to="{ name: 'user-rules', params: { id: user.id } }" class="directory-name">{{ user.username }}</RouterLink>
                <p class="mt-1 text-xs leading-relaxed text-slate-500">{{ ruleSummary(user.id) }}</p>
              </div>
            </div>
            <ManageAccessLink :user-id="user.id" :username="user.username" class="shrink-0" />
          </li>
        </ul>
        <div v-if="users?.length" class="flex flex-wrap items-center justify-between gap-2 border-t border-slate-100 px-5 py-3 sm:px-6">
          <span class="text-xs text-slate-500">Showing {{ Math.min(matchingUsers.length, 5) }} of {{ matchingUsers.length }}</span>
          <RouterLink :to="{ name: 'users' }" class="directory-link">View all users</RouterLink>
        </div>
      </section>

      <div class="min-w-0 space-y-6">
        <section class="rounded-2xl border border-slate-200 bg-white p-5 sm:p-6" aria-labelledby="databases-title">
          <div class="flex flex-wrap items-center justify-between gap-2">
            <h2 id="databases-title" class="text-lg font-semibold text-slate-900">Database connections</h2>
            <RouterLink :to="{ name: 'catalog-new' }" class="directory-text-button"><i class="pi pi-plus text-xs" aria-hidden="true"></i>Connect database</RouterLink>
          </div>
          <p class="mt-1 text-xs text-slate-500" aria-live="polite">{{ checking ? 'Checking connections...' : statusError ? 'Connection checks unavailable.' : checkedAt ? `Connections checked at ${checkedAt}` : 'Connection status unknown.' }}</p>
          <p v-if="loading" role="status" class="mt-4 text-sm text-slate-500">Loading databases...</p>
          <p v-else-if="catalogs === null" class="mt-4 text-sm text-slate-500">Database list unavailable.</p>
          <div v-else-if="!catalogs.length" class="mt-4">
            <p class="text-sm text-slate-600">No databases connected yet.</p>
            <RouterLink :to="{ name: 'catalog-new' }" class="directory-primary mt-4"><i class="pi pi-plus" aria-hidden="true"></i>Connect database</RouterLink>
          </div>
          <ul v-else class="mt-3 divide-y divide-slate-100">
            <li v-for="catalog in visibleCatalogs" :key="catalog.id" class="flex items-center justify-between gap-3 py-3">
              <div class="min-w-0">
                <RouterLink :to="{ name: 'catalog', params: { id: catalog.id } }" class="directory-name">{{ catalog.name }}</RouterLink>
                <p class="mt-1 text-xs text-slate-500">{{ getTrinoDbmsLabel(catalog.sgbd) }}</p>
              </div>
              <ConnectionStatusBadge :status="statuses[catalog.id]" :checking="checking" />
            </li>
          </ul>
          <div v-if="catalogs?.length" class="mt-2 flex flex-wrap items-center justify-between gap-2 border-t border-slate-100 pt-3">
            <span v-if="failedConnections" class="text-xs text-red-700">{{ failedConnections }} failed {{ failedConnections === 1 ? 'connection' : 'connections' }}</span>
            <span v-else class="text-xs text-slate-500">Showing {{ visibleCatalogs.length }} of {{ catalogs.length }}</span>
            <RouterLink :to="{ name: 'catalogs' }" class="directory-link">View all databases</RouterLink>
          </div>
        </section>

        <section class="rounded-2xl border border-slate-200 bg-white p-5 sm:p-6" aria-labelledby="rules-title" :aria-busy="loading">
          <h2 id="rules-title" class="text-lg font-semibold text-slate-900">Rule breakdown</h2>
          <p class="mt-1 text-xs text-slate-500">Configured rules, counted per user and path.</p>
          <p v-if="loading" role="status" class="mt-4 text-sm text-slate-500">Loading rules...</p>
          <p v-else-if="rules === null" class="mt-4 text-sm text-slate-500">Rule counts unavailable.</p>
          <dl v-else class="mt-4 space-y-3">
            <div v-for="kind in ruleKinds" :key="kind.label" class="grid grid-cols-[1fr_auto] gap-x-3 text-sm">
              <dt class="text-slate-600">{{ kind.label }}</dt><dd class="font-semibold tabular-nums text-slate-900">{{ kind.count }}</dd>
              <div class="col-span-2 mt-1.5 h-1.5 overflow-hidden rounded-full bg-slate-100" aria-hidden="true"><div class="h-full rounded-full" :class="kind.color" :style="{ width: `${rules.length ? kind.count / rules.length * 100 : 0}%` }"></div></div>
            </div>
          </dl>
        </section>
      </div>
    </div>

    <details class="mt-6 rounded-xl border border-slate-200 bg-white p-5 sm:p-6">
      <summary class="cursor-pointer text-sm font-semibold text-slate-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-indigo-600">How to configure access<span class="ml-2 inline-block text-xs font-normal text-slate-500">A quick guide</span></summary>
      <ol class="mt-4 grid gap-4 text-sm md:grid-cols-3">
        <li><h3 class="font-semibold text-slate-900">1. Choose a user</h3><p class="mt-1 leading-relaxed text-slate-600">Select Manage access next to a user to edit their rules.</p></li>
        <li><h3 class="font-semibold text-slate-900">2. Choose the data</h3><p class="mt-1 leading-relaxed text-slate-600">Select a database and schema, then open a table using its gear icon.</p></li>
        <li><h3 class="font-semibold text-slate-900">3. Set rules and preview</h3><p class="mt-1 leading-relaxed text-slate-600">Allow access, filter rows or transform columns. Compare the before and after preview.</p></li>
      </ol>
    </details>
    <footer class="mt-8 flex justify-end"><img src="/images/IIAS_MINIATURE.png" alt="IIAS" class="h-10 max-w-full object-contain opacity-80" /></footer>
  </main>
</template>
