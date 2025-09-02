<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useToast } from "primevue/usetoast";
import type { User } from "../types/user";
import { UserAPI } from "../types/user";
import RuleManager from "../components/RuleManager.vue";

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
    <div class="p-6 max-w-6xl mx-auto space-y-6">
        <div class="flex items-center justify-between">
        <div>
            <h1 class="text-2xl font-bold text-gray-800">Manage user access</h1>
            <p class="text-gray-500">User : <span class="font-medium">{{ user?.username }}</span> (ID {{ user?.id }})</p>
        </div>
        <div class="flex gap-2">
            <button class="px-3 py-2 border rounded-lg hover:bg-gray-50" @click="$router.back()">Back</button>
            <button class="px-3 py-2 bg-gray-800 text-white rounded-lg hover:bg-gray-700" @click="$router.push({ name: 'user-edit', params: { id } })">
            Edit profil
            </button>
        </div>
        </div>

        <div v-if="loading" class="text-gray-500">Loading...</div>

        <RuleManager v-else :user-id="id" :key="id" />
    </div>
</template>

<style scoped></style>
