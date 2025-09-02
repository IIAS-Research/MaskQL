<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import { useToast } from "primevue/usetoast";
import type { User } from "../types/user";
import { UserAPI } from "../types/user";

const router = useRouter();
const toast = useToast();

const loading = ref(false);
const users = ref<User[]>([]);
const q = ref("");

const filtered = computed(() => {
    const term = q.value.trim().toLowerCase();
    if (!term) return users.value;
    return users.value.filter(u => (u.username || "").toLowerCase().includes(term));
});

async function fetchUsers() {
    loading.value = true;
    try {
        users.value = await UserAPI.list();
    } catch (e) {
        console.error(e);
        toast.add({ severity: "error", summary: "Error", detail: "Unable to load users", life: 3000 });
    } finally {
        loading.value = false;
    }
}

async function removeUser(id: number) {
    const ok = window.confirm("Deleted this user ?");
    if (!ok) return;

    try {
        await UserAPI.remove(id);
        users.value = users.value.filter(u => u.id !== id);
        toast.add({ severity: "success", summary: "Deleted", detail: "User deleted", life: 2000 });
    } catch (e) {
        console.error(e);
        toast.add({ severity: "error", summary: "Error", detail: "Unable to delete user", life: 3000 });
    }
}

function goEdit(id: number) {
    router.push({ name: "user", params: { id } });
}

function goRules(id: number) {
    router.push({ name: "user-rules", params: { id } });
}

onMounted(fetchUsers);
</script>

<template>
    <div class="p-6 max-w-4xl mx-auto">
        <div class="flex items-center justify-between mb-6">
        <h1 class="text-2xl font-bold text-gray-800">Users</h1>
        <div class="flex gap-2">
            <input
            v-model="q"
            type="search"
            placeholder="Search"
            class="px-3 py-2 border rounded-lg focus:ring focus:outline-none"
            />
            <RouterLink
            :to="{ name: 'user-new' }"
            class="px-3 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
            >
            Create user
            </RouterLink>
        </div>
        </div>

        <div class="overflow-x-auto bg-white rounded-2xl shadow">
        <table class="min-w-full text-sm">
            <thead>
            <tr class="text-left border-b">
                <th class="px-4 py-3">Username</th>
                <th class="px-4 py-3">Actions</th>
            </tr>
            </thead>
            <tbody>
            <tr v-if="loading">
                <td class="px-4 py-4 text-gray-500" colspan="2">Loading...</td>
            </tr>

            <tr v-else-if="!filtered.length">
                <td class="px-4 py-4 text-gray-500" colspan="2">No results</td>
            </tr>

            <tr v-for="u in filtered" :key="u.id" class="border-b hover:bg-gray-50">
                <td class="px-4 py-3 font-medium">{{ u.username }}</td>
                <td class="px-4 py-3">
                <div class="flex gap-2">
                    <button
                    class="px-3 py-1 rounded-lg bg-sky-600 text-white hover:bg-sky-700"
                    @click="goRules(u.id)"
                    title="Gérer les droits"
                    >
                    Manage access
                    </button>
                    <button
                    class="px-3 py-1 rounded-lg bg-gray-800 text-white hover:bg-gray-700"
                    @click="goEdit(u.id)"
                    title="Modifier"
                    >
                    Edit
                    </button>
                    <button
                    class="px-3 py-1 rounded-lg bg-red-600 text-white hover:bg-red-700"
                    @click="removeUser(u.id)"
                    title="Supprimer"
                    >
                    Delete
                    </button>
                </div>
                </td>
            </tr>
            </tbody>
        </table>
        </div>
    </div>
</template>

<style scoped></style>
