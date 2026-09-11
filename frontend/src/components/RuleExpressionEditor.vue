<script setup lang="ts">
import { computed, nextTick, ref, watch } from "vue";
import { buildFilter, newCondition, parseFilter, type FilterDraft, type FilterCondition, type FilterOperator, type ValueType } from "../utils/ruleExpressions";
import { buildTransform, compatibleFunctions, newTransform, parseTransform, ruleFunctions, typeFamily, type ColumnInfo, type TransformDraft } from "../utils/ruleFunctions";
import RuleFunctionPicker from "./RuleFunctionPicker.vue";
import RuleFunctionParameters from "./RuleFunctionParameters.vue";
import RuleSelect from "./RuleSelect.vue";

const props = defineProps<{
  id: string;
  modelValue: string;
  kind: "filter" | "mask";
  columns: ColumnInfo[];
  column?: string;
  typesLoading?: boolean;
  describedBy?: string;
  feedback?: { status: "saving" | "saved" | "error"; message: string };
}>();
const emit = defineEmits<{ (event: "update:modelValue", value: string): void; (event: "restore"): void }>();
const mode = ref<"guided" | "sql">("guided");
const filter = ref<FilterDraft>({ join: "AND", conditions: [] });
const transformation = ref<TransformDraft | null>(null);
const hasGuide = ref(true);
const touched = ref(false);
const replacingSql = ref(false);
const choosing = ref(false);
let modeChosen = false;
let lastEmitted: string | undefined;
const columnType = computed(() => typeOf(props.column ?? ""));
const available = computed(() => compatibleFunctions(columnType.value));
const definition = computed(() => ruleFunctions.find(fn => fn.id === transformation.value?.functionId));
const operators: { value: FilterOperator; label: string }[] = [
  { value: "eq", label: "equals" }, { value: "ne", label: "does not equal" },
  { value: "gt", label: "greater than" }, { value: "gte", label: "at least" },
  { value: "lt", label: "less than" }, { value: "lte", label: "at most" },
  { value: "contains", label: "contains" }, { value: "starts", label: "starts with" },
  { value: "ends", label: "ends with" },
  { value: "is_null", label: "is empty (NULL)" }, { value: "not_null", label: "is not empty (NULL)" },
];
function typeOf(column: string) { return props.columns.find(item => item.name === column)?.type ?? null; }
function valueType(column: string): ValueType | null {
  const family = typeFamily(typeOf(column));
  if (family === "integer" || family === "number") return "number";
  return ["text", "boolean", "date", "timestamp"].includes(family) ? family as ValueType : null;
}
function operatorChoices(column: string) {
  const family = typeFamily(typeOf(column));
  return operators.filter(operator => {
    if (["is_null", "not_null"].includes(operator.value)) return true;
    if (["unknown", "other", "binary"].includes(family)) return false;
    if (["contains", "starts", "ends"].includes(operator.value)) return family === "text";
    return family !== "boolean" || ["eq", "ne"].includes(operator.value);
  });
}
function needsValue(operator: FilterOperator) { return !["is_null", "not_null"].includes(operator); }
function compatibleCondition(condition: FilterCondition) {
  return operatorChoices(condition.column).some(operator => operator.value === condition.operator) &&
    (!needsValue(condition.operator) || condition.value.type === valueType(condition.column));
}
function readSql(sql: string) {
  if (props.kind === "filter") {
    const parsed = parseFilter(sql);
    hasGuide.value = parsed !== null;
    if (parsed) filter.value = parsed;
  } else {
    const parsed = parseTransform(props.column ?? "", columnType.value, sql);
    hasGuide.value = parsed !== null;
    if (parsed) transformation.value = parsed.transform;
  }
  touched.value = false;
  replacingSql.value = false;
  choosing.value = false;
}
watch([() => props.modelValue, columnType], ([sql, type], [oldSql, oldType]) => {
  if (sql === lastEmitted && type === oldType) { lastEmitted = undefined; return; }
  if (sql === oldSql && touched.value && type !== oldType) return;
  readSql(sql);
  if (!hasGuide.value) mode.value = "sql";
  else if (!modeChosen) mode.value = "guided";
}, { immediate: true });
const generated = computed(() => {
  if (props.kind === "mask") return buildTransform(props.column ?? "", columnType.value, transformation.value);
  if (filter.value.conditions.some(condition => !compatibleCondition(condition))) return null;
  return buildFilter(filter.value);
});
const incomplete = computed(() => mode.value === "guided" && hasGuide.value && touched.value && generated.value === null);
const feedbackId = computed(() => `${props.id}-feedback`);
const describedBy = computed(() => [props.describedBy, props.feedback || incomplete.value ? feedbackId.value : ""].filter(Boolean).join(" ") || undefined);
function write(sql: string) {
  if (sql === props.modelValue) return;
  lastEmitted = sql;
  emit("update:modelValue", sql);
}
function updateGuide() {
  touched.value = true;
  if (generated.value !== null) { replacingSql.value = false; write(generated.value); }
}
function setMode(next: "guided" | "sql") { modeChosen = true; mode.value = next; choosing.value = false; }
function editSql() {
  setMode("sql");
  nextTick(() => document.getElementById(props.id)?.focus());
}
function navigateTabs(event: KeyboardEvent) {
  if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
  event.preventDefault();
  const next = event.key === "Home" ? "guided" : event.key === "End" ? "sql" : mode.value === "guided" ? "sql" : "guided";
  setMode(next);
  nextTick(() => document.getElementById(`${props.id}-tab-${next}`)?.focus());
}
function updateSql(event: Event) { const sql = (event.target as HTMLTextAreaElement).value; readSql(sql); write(sql); }
function startGuide() {
  filter.value = { join: "AND", conditions: [newCondition()] };
  transformation.value = null;
  hasGuide.value = true;
  touched.value = false;
  replacingSql.value = true;
  choosing.value = props.kind === "mask";
}
function chooseFunction(id: string) {
  if (!choosing.value || !available.value.some(fn => fn.id === id)) return;
  if (transformation.value?.functionId === id) { closePicker(); return; }
  transformation.value = newTransform(id);
  updateGuide();
  closePicker();
}
function closePicker() {
  choosing.value = false;
  nextTick(() => document.getElementById(props.id)?.focus());
}
function changeParameter(key: string, value: string) {
  if (!transformation.value) return;
  transformation.value.values[key] = value;
  if (key === "seedSource") transformation.value.values.seed = null;
  updateGuide();
}
function removeTransformation() {
  transformation.value = null;
  updateGuide();
  closePicker();
}
function columnChoices(column: string) {
  const choices = props.columns.map(item => ({ label: item.name, value: item.name }));
  if (column && !choices.some(item => item.value === column)) choices.unshift({ label: column, value: column });
  return choices;
}
function conditionOperators(condition: FilterCondition) {
  const choices = operatorChoices(condition.column);
  return operators.filter(operator => choices.includes(operator) || operator.value === condition.operator)
    .map(operator => ({ ...operator, disabled: !choices.includes(operator) }));
}
function changeColumn(index: number, column: string) {
  const condition = filter.value.conditions[index];
  condition.column = column;
  condition.value = { type: valueType(condition.column) ?? "text", text: null };
  if (!operatorChoices(condition.column).some(operator => operator.value === condition.operator)) condition.operator = valueType(condition.column) ? "eq" : "is_null";
  updateGuide();
}
function changeOperator(condition: FilterCondition, operator: string) {
  condition.operator = operator as FilterOperator;
  updateGuide();
}
function changeValue(condition: FilterCondition, value: string) {
  condition.value.type = valueType(condition.column) ?? condition.value.type;
  condition.value.text = value;
  updateGuide();
}
function addCondition() { filter.value.conditions.push(newCondition()); updateGuide(); }
function removeCondition(index: number) { filter.value.conditions.splice(index, 1); updateGuide(); }
function resetGuide() { readSql(props.modelValue); if (!hasGuide.value) mode.value = "sql"; }
</script>

<template>
  <div class="rule-expression-editor" :class="{ 'mt-2': kind === 'filter' }" role="group" :aria-label="kind === 'mask' ? `Transformation for ${column}` : 'Row filter expression'">
    <div class="flex border-b border-slate-200" role="tablist" aria-label="Expression editor" @keydown="navigateTabs">
      <button v-for="option in (['guided', 'sql'] as const)" :id="`${id}-tab-${option}`" :key="option" type="button" role="tab" class="-mb-px flex flex-1 items-center justify-center gap-2 border-b-2 px-2 pb-3 pt-1 text-sm transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600" :class="mode === option ? 'border-indigo-600 font-semibold text-indigo-700' : 'border-transparent text-slate-500 hover:border-slate-300 hover:text-slate-800'" :aria-selected="mode === option" :aria-controls="`${id}-panel`" :tabindex="mode === option ? 0 : -1" @click="setMode(option)">
        <i :class="option === 'guided' ? 'pi pi-sliders-h' : 'pi pi-code'" class="text-sm" aria-hidden="true"></i>{{ option === 'guided' ? 'Visual editor' : 'SQL editor' }}
      </button>
    </div>
    <div :id="`${id}-panel`" role="tabpanel" :aria-labelledby="`${id}-tab-${mode}`" tabindex="0" class="space-y-3 pt-4 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600">
      <textarea v-if="mode === 'sql'" :id="id" :value="modelValue" @input="updateSql" :rows="kind === 'filter' ? 3 : 2" class="w-full rounded-lg border px-2.5 py-2 font-mono text-sm" :class="{ 'border-red-500 bg-red-50': feedback?.status === 'error' }" :aria-label="kind === 'mask' ? `SQL transformation for ${column}` : 'SQL row filter'" :aria-invalid="feedback?.status === 'error'" :aria-describedby="describedBy" :placeholder="kind === 'filter' ? `country = 'FR'` : 'lower(my_column)'"></textarea>
      <div v-else-if="!hasGuide" class="rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs text-slate-600">
        <p class="font-medium text-slate-700">Visual editor unavailable for this SQL expression.</p>
        <div class="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1">
          <button type="button" class="font-medium text-indigo-700 hover:underline" @click="startGuide">Replace SQL with a visual rule</button>
          <span class="inline-flex items-center gap-2">or <button type="button" class="font-medium text-indigo-700 hover:underline" @click="editSql">Continue in SQL editor</button></span>
        </div>
      </div>
      <div v-else role="group" :aria-label="kind === 'filter' ? 'Filter conditions' : 'Transformation settings'" :aria-describedby="describedBy" :aria-invalid="incomplete || feedback?.status === 'error'" class="space-y-3" :class="{ 'rounded-lg border border-red-400 p-2': feedback?.status === 'error' }">
        <p v-if="replacingSql" class="text-xs text-slate-600">Your SQL stays in effect until a complete replacement is entered.</p>
        <template v-if="kind === 'filter'">
          <div v-if="filter.conditions.length" class="flex flex-wrap items-center gap-x-3 gap-y-2">
            <span class="text-xs font-medium text-slate-600">Keep rows matching</span>
            <div role="group" aria-label="Combine conditions" class="inline-flex rounded-lg bg-slate-200/70 p-0.5">
              <button v-for="join in (['AND', 'OR'] as const)" :key="join" type="button" :aria-pressed="filter.join === join" :title="join === 'AND' ? 'Every condition must match' : 'At least one condition must match'" class="rounded-md px-3 py-1.5 text-xs font-medium transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 disabled:opacity-50" :class="filter.join === join ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-600 hover:bg-white hover:text-slate-900'" :disabled="typesLoading" @click="filter.join = join; updateGuide()">{{ join === 'AND' ? 'All conditions' : 'Any condition' }}</button>
            </div>
          </div>
          <p v-if="!filter.conditions.length" class="py-2 text-sm text-slate-500">All rows are kept. Add a condition to restrict access.</p>
          <div v-if="filter.conditions.length">
            <div class="hidden sm:block" aria-hidden="true">
              <div class="filter-condition-row mb-1 text-xs font-medium text-slate-600">
                <span>Column</span>
                <span>Condition</span>
                <span v-if="filter.conditions.some(condition => needsValue(condition.operator))">Value</span>
              </div>
            </div>
            <div v-for="(condition, index) in filter.conditions" :key="index">
              <div v-if="index" class="flex h-3 items-center gap-2" aria-hidden="true">
                <span class="h-px flex-1 bg-slate-200"></span>
                <span class="text-[10px] font-semibold leading-3 text-slate-500">{{ filter.join }}</span>
                <span class="h-px flex-1 bg-slate-200"></span>
              </div>
              <div class="filter-condition-row">
                <label class="col-start-1 row-start-1 min-w-0 text-xs text-slate-600">
                  <span class="font-medium sm:hidden">Column</span>
                  <RuleSelect :id="index === 0 ? id : `${id}-column-${index}`" :model-value="condition.column" :options="columnChoices(condition.column)" :type-label="typeOf(condition.column)" :aria-label="`Column ${index + 1}`" placeholder="Choose a column" filter class="mt-1 sm:mt-0" :disabled="typesLoading" @update:model-value="changeColumn(index, $event)" />
                </label>
                <label class="col-span-2 min-w-0 text-xs text-slate-600 sm:col-span-1 sm:col-start-2 sm:row-start-1"><span class="font-medium sm:hidden">Condition</span>
                  <RuleSelect :model-value="condition.operator" :options="conditionOperators(condition)" :aria-label="`Operator ${index + 1}`" class="mt-1 sm:mt-0" :disabled="!condition.column || typesLoading" @update:model-value="changeOperator(condition, $event)" />
                </label>
                <label v-if="needsValue(condition.operator)" class="col-span-2 min-w-0 text-xs text-slate-600 sm:col-span-1 sm:col-start-3 sm:row-start-1"><span class="font-medium sm:hidden">Value</span>
                  <RuleSelect v-if="condition.value.type === 'boolean'" :model-value="condition.value.text" :options="[{ label: 'True', value: 'true' }, { label: 'False', value: 'false' }]" :aria-label="`Value ${index + 1}`" class="mt-1 sm:mt-0" @update:model-value="changeValue(condition, $event)" />
                  <input v-else :value="condition.value.text ?? ''" :type="condition.value.type === 'date' ? 'date' : condition.value.type === 'timestamp' ? 'datetime-local' : 'text'" :step="condition.value.type === 'timestamp' ? 'any' : undefined" :inputmode="condition.value.type === 'number' ? 'decimal' : 'text'" :aria-label="`Value ${index + 1}`" class="expression-control mt-1 w-full sm:mt-0" :disabled="!condition.column" @input="changeValue(condition, ($event.target as HTMLInputElement).value)" />
                </label>
                <button type="button" :aria-label="`Remove condition ${index + 1}`" title="Remove condition" class="col-start-2 row-start-1 h-10 w-8 rounded-lg text-slate-400 hover:bg-red-50 hover:text-red-700 sm:col-start-4" @click="removeCondition(index)"><i class="pi pi-times text-xs" aria-hidden="true"></i></button>
              </div>
              <p v-if="condition.column && !compatibleCondition(condition) && !typesLoading" class="mt-2 text-xs text-amber-700">This condition does not match the column type. Adjust it or use SQL.</p>
              <p v-else-if="['contains', 'starts', 'ends'].includes(condition.operator)" class="mt-2 text-xs text-slate-500">Matches the text exactly, including uppercase and lowercase. % and _ are ordinary characters.</p>
              <p v-else-if="!needsValue(condition.operator)" class="mt-2 text-xs text-slate-500">NULL means a missing value; an empty text is a different value.</p>
            </div>
          </div>
          <button :id="!filter.conditions.length ? id : undefined" type="button" class="inline-flex items-center gap-2 rounded-lg border border-indigo-200 bg-white px-3 py-2 text-sm font-medium text-indigo-700 hover:bg-indigo-50 disabled:opacity-50" :disabled="typesLoading" @click="addCondition"><i class="pi pi-plus text-xs" aria-hidden="true"></i>Add condition</button>
        </template>
        <template v-else>
          <RuleFunctionPicker v-if="choosing" :column="column" :column-type="columnType" :selected-id="transformation?.functionId" @choose="chooseFunction" @close="closePicker" @sql="editSql" />
          <div v-if="transformation && definition" class="space-y-4" data-transformation>
            <div>
              <div class="flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
                <h5 class="min-w-[8rem] flex-1 text-base font-semibold text-slate-900">{{ definition.label }}</h5>
                <div class="flex shrink-0 items-center gap-1" role="group" aria-label="Transformation actions">
                  <button :id="id" type="button" class="rounded-md px-2 py-1.5 text-xs font-medium text-indigo-700 hover:bg-indigo-50" :disabled="typesLoading" @click="choosing = true">Change</button>
                  <button type="button" class="rounded-md px-2 py-1.5 text-xs font-medium text-slate-500 hover:bg-red-50 hover:text-red-700" aria-label="Remove transformation" @click="removeTransformation">Remove</button>
                </div>
              </div>
              <p class="mt-1.5 text-sm leading-relaxed text-slate-600">{{ definition.description }}</p>
            </div>
            <RuleFunctionParameters :id="`${id}-params`" :definition="definition" :transformation="transformation" :column-type="columnType" :columns="columns" @change="changeParameter" />
            <p v-if="definition.caution?.(columnType)" class="rounded-lg bg-amber-50 p-2.5 text-xs text-amber-800">{{ definition.caution?.(columnType) }}</p>
            <details v-if="definition.example" class="text-xs text-slate-500">
              <summary class="cursor-pointer hover:text-slate-800">Example</summary>
              <p class="mt-2 whitespace-pre-wrap leading-relaxed text-slate-600">{{ definition.example }}</p>
            </details>
          </div>
          <div v-else class="space-y-2">
            <button :id="id" type="button" class="flex w-full items-center justify-between gap-3 rounded-lg border border-indigo-600 bg-indigo-600 px-4 py-3 text-left text-sm font-semibold text-white shadow-sm transition-colors hover:border-indigo-700 hover:bg-indigo-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 disabled:opacity-50" :disabled="typesLoading" @click="choosing = true">Select a transformation<i class="pi pi-chevron-down text-xs text-indigo-100" aria-hidden="true"></i></button>
            <p class="text-xs text-slate-500">{{ replacingSql ? 'Select the replacement for your SQL expression.' : 'No transformation applied.' }}</p>
          </div>
          <p v-if="!columnType && !typesLoading" class="text-xs text-slate-500">The column type is unavailable. Only hiding the value is offered; SQL remains available.</p>
        </template>
      </div>
      <p v-if="incomplete" :id="feedbackId" role="status" class="text-xs text-amber-700">Complete the fields with valid values. Changes are not saved. <button type="button" class="ml-1 underline" @click="resetGuide">Cancel</button></p>
      <p v-else-if="feedback" :id="feedbackId" role="status" aria-live="polite" class="text-xs" :class="feedback.status === 'error' ? 'text-red-700' : feedback.status === 'saved' ? 'text-green-700' : 'text-slate-500'">
        <strong v-if="feedback.status === 'error'">Non sauvegardé. </strong>{{ feedback.message }}
        <button v-if="feedback.status === 'error'" type="button" class="ml-2 inline-flex items-center gap-1 rounded px-1 text-xs text-slate-600 hover:bg-slate-100 hover:text-slate-900" title="Revenir à la dernière version enregistrée" @click="emit('restore')"><i class="pi pi-undo text-[10px]" aria-hidden="true"></i>Rétablir</button>
      </p>
    </div>
  </div>
</template>

<style scoped>
.expression-control { @apply min-w-0 rounded-lg border border-slate-200 bg-white px-2.5 py-2 text-sm text-slate-800; }
.filter-condition-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 2rem;
  align-items: end;
  gap: 0.75rem;
}
@media (min-width: 640px) {
  .filter-condition-row {
    grid-template-columns: repeat(3, minmax(0, 1fr)) 2rem;
  }
}
</style>
