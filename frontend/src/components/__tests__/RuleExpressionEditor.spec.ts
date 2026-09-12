import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import PrimeVue from "primevue/config";
import RuleExpressionEditor from "../RuleExpressionEditor.vue";

const columns = [
  { name: "name", type: "varchar" }, { name: "patient_id", type: "bigint" },
  { name: "active", type: "boolean" }, { name: "birth_date", type: "date" },
  { name: "document", type: "varbinary" },
];
const props = { id: "rule", kind: "mask" as const, column: "name", columns, modelValue: "" };
const global = { plugins: [PrimeVue], stubs: { teleport: true } };
const button = (wrapper: ReturnType<typeof mount>, label: string) => wrapper.findAll("button").find(node => node.text() === label)!;

async function openSelect(wrapper: ReturnType<typeof mount>, selector: string) {
  const control = wrapper.get(selector);
  await control.trigger("click");
  return wrapper.get(`[id="${control.attributes("aria-controls")}"][role="listbox"]`);
}

async function selectOption(wrapper: ReturnType<typeof mount>, selector: string, label: string) {
  const listbox = await openSelect(wrapper, selector);
  const option = listbox.findAll('[role="option"]').find(node => node.text() === label)!;
  await option.trigger("click");
  await new Promise(resolve => setTimeout(resolve, 0));
}

async function availableOptions(wrapper: ReturnType<typeof mount>, selector: string) {
  const listbox = await openSelect(wrapper, selector);
  const labels = listbox.findAll('[role="option"]').filter(node => node.attributes("aria-disabled") !== "true").map(node => node.text());
  await wrapper.get(selector).trigger("keydown", { key: "Escape", code: "Escape" });
  await new Promise(resolve => setTimeout(resolve, 0));
  return labels;
}

describe("rule expression editor", () => {
  it("keeps complex SQL verbatim until a complete replacement is chosen", async () => {
    const sql = "lower(trim(name))";
    const wrapper = mount(RuleExpressionEditor, { global, props: { ...props, modelValue: sql } });
    expect(wrapper.get('[role="tab"][aria-selected="true"]').text()).toBe('SQL editor');
    await button(wrapper, "SQL editor").trigger("keydown", { key: 'ArrowLeft' });
    expect(wrapper.get('[role="tab"][aria-selected="true"]').text()).toBe('Visual editor');
    expect(wrapper.get('[role="tabpanel"]').attributes('aria-labelledby')).toBe('rule-tab-guided');
    expect(wrapper.emitted("update:modelValue")).toBeUndefined();
    await button(wrapper, "Continue in SQL editor").trigger("click");
    expect(wrapper.get("textarea").element.value).toBe(sql);
    expect(wrapper.emitted("update:modelValue")).toBeUndefined();
    await button(wrapper, "Visual editor").trigger("click");
    await button(wrapper, "Replace SQL with a visual rule").trigger("click");
    await button(wrapper, "Write SQL").trigger("click");
    expect(wrapper.get("textarea").element.value).toBe(sql);
    expect(wrapper.emitted("update:modelValue")).toBeUndefined();
    await button(wrapper, "Visual editor").trigger("click");
    await button(wrapper, "Select a transformation").trigger("click");
    await wrapper.get('[data-function="encrypt"]').trigger("click");
    expect(wrapper.emitted("update:modelValue")).toEqual([['encrypt("name")']]);
  });

  it("uses the selected column type and keeps incomplete conditions across mode changes", async () => {
    const wrapper = mount(RuleExpressionEditor, { global, props: { ...props, kind: "filter", modelValue: "patient_id <= 3" } });
    expect(wrapper.find('[aria-label="Value type 1"]').exists()).toBe(false);
    const numericOperators = await availableOptions(wrapper, '[role="combobox"][aria-label="Operator 1"]');
    expect(numericOperators).toContain("at most");
    expect(numericOperators).not.toContain("contains");
    await button(wrapper, "Add condition").trigger("click");
    await selectOption(wrapper, '[role="combobox"][aria-label="Column 2"]', "active");
    const booleanOperators = await availableOptions(wrapper, '[role="combobox"][aria-label="Operator 2"]');
    expect(booleanOperators).toContain("equals");
    expect(booleanOperators).not.toContain("greater than");
    expect(await availableOptions(wrapper, '[role="combobox"][aria-label="Value 2"]')).toEqual(["True", "False"]);
    await selectOption(wrapper, '[role="combobox"][aria-label="Column 2"]', "name");
    expect(wrapper.text()).toContain("Changes are not saved");
    await button(wrapper, "SQL editor").trigger("click");
    expect(wrapper.get("textarea").element.value).toBe("patient_id <= 3");
    await button(wrapper, "Visual editor").trigger("click");
    expect(wrapper.findAll('[role="combobox"][aria-label^="Column "]')).toHaveLength(2);
    expect(wrapper.emitted("update:modelValue")).toBeUndefined();
    await wrapper.get('[aria-label="Value 2"]').setValue("O'Connor");
    expect(wrapper.emitted("update:modelValue")).toEqual([[`("patient_id" <= 3) AND ("name" = 'O''Connor')`]]);
  });

  it("explains parameters and requires an explicit seed that can come from a column", async () => {
    const wrapper = mount(RuleExpressionEditor, { global, props });
    await button(wrapper, "Select a transformation").trigger("click");
    await wrapper.get('[aria-label="Search functions"]').setValue("pseudonym");
    expect(wrapper.find('[data-function="lower"]').exists()).toBe(false);
    await wrapper.get('[data-function="text_pseudo"]').trigger("click");
    expect(wrapper.get('#rule-params-seed-help').text()).not.toBe("");
    expect(wrapper.get('#rule-params-seed').attributes('aria-describedby')).toBe('rule-params-seed-help');
    expect(wrapper.emitted("update:modelValue")).toBeUndefined();
    await selectOption(wrapper, '[role="combobox"][aria-label="Seed source"]', "Value from a column");
    const seedColumns = await availableOptions(wrapper, "#rule-params-seed");
    expect(seedColumns).toContain("patient_id");
    expect(seedColumns).not.toContain("document");
    await selectOption(wrapper, "#rule-params-seed", "patient_id");
    expect(wrapper.emitted("update:modelValue")).toEqual([['text_pseudo("name", CAST("patient_id" AS VARCHAR))']]);
  });

  it("replaces the single function without saving unfinished parameters", async () => {
    const wrapper = mount(RuleExpressionEditor, { global, props: { ...props, modelValue: "trim(name)" } });
    expect(wrapper.text()).not.toContain("Add another function");
    await button(wrapper, "Change").trigger("click");
    expect(wrapper.find('[data-transformation]').exists()).toBe(true);
    expect(wrapper.get('[role="dialog"]').text()).toContain('Select a transformation');
    await wrapper.get('[role="dialog"]').trigger('keydown', { key: 'Escape', code: 'Escape' });
    expect(wrapper.find('[role="dialog"]').exists()).toBe(false);
    expect(wrapper.emitted("update:modelValue")).toBeUndefined();
    await button(wrapper, "Change").trigger("click");
    await wrapper.get('[data-function="substring"]').trigger("click");
    expect(wrapper.emitted("update:modelValue")).toBeUndefined();
    await wrapper.get('#rule-params-length').setValue('3');
    expect(wrapper.emitted("update:modelValue")?.at(-1)).toEqual(['substring("name", 1, 3)']);
    expect(wrapper.findAll('[data-transformation]')).toHaveLength(1);
    expect(wrapper.get('details').attributes('open')).toBeUndefined();
    await button(wrapper, "Change").trigger("click");
    await wrapper.get('[data-function="lower"]').trigger("click");
    expect(wrapper.emitted("update:modelValue")?.at(-1)).toEqual(['lower("name")']);
    await wrapper.get('[aria-label="Remove transformation"]').trigger('click');
    expect(wrapper.emitted("update:modelValue")?.at(-1)).toEqual(['']);
  });

  it("filters functions by type and handles metadata arriving after the SQL", async () => {
    const wrapper = mount(RuleExpressionEditor, { global, props: { ...props, columns: [{ name: "name", type: null }], modelValue: "lower(trim(name))" } });
    expect(wrapper.get('textarea').element.value).toBe('lower(trim(name))');
    await wrapper.setProps({ columns });
    expect(wrapper.get('textarea').element.value).toBe('lower(trim(name))');
    expect(wrapper.find('[data-transformation]').exists()).toBe(false);
    await wrapper.setProps({ modelValue: 'lower(name)' });
    expect(wrapper.find('textarea').exists()).toBe(false);
    expect(wrapper.findAll('[data-transformation]')).toHaveLength(1);
    expect(wrapper.emitted("update:modelValue")).toBeUndefined();
    const numeric = mount(RuleExpressionEditor, { global, props: { ...props, column: "patient_id" } });
    await button(numeric, 'Select a transformation').trigger('click');
    expect(numeric.find('[data-function="text_pseudo"]').exists()).toBe(false);
    expect(numeric.find('[data-function="date_add"]').exists()).toBe(false);
    expect(numeric.find('[data-function="round"]').exists()).toBe(true);
    await numeric.setProps({ columns: [{ name: 'patient_id', type: null }] });
    await button(numeric, 'Select a transformation').trigger('click');
    expect(numeric.findAll('[data-function]')).toHaveLength(1);
  });

  it("keeps server errors visible and restores the saved rule without another write", async () => {
    const wrapper = mount(RuleExpressionEditor, { global, props: {
      ...props, modelValue: "not_a_function(name)", feedback: { status: "error", message: "Expression rejected" },
    } });
    expect(wrapper.get("textarea").attributes("aria-invalid")).toBe("true");
    expect(wrapper.get('[role="status"]').text()).toContain("Non sauvegardé.");
    await button(wrapper, "Rétablir").trigger("click");
    expect(wrapper.emitted("restore")).toHaveLength(1);
    await wrapper.setProps({ modelValue: "encrypt(name)", feedback: undefined });
    expect(wrapper.text()).toContain("Encrypt");
    expect(wrapper.emitted("update:modelValue")).toBeUndefined();
  });
});
