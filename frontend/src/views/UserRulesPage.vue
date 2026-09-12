<script setup lang="ts">
import { ref, onMounted } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";
import { useToast } from "primevue/usetoast";
import type { User } from "../types/user";
import { UserAPI } from "../types/user";
import RuleManager from "../components/RuleManager.vue";
import "../assets/directory.css";
import "../assets/settings.css";

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
    <main class="directory-page" aria-labelledby="access-title">
        <nav class="settings-breadcrumb" aria-label="Breadcrumb">
            <RouterLink :to="{ name: 'users' }">Users</RouterLink>
            <i class="pi pi-angle-right text-[10px]" aria-hidden="true"></i>
            <span aria-current="page">Access rules</span>
        </nav>

        <header class="settings-header">
            <div class="settings-identity w-full sm:w-auto sm:flex-1">
                <span class="settings-avatar access-avatar relative" aria-hidden="true">
                    <template v-if="user">{{ user.username.slice(0, 2).toUpperCase() }}</template>
                    <i v-else class="pi pi-user"></i>
                    <span class="absolute -bottom-2 -right-2 flex h-8 w-8 items-center justify-center rounded-xl border-2 border-white bg-orange-200 text-orange-900"><i class="pi pi-shield text-sm"></i></span>
                </span>
                <div class="min-w-0">
                    <h1 id="access-title" class="directory-title break-words">{{ user?.username || 'Access rules' }}</h1>
                    <p class="directory-subtitle">Database permissions, row filters and column transformations.</p>
                </div>
            </div>
            <RouterLink v-if="user" :to="{ name: 'user', params: { id } }" class="directory-secondary shrink-0">
                <i class="pi pi-pencil text-xs" aria-hidden="true"></i>Edit user
            </RouterLink>
        </header>

        <div v-if="loading" class="text-gray-500">Loading...</div>

        <RuleManager v-else :user-id="id" :user-name="user?.username" :key="id" />
    </main>
</template>

<style scoped>
.access-avatar { @apply h-16 w-16; }
</style>
