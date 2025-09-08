<script setup lang="ts">
    import { computed, ref } from "vue";
    import type { User, UserCreate } from "../types/user";

    type Mode = "create" | "edit";

    const props = withDefaults(defineProps<{
        modelValue: UserCreate | User;
        saving?: boolean;
        mode?: Mode;
    }>(), {
        saving: false,
        mode: "create",
    });

    const emit = defineEmits<{
        (e: "update:modelValue", value: UserCreate | User): void;
        (e: "submit", value: UserCreate | User): void;
        (e: "cancel"): void;
    }>();

    const local = computed<UserCreate | User>({
        get: () => props.modelValue,
        set: (v) => emit("update:modelValue", v),
    });

    const showPwd = ref(false);

    const errors = ref<{ username?: string; password?: string }>({});
    function validate() {
        const e: typeof errors.value = {};
        if (!(local.value as any).username) e.username = "Username required";
        if (props.mode === "create" && !(local.value as any).password) {
            e.password = "Password required";
        }
        errors.value = e;
        return Object.keys(e).length === 0;
    }

    function onSubmit() {
        if (!validate()) return;
        emit("submit", { ...(local.value as any) });
    }
</script>

<template>
    <form class="space-y-4" @submit.prevent="onSubmit">
        <div>
        <label class="block text-gray-700 mb-1">Username</label>
        <input
            v-model="(local as any).username"
            type="text"
            class="w-full px-3 py-2 border rounded-lg focus:ring"
            :disabled="saving"
        />
        <p v-if="errors.username" class="text-sm text-red-600 mt-1">{{ errors.username }}</p>
        </div>

        <div>
        <label class="block text-gray-700 mb-1">
            Password
            <span v-if="mode === 'edit'" class="text-gray-500 text-sm">Not updated if empty</span>
        </label>
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
            >
            {{ showPwd ? 'Hide' : 'Show' }}
            </button>
        </div>
        <p v-if="errors.password" class="text-sm text-red-600 mt-1">{{ errors.password }}</p>
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
