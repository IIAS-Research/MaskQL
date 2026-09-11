<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { useToast } from "primevue/usetoast";
import type { UserCreate } from "../types/user";
import { UserAPI } from "../types/user";
import UserForm from "../components/UserForm.vue";
import "../assets/directory.css";

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
    <div class="directory-form-page">
        <div class="directory-header">
        <h1 class="directory-title">Create user</h1>
        <button type="button" class="directory-secondary shrink-0" @click="$router.back()"><i class="pi pi-angle-left" aria-hidden="true"></i>Back</button>
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
