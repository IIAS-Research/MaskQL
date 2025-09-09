<script setup lang="ts">
    import { ref, watch, toRaw, unref, isProxy } from "vue";
    import type { Catalog, CatalogCreate } from "../types/catalog";

    type Mode = "create" | "edit";

    const props = withDefaults(defineProps<{
    modelValue: CatalogCreate | Catalog;
    saving?: boolean;
    mode?: Mode;
    }>(), {
    saving: false,
    mode: "create",
    });

    const emit = defineEmits<{
    (e: "update:modelValue", value: CatalogCreate | Catalog): void;
    (e: "submit", value: CatalogCreate | Catalog): void;
    (e: "cancel"): void;
    }>();
    
    const local = ref<CatalogCreate | Catalog>(props.modelValue);

    let syncingFromParent = false;
    watch(() => props.modelValue, (v) => {
    syncingFromParent = true;
    local.value = v;
    queueMicrotask(() => (syncingFromParent = false));
    });

    watch(local, (v) => {
    if (syncingFromParent) return;
    emit("update:modelValue", v);
    }, { deep: true });

    const showPwd = ref(false);

    const errors = ref<{ name?: string; url?: string; sgbd?: string }>({});
    function validate() {
    const e: typeof errors.value = {};
    if (!(local.value as any).name) e.name = "Nom requis";
    if (!(local.value as any).url) e.url = "URL requise";
    if (!(local.value as any).sgbd) e.sgbd = "SGBD requis";
    errors.value = e;
    return Object.keys(e).length === 0;
    }

    function onSubmit() {
    if (!validate()) return;
    emit("submit", local.value);
    }
</script>

<template>
    <form class="space-y-4" @submit.prevent="onSubmit">
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div class="sm:col-span-2">
            <label class="block text-gray-700 mb-1">Name</label>
            <input
            v-model="(local as any).name"
            type="text"
            class="w-full px-3 py-2 border rounded-lg focus:ring"
            :disabled="saving"
            />
            <p v-if="errors.name" class="text-sm text-red-600 mt-1">{{ errors.name }}</p>
        </div>

        <div class="sm:col-span-2">
            <label class="block text-gray-700 mb-1">URL</label>
            <input
            v-model="(local as any).url"
            type="url"
            class="w-full px-3 py-2 border rounded-lg focus:ring"
            :disabled="saving"
            />
            <p v-if="errors.url" class="text-sm text-red-600 mt-1">{{ errors.url }}</p>
        </div>

        <div>
            <label class="block text-gray-700 mb-1">SGBD</label>
            <input
            v-model="(local as any).sgbd"
            type="text"
            placeholder="ex: postgres, mysql…"
            class="w-full px-3 py-2 border rounded-lg focus:ring"
            :disabled="saving"
            />
            <p v-if="errors.sgbd" class="text-sm text-red-600 mt-1">{{ errors.sgbd }}</p>
        </div>

        <div>
            <label class="block text-gray-700 mb-1">Username</label>
            <input
            v-model="(local as any).username"
            type="text"
            class="w-full px-3 py-2 border rounded-lg focus:ring"
            :disabled="saving"
            />
        </div>

        <div class="sm:col-span-2">
            <label class="block text-gray-700 mb-1">Password</label>
            <div class="flex">
            <input
                v-model="(local as any).password"
                :type="showPwd ? 'text' : 'password'"
                class="w-full px-3 py-2 border rounded-l-lg focus:ring focus:outline-none"
                :disabled="saving"
            />
            <button
                type="button"
                class="px-3 border border-l-0 rounded-r-lg"
                @click="showPwd = !showPwd"
                :disabled="saving"
                title="Show/Hide"
            >
                {{ showPwd ? 'Hide' : 'Show' }}
            </button>
            </div>
        </div>
    </div>

    <div class="pt-2 flex gap-3">
        <button
            type="submit"
            :disabled="saving"
            class="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50"
        >
            <span v-if="mode === 'create' && !saving">Create</span>
            <span v-else-if="mode === 'edit' && !saving">Save</span>
            <span v-else>Loading...</span>
        </button>

        <button
            type="button"
            class="px-4 py-2 border rounded-lg hover:bg-gray-50"
            @click="emit('cancel')"
            :disabled="saving"
        >
            Cancel
        </button>
        </div>
    </form>
</template>

<style scoped></style>
