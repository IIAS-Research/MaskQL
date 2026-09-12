<script setup lang="ts">
import { computed } from "vue";
import { typeFamily, type ColumnInfo, type FunctionDefinition, type ParameterDefinition, type TransformDraft } from "../utils/ruleFunctions";
import RuleSelect from "./RuleSelect.vue";

const props = defineProps<{ id: string; definition: FunctionDefinition; transformation: TransformDraft; columnType: string | null; columns: ColumnInfo[] }>();
const emit = defineEmits<{ (event: "change", key: string, value: string): void }>();
const seedColumns = computed(() => props.columns.filter(column => !["unknown", "other", "binary"].includes(typeFamily(column.type))));
const seedColumnOptions = computed(() => {
  const options = seedColumns.value.map(column => ({ label: column.name, value: column.name }));
  const seed = props.transformation.values.seed;
  return seed && !options.some(option => option.value === seed)
    ? [{ label: seed, value: seed, disabled: true }, ...options]
    : options;
});
function inputType(kind: string) {
  if (kind === "secret") return "password";
  if (kind !== "value") return "text";
  const family = typeFamily(props.columnType);
  return family === "date" ? "date" : family === "timestamp" ? "datetime-local" : "text";
}
function change(key: string, event: Event) {
  emit("change", key, (event.target as HTMLInputElement).value);
}
function help(parameter: ParameterDefinition) {
  if (parameter.kind !== "value") return parameter.help;
  switch (typeFamily(props.columnType)) {
    case "text": return "Text to return, for example Unknown or REDACTED.";
    case "integer": return "A whole number, for example 0 or -1.";
    case "number": return "A number, with a decimal point if needed, for example 12.5.";
    case "boolean": return "Choose the true or false value to return.";
    case "date": return "Choose the calendar date to return.";
    case "timestamp": return "Choose the date and time to return, without a time zone.";
    case "binary": return "Bytes written as hexadecimal pairs, for example 48656c6c6f for Hello.";
    default: return parameter.help;
  }
}
</script>

<template>
  <div v-if="definition.parameters.length" class="space-y-4">
    <div v-for="parameter in definition.parameters" :key="parameter.key">
      <label :for="`${id}-${parameter.key}`" class="mb-1.5 block text-sm font-semibold text-slate-800">{{ parameter.label }}</label>
      <template v-if="parameter.kind === 'seed'">
        <RuleSelect :model-value="transformation.values.seedSource || 'fixed'" :options="[{ label: 'Fixed seed', value: 'fixed' }, { label: 'Value from a column', value: 'column' }]" aria-label="Seed source" :described-by="`${id}-${parameter.key}-help`" class="mb-1.5" @update:model-value="emit('change', 'seedSource', $event)" />
        <RuleSelect v-if="transformation.values.seedSource === 'column'" :id="`${id}-${parameter.key}`" :model-value="transformation.values[parameter.key] ?? null" :options="seedColumnOptions" placeholder="Choose a column" :filter="true" :aria-label="parameter.label" :described-by="`${id}-${parameter.key}-help`" @update:model-value="emit('change', parameter.key, $event)" />
        <input v-else :id="`${id}-${parameter.key}`" :value="transformation.values[parameter.key] ?? ''" :aria-describedby="`${id}-${parameter.key}-help`" class="parameter-input" @input="change(parameter.key, $event)" />
      </template>
      <RuleSelect v-else-if="parameter.options" :id="`${id}-${parameter.key}`" :model-value="transformation.values[parameter.key] ?? null" :options="parameter.options" placeholder="Choose" :aria-label="parameter.label" :described-by="`${id}-${parameter.key}-help`" @update:model-value="emit('change', parameter.key, $event)" />
      <RuleSelect v-else-if="parameter.kind === 'value' && typeFamily(columnType) === 'boolean'" :id="`${id}-${parameter.key}`" :model-value="transformation.values[parameter.key] ?? null" :options="[{ label: 'True', value: 'true' }, { label: 'False', value: 'false' }]" placeholder="Choose" :aria-label="parameter.label" :described-by="`${id}-${parameter.key}-help`" @update:model-value="emit('change', parameter.key, $event)" />
      <input v-else :id="`${id}-${parameter.key}`" :value="transformation.values[parameter.key] ?? ''" :type="inputType(parameter.kind)" :step="parameter.kind === 'value' && typeFamily(columnType) === 'timestamp' ? 'any' : undefined" :autocomplete="parameter.kind === 'secret' ? 'new-password' : undefined" :inputmode="['integer', 'number'].includes(parameter.kind) || (parameter.kind === 'value' && ['integer', 'number'].includes(typeFamily(columnType))) ? 'decimal' : 'text'" :aria-describedby="`${id}-${parameter.key}-help`" class="parameter-input" @input="change(parameter.key, $event)" />
      <p :id="`${id}-${parameter.key}-help`" class="mt-1.5 text-xs leading-relaxed text-slate-500">{{ help(parameter) }}</p>
    </div>
  </div>
</template>

<style scoped>
.parameter-input { @apply w-full min-w-0 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:border-accent-500 focus:outline-none focus:ring-2 focus:ring-accent-100; }
</style>
