<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useToast } from "primevue/usetoast";
import type { User } from "../types/user";
import { UserAPI } from "../types/user";
import RuleManager from "../components/RuleManager.vue";
import "../assets/directory.css";

const route = useRoute();
const router = useRouter();
const toast = useToast();

const id = Number(route.params.id);
const loading = ref(true);
const user = ref<User | null>(null);

async function load() {
    try {
        user.value = await UserAPI.getById(id);
    } catch (e) {
        console.error(e);
        toast.add({ severity: "error", summary: "Error", detail: "Unknown user", life: 3000 });
        router.push({ name: "users" });
        return;
    } finally {
        loading.value = false;
    }
}

onMounted(load);
</script>

<template>
    <div class="directory-page space-y-6">
        <div class="directory-header">
        <div class="min-w-0">
            <h1 class="directory-title">Manage user access</h1>
            <p class="directory-subtitle break-words">User: <span class="font-medium">{{ user?.username }}</span></p>
        </div>
        <div class="flex flex-wrap gap-2">
            <button type="button" class="directory-secondary" @click="$router.back()"><i class="pi pi-angle-left" aria-hidden="true"></i>Back</button>
            <button type="button" class="directory-secondary" @click="$router.push({ name: 'user', params: { id } })">
            <i class="pi pi-pencil text-xs" aria-hidden="true"></i>Edit user
            </button>
        </div>
        </div>

        <div v-if="loading" class="text-gray-500">Loading...</div>

        <RuleManager v-else :user-id="id" :user-name="user?.username" :key="id" />
    </div>
</template>

<style scoped></style>
