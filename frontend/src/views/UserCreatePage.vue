<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { useToast } from "primevue/usetoast";
import type { UserCreate } from "../types/user";
import { UserAPI } from "../types/user";
import UserForm from "../components/UserForm.vue";

const router = useRouter();
const toast = useToast();

const saving = ref(false);
const model = ref<UserCreate>({
    username: "",
    password: ""
});

async function handleSubmit(payload: UserCreate) {
    saving.value = true;
    try {
        await UserAPI.create(payload);
        toast.add({ severity: "success", summary: "Created", detail: "User created", life: 2000 });
        router.push({ name: "users" });
    } catch (e) {
        console.error(e);
        toast.add({ severity: "error", summary: "Error", detail: "Unable to create user", life: 3000 });
    } finally {
        saving.value = false;
    }
}
</script>

<template>
    <div class="p-6 max-w-2xl mx-auto">
        <div class="flex items-center justify-between mb-6">
        <h1 class="text-2xl font-bold text-gray-800">New user</h1>
        <button class="px-3 py-2 rounded-lg border hover:bg-gray-50" @click="$router.back()">Back</button>
        </div>

        <UserForm
        v-model="model"
        :saving="saving"
        mode="create"
        @submit="handleSubmit"
        @cancel="$router.back()"
        />
    </div>
</template>

<style scoped></style>
