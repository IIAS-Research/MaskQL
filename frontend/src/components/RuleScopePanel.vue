<script setup lang="ts">
type Status = "allow" | "deny" | "inherit";

const props = withDefaults(defineProps<{
    title: string;
    items: { key: string; label: string }[];
    isColumn?: boolean;
    selectedKey?: string | null;

    statusOf: (key: string) => Status;
    onAllow: (key: string) => void | Promise<void>;
    onDeny: (key: string) => void | Promise<void>;
    onInherit: (key: string) => void | Promise<void>;

    showEffect?: boolean;
    getEffect?: (key: string) => string;
    setEffect?: (key: string, val: string) => void;

    showAdd?: boolean;
    addModel?: string;
    addPlaceholder?: string;
    addDisabled?: boolean;
}>(), {
    showEffect: false,
    isColumn: false,
    showAdd: false,
    addModel: "",
    addPlaceholder: "",
    addDisabled: false,
});

const emit = defineEmits<{
    (e: "select", key: string): void;
    (e: "update:addModel", v: string): void;
}>();

function badgeClass(s: Status) {
    if (s === "allow") return "text-green-700 bg-green-50 border-green-200";
    if (s === "deny")  return "text-red-700 bg-red-50 border-red-200";
    return "text-gray-600 bg-gray-50 border-gray-200";
}
function segBtn(active: boolean) {
    return `px-2 py-1 text-xs leading-none ${active ? 'bg-gray-800 text-white' : 'bg-white text-gray-700 hover:bg-gray-50'}`;
}
</script>

<template>
    <div class="bg-white rounded-2xl shadow p-3 h-full flex flex-col">
        <div class="mb-3">
        <h2 class="font-semibold text-sm">{{ title }}</h2>
        </div>

        <ul class="space-y-2 pr-1 flex-1 min-h-0 mb-5">
        <li
            v-for="it in items"
            :key="it.key"
            class="border rounded-xl p-2 hover:bg-gray-50 cursor-pointer"
            :class="selectedKey === it.key ? 'ring-2 ring-indigo-500' : ''"
            @click="emit('select', it.key)"
        >
            <div class="text-sm font-medium truncate">{{ it.label }}</div>

            <div class="mt-2 flex items-center gap-2 flex-wrap">
            <span
                class="text-[10px] px-1.5 py-0.5 border rounded"
                :class="badgeClass(statusOf(it.key))"
            >
                {{ statusOf(it.key) === 'inherit' ? 'hérite' : (statusOf(it.key) === 'allow' ? 'allow' : 'deny') }}
            </span>

            <div class="inline-flex border rounded-lg">
                <button :class="segBtn(statusOf(it.key)==='allow')"   @click.stop="onAllow(it.key)"   title="Autoriser"><i class="pi pi-check text-xs"></i></button>
                <button :class="segBtn(statusOf(it.key)==='deny')"    @click.stop="onDeny(it.key)"    title="Refuser"><i class="pi pi-ban text-xs"></i></button>
                <button :class="segBtn(statusOf(it.key)==='inherit')" @click.stop="onInherit(it.key)" title="Hériter"><i class="pi pi-undo text-xs"></i></button>
            </div>
            </div>

            <div
                v-if="showEffect"
                class="mt-2"
            >
                <span v-if="isColumn" class="italic text-[10px]">
                    Transform column
                </span>
                <span v-else class="italic text-[10px]">
                    Filter rows (SQL where)
                </span>
                <input
                    :value="getEffect(it.key)"
                    @input="setEffect(it.key, ($event.target as HTMLInputElement).value)"
                    class="w-full px-2 py-1 h-9 text-sm border rounded-lg"
                    :placeholder='isColumn ? "lower(my_column)" : "my_column == 42"'
                />
            </div>
        </li>
        </ul>

        <div v-if="showAdd" class="space-y-2 border-t pt-3 mt-auto">
        <input
            :value="addModel"
            @input="emit('update:addModel', ($event.target as HTMLInputElement).value)"
            :placeholder="addPlaceholder"
            class="px-2 py-1 h-8 text-sm border rounded-lg w-full"
            :disabled="addDisabled"
        />
        <button
            class="h-8 px-2 text-sm border rounded-lg hover:bg-gray-50 text-gray-700 disabled:opacity-50 w-full"
            :disabled="addDisabled || !addModel?.trim()"
            @click="$emit('select', '__add__')"
        >
            Add
        </button>
        </div>
    </div>
</template>

<style>
@import "primeicons/primeicons.css";
</style>
