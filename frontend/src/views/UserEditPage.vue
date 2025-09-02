<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useToast } from "primevue/usetoast";
import type { User, UserUpdate } from "../types/user";
import { UserAPI } from "../types/user";
import UserForm from "../components/UserForm.vue";

const route = useRoute();
const router = useRouter();
const toast = useToast();

const id = Number(route.params.id);
const loading = ref(true);
const saving = ref(false);
const model = ref<User | null>(null);

async function load() {
    try {
        model.value = await UserAPI.getById(id);
        (model.value as any).password = "";
    } catch (e) {
        console.error(e);
        toast.add({ severity: "error", summary: "Error", detail: "Unable to load user", life: 3000 });
        router.push({ name: "users" });
        return;
    } finally {
        loading.value = false;
    }
}

async function handleSubmit(payload: User) {
    saving.value = true;
    try {
        const { id: payloadId, username, password } = payload;
        const update: UserUpdate = { username };
        if (password && password.trim() !== "") {
        update.password = password;
        }
        await UserAPI.update(Number(payloadId), update);
        toast.add({ severity: "success", summary: "Saved", detail: "User updated", life: 2000 });
        router.push({ name: "users" });
    } catch (e) {
        console.error(e);
        toast.add({ severity: "error", summary: "Error", detail: "Unable to update", life: 3000 });
    } finally {
        saving.value = false;
    }
}

onMounted(load);
</script>

<template>
    <div class="p-6 max-w-2xl mx-auto">
        <div class="flex items-center justify-between mb-6">
        <h1 class="text-2xl font-bold text-gray-800">Edit user</h1>
        <button class="px-3 py-2 rounded-lg border hover:bg-gray-50" @click="$router.back()">Back</button>
        </div>

        <div v-if="loading" class="text-gray-500">Loading...</div>

        <UserForm
        v-else
        v-model="model"
        :saving="saving"
        mode="edit"
        @submit="handleSubmit"
        @cancel="$router.back()"
        />
    </div>
</template>

<style scoped></style>
