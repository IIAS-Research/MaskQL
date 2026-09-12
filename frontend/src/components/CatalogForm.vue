<script setup lang="ts">
import { ref, watch, computed } from "vue";
import Dropdown from "primevue/dropdown";
import type { Catalog, CatalogCreate } from "../types/catalog";
import { TRINO_DBMS_OPTIONS, getTrinoDbmsJdbcExample, isKnownTrinoDbms } from "../constants/trinoDbms";
import "../assets/directory.css";
import "../assets/settings.css";

type Mode = "create" | "edit";
const props = withDefaults(defineProps<{
  modelValue: CatalogCreate | Catalog;
  saving?: boolean;
  mode?: Mode;
  error?: string;
}>(), { saving: false, mode: "create", error: "" });
const emit = defineEmits<{
  (e: "update:modelValue", value: CatalogCreate | Catalog): void;
  (e: "submit", value: CatalogCreate | Catalog): void;
  (e: "cancel"): void;
}>();

const local = ref<CatalogCreate | Catalog>(props.modelValue);
let syncingFromParent = false;
watch(() => props.modelValue, value => {
  syncingFromParent = true;
  local.value = value;
  queueMicrotask(() => (syncingFromParent = false));
});
watch(local, value => {
  if (!syncingFromParent) emit("update:modelValue", value);
}, { deep: true });

const showPwd = ref(false);
const errors = ref<{ name?: string; url?: string; sgbd?: string }>({});
function onSubmit() {
  if (props.saving) return;
  const next: typeof errors.value = {};
  if (!local.value.name) next.name = "Name required";
  if (!local.value.url) next.url = "JDBC URL required";
  if (!local.value.sgbd) next.sgbd = "Database type required";
  errors.value = next;
  if (!Object.keys(next).length) emit("submit", { ...local.value });
}
const nameModel = computed({
  get: () => local.value.name,
  set: (value: string) => { local.value.name = value.toLowerCase().replace(/\s+/g, "").replace(/[^a-z]/g, ""); },
});
const sgbdOptions = computed(() => {
  const current = local.value.sgbd?.trim();
  if (!current || isKnownTrinoDbms(current)) return TRINO_DBMS_OPTIONS;
  return [{ value: current, label: `${current} (existing value)`, jdbcExample: getTrinoDbmsJdbcExample(current) }, ...TRINO_DBMS_OPTIONS];
});
const jdbcExample = computed(() => getTrinoDbmsJdbcExample(local.value.sgbd));
</script>

<template>
  <form class="directory-panel settings-form" :aria-busy="saving" @submit.prevent="onSubmit">
    <section class="settings-section" aria-labelledby="connection-details-title">
      <div class="settings-section-heading">
        <h2 id="connection-details-title"><i class="pi pi-database" aria-hidden="true"></i>Connection details</h2>
        <p class="settings-hint">Name this connection and choose the type of database.</p>
      </div>
      <div class="grid min-w-0 gap-5 lg:grid-cols-2">
        <div class="min-w-0">
          <label for="catalog-name" class="settings-label">Name</label>
          <input id="catalog-name" v-model="nameModel" type="text" class="settings-input" autocomplete="off" spellcheck="false" :disabled="saving" :aria-invalid="!!errors.name" :aria-describedby="errors.name ? 'catalog-name-help catalog-name-error' : 'catalog-name-help'" />
          <p id="catalog-name-help" class="settings-hint">Lowercase letters only. Used as the catalog name in SQL.</p>
          <p v-if="errors.name" id="catalog-name-error" class="settings-field-error" role="alert">{{ errors.name }}</p>
        </div>
        <div class="min-w-0">
          <label for="catalog-dbms" class="settings-label">Database type</label>
          <Dropdown input-id="catalog-dbms" v-model="local.sgbd" :options="sgbdOptions" option-label="label" option-value="value" placeholder="Select a database type" filter filter-placeholder="Search database types" :filter-input-props="{ 'aria-label': 'Search database types' }" reset-filter-on-hide :disabled="saving" :input-props="{ 'aria-invalid': !!errors.sgbd, 'aria-describedby': errors.sgbd ? 'catalog-dbms-error' : undefined }" class="settings-select" :class="{ 'p-invalid': errors.sgbd }" panel-class="settings-select-panel" scroll-height="14rem" />
          <p v-if="errors.sgbd" id="catalog-dbms-error" class="settings-field-error" role="alert">{{ errors.sgbd }}</p>
        </div>
      </div>
    </section>

    <section class="settings-section" aria-labelledby="connection-address-title">
      <div class="settings-section-heading">
        <h2 id="connection-address-title"><i class="pi pi-link" aria-hidden="true"></i>Connection address</h2>
        <p class="settings-hint">Where MaskQL connects to your database.</p>
      </div>
      <div class="min-w-0">
        <label for="catalog-url" class="settings-label">JDBC URL</label>
        <input id="catalog-url" v-model="local.url" type="text" :placeholder="jdbcExample" class="settings-input font-mono" autocomplete="off" spellcheck="false" :disabled="saving" :aria-invalid="!!errors.url" :aria-describedby="errors.url ? 'catalog-url-help catalog-url-error' : 'catalog-url-help'" />
        <p id="catalog-url-help" class="settings-hint break-words">Example: <code class="break-all">{{ jdbcExample }}</code></p>
        <p v-if="errors.url" id="catalog-url-error" class="settings-field-error" role="alert">{{ errors.url }}</p>
      </div>
    </section>

    <section class="settings-section" aria-labelledby="connection-credentials-title">
      <div class="settings-section-heading">
        <h2 id="connection-credentials-title"><i class="pi pi-key" aria-hidden="true"></i>Database credentials</h2>
        <p class="settings-hint">The account MaskQL uses to connect to this database.</p>
      </div>
      <div class="min-w-0 space-y-5">
        <div>
          <label for="catalog-username" class="settings-label">Username</label>
          <input id="catalog-username" v-model="local.username" type="text" class="settings-input" autocomplete="off" :disabled="saving" />
        </div>
        <div>
          <label for="catalog-password" class="settings-label">{{ mode === 'edit' ? 'New password' : 'Password' }}<span v-if="mode === 'edit'" class="ml-2 text-xs font-normal text-slate-400">Optional</span></label>
          <div class="settings-password">
            <input id="catalog-password" v-model="local.password" :type="showPwd ? 'text' : 'password'" class="settings-input" autocomplete="new-password" :disabled="saving" :aria-describedby="mode === 'edit' ? 'catalog-password-help' : undefined" />
            <button type="button" class="settings-password-toggle" :aria-label="showPwd ? 'Hide password' : 'Show password'" :aria-pressed="showPwd" :disabled="saving" @click="showPwd = !showPwd"><i class="pi" :class="showPwd ? 'pi-eye-slash' : 'pi-eye'" aria-hidden="true"></i></button>
          </div>
          <p v-if="mode === 'edit'" id="catalog-password-help" class="settings-hint">Leave blank to keep the current password.</p>
        </div>
      </div>
    </section>

    <p v-if="error" class="settings-error" role="alert">{{ error }}</p>
    <footer class="settings-footer">
      <button type="button" class="directory-secondary" :disabled="saving" @click="emit('cancel')">Cancel</button>
      <button type="submit" class="directory-primary" :disabled="saving"><i class="pi" :class="saving ? 'pi-spinner pi-spin' : 'pi-check'" aria-hidden="true"></i>{{ saving ? 'Saving...' : mode === 'edit' ? 'Save changes' : 'Connect database' }}</button>
    </footer>
  </form>
</template>
