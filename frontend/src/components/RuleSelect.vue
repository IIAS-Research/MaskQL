<script setup lang="ts">
import { computed, ref } from "vue";
import Dropdown from "primevue/dropdown";

const props = withDefaults(defineProps<{
  id?: string;
  modelValue: string | null;
  options: { label: string; value: string; disabled?: boolean }[];
  placeholder?: string;
  disabled?: boolean;
  filter?: boolean;
  ariaLabel?: string;
  describedBy?: string;
  typeLabel?: string | null;
}>(), { placeholder: "Choose" });
const emit = defineEmits<{ (event: "update:modelValue", value: string): void }>();
const open = ref(false);
const selectedLabel = computed(() => props.options.find(option => option.value === props.modelValue)?.label || props.modelValue || props.placeholder);
function onKeydown(event: KeyboardEvent) {
  if (event.key === "Escape" && open.value) event.stopPropagation();
}
</script>

<template>
  <Dropdown
    :input-id="id"
    :model-value="modelValue"
    :options="options"
    option-label="label"
    option-value="value"
    option-disabled="disabled"
    :placeholder="placeholder"
    :disabled="disabled"
    :filter="filter"
    filter-placeholder="Search columns"
    :filter-input-props="{ 'aria-label': 'Search columns' }"
    reset-filter-on-hide
    :aria-label="ariaLabel"
    :input-props="{ 'aria-describedby': describedBy }"
    :panel-props="{ onKeydown }"
    class="rule-select"
    panel-class="rule-select-panel"
    scroll-height="14rem"
    @before-show="open = true"
    @hide="open = false"
    @keydown="onKeydown"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <template #value>
      <span class="flex min-w-0 items-center gap-2" :class="{ 'text-slate-400': !modelValue }">
        <span class="min-w-0 flex-1 truncate">{{ selectedLabel }}</span>
        <span v-if="typeLabel" class="max-w-[40%] shrink-0 truncate font-mono text-[10px] text-slate-400" :title="typeLabel">{{ typeLabel }}</span>
      </span>
    </template>
  </Dropdown>
</template>

<style scoped>
.rule-select.p-dropdown { @apply w-full min-w-0 rounded-lg border border-slate-200 bg-white; }
.rule-select.p-dropdown:not(.p-disabled):hover { @apply border-slate-400; }
.rule-select.p-dropdown.p-focus { @apply border-accent-500 ring-2 ring-accent-100; }
.rule-select :deep(.p-dropdown-label) { @apply min-w-0 px-2.5 py-2 text-sm leading-5 text-slate-800; }
.rule-select :deep(.p-dropdown-trigger) { @apply w-8 text-slate-400; }
.rule-select :deep(.p-dropdown-trigger-icon) { @apply h-3 w-3; }
:global(.rule-select-panel.p-dropdown-panel) { @apply overflow-hidden rounded-lg border border-slate-200; max-width: calc(100vw - 2rem); }
:global(.rule-select-panel.p-dropdown-panel .p-dropdown-header) { @apply border-b border-slate-200 bg-slate-50 p-2; }
:global(.rule-select-panel.p-dropdown-panel .p-dropdown-filter) { @apply py-2 pl-2.5 pr-8 text-sm; }
:global(.rule-select-panel.p-dropdown-panel .p-dropdown-items) { @apply py-1; }
:global(.rule-select-panel.p-dropdown-panel .p-dropdown-items .p-dropdown-item) { @apply whitespace-normal px-3 py-2 text-sm; overflow-wrap: anywhere; }
:global(.rule-select-panel.p-dropdown-panel .p-dropdown-items .p-dropdown-item.p-highlight),
:global(.rule-select-panel.p-dropdown-panel .p-dropdown-items .p-dropdown-item.p-highlight.p-focus) { @apply bg-accent-200 font-medium text-accent-900; }
:global(.rule-select-panel.p-dropdown-panel .p-dropdown-items .p-dropdown-empty-message) { @apply px-3 py-2 text-sm text-slate-500; }
</style>
