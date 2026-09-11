<script setup lang="ts">
import { computed, nextTick, onUnmounted, ref } from "vue";
import Dialog from "primevue/dialog";
import { compatibleFunctions } from "../utils/ruleFunctions";

const props = defineProps<{ columnType: string | null; column?: string; selectedId?: string }>();
const emit = defineEmits<{ (event: "choose", id: string): void; (event: "close"): void; (event: "sql"): void }>();
const search = ref("");
const searchInput = ref<HTMLInputElement | null>(null);
function focusSearch() { nextTick(() => searchInput.value?.focus()); }
onUnmounted(() => {
  // PrimeVue clears the body scroll lock even when another modal remains open.
  if (document.querySelector('.p-dialog-mask.p-component-overlay')) document.body.classList.add('p-overflow-hidden');
});
const group = ref("");
const categoryOrder = ["MaskQL", "General", "Text", "Numbers", "Dates", "Booleans"];
const functions = computed(() => compatibleFunctions(props.columnType)
  .sort((a, b) => categoryOrder.indexOf(a.group) - categoryOrder.indexOf(b.group)));
const groups = computed(() => [...new Set(functions.value.map(fn => fn.group))]);
const matches = computed(() => functions.value.filter(fn =>
  (!group.value || fn.group === group.value) &&
  `${fn.label} ${fn.id} ${fn.description}`.toLowerCase().includes(search.value.trim().toLowerCase()),
));
const sections = computed(() => groups.value.map(category => ({
  category, functions: matches.value.filter(fn => fn.group === category),
})).filter(section => section.functions.length));
</script>

<template>
  <Dialog
    :visible="true"
    modal
    header="Select a transformation"
    :draggable="false"
    :close-on-escape="false"
    :close-button-props="{ 'aria-label': 'Close function library' }"
    :style="{ width: 'min(52rem, calc(100vw - 2rem))', height: 'min(44rem, 90dvh)', maxHeight: '90dvh' }"
    :content-style="{ display: 'flex', flex: '1', flexDirection: 'column', overflow: 'hidden', minHeight: '0', padding: '0' }"
    @show="focusSearch"
    @update:visible="!$event && emit('close')"
    @keydown.esc.stop.prevent="emit('close')"
  >
    <div class="shrink-0 border-b border-slate-200 px-6 pb-3">
      <p class="mb-3 text-sm text-slate-500">
        <span v-if="column" class="font-medium text-slate-800">{{ column }} · </span>{{ columnType || 'Unknown type' }}
        <span class="ml-2 text-xs">{{ functions.length }} available</span>
      </p>
      <input ref="searchInput" v-model="search" type="search" autofocus aria-label="Search functions" placeholder="Search by name or purpose…" class="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm" />
      <div class="mt-3 flex flex-wrap gap-1" role="group" aria-label="Function categories">
        <button v-for="category in ['', ...groups]" :key="category" type="button" class="rounded-full px-3 py-1.5 text-xs" :class="group === category ? 'bg-indigo-100 font-medium text-indigo-800' : 'text-slate-600 hover:bg-slate-100'" :aria-pressed="group === category" @click="group = category">{{ category || 'All' }}</button>
      </div>
    </div>
    <div class="min-h-0 flex-1 space-y-5 overflow-y-auto overscroll-contain px-6 py-4" role="group" aria-label="Function library">
      <section v-for="section in sections" :key="section.category">
        <h6 v-if="!group" class="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">{{ section.category }}</h6>
        <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <button v-for="fn in section.functions" :key="fn.id" type="button" :data-function="fn.id" :aria-pressed="selectedId === fn.id" class="block w-full rounded-xl border p-4 text-left transition-colors hover:border-indigo-300 hover:bg-indigo-50 focus-visible:outline-indigo-500" :class="selectedId === fn.id ? 'border-indigo-300 bg-indigo-50' : 'border-slate-200 bg-white'" @click="emit('choose', fn.id)">
            <span class="flex items-center justify-between gap-2">
              <span class="text-sm font-semibold text-slate-900">{{ fn.label }}</span>
              <span v-if="selectedId === fn.id" class="shrink-0 text-xs font-medium text-indigo-700">Current</span>
              <i v-else class="pi pi-arrow-right text-xs text-indigo-400" aria-hidden="true"></i>
            </span>
            <span class="mt-2 block text-sm leading-relaxed text-slate-500">{{ fn.description }}</span>
          </button>
        </div>
      </section>
      <p v-if="!matches.length" class="py-6 text-center text-sm text-slate-500">No matching function for this column type.</p>
    </div>
    <template #footer>
      <div class="flex items-center justify-between gap-3 border-t border-slate-200 pt-4 text-sm">
        <span class="text-slate-500">Need another expression?</span>
        <button type="button" class="font-medium text-indigo-700 hover:underline" @click="emit('sql')">Write SQL</button>
      </div>
    </template>
  </Dialog>
</template>
