<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter();

const menuItems = [
    { label: "Databases", icon: "pi pi-book", route: "/catalogs" },
    { label: "Users", icon: "pi pi-user", route: "/users" }
];

const goTo = (path: string) => {
    router.push(path);
}
</script>

<template>
    <div class="flex flex-col h-screen w-16 bg-gray-900 text-white items-center justify-between py-4">
    <div class="group relative">
        <img src="/images/maskql_logo.svg" alt="Logo" class="w-10 h-10" />
        <span
            class="absolute left-14 top-1/2 -translate-y-1/2 px-2 py-1 text-sm bg-gray-800 text-white rounded-md opacity-0 group-hover:opacity-100 whitespace-nowrap"
            >
            MaskQL
        </span>
    </div>

    <div class="flex flex-col gap-6">
        <div v-for="item in menuItems" :key="item.label" class="group relative">
            <button
            @click="goTo(item.route)"
            class="p-3 rounded-xl hover:bg-gray-700 flex items-center justify-center"
            >
            <i :class="item.icon"></i>
            </button>
            <span
            class="absolute left-14 top-1/2 -translate-y-1/2 px-2 py-1 text-sm bg-gray-800 text-white rounded-md opacity-0 group-hover:opacity-100 whitespace-nowrap"
            >
            {{ item.label }}
            </span>
        </div>
    </div>

    <div class="group relative">
        <button
            class="p-3 rounded-xl hover:bg-red-600 flex items-center justify-center"
            @click="router.push('/logout')"
        >
            <i class="pi pi-sign-out"></i>
        </button>
        <span
            class="absolute left-14 top-1/2 -translate-y-1/2 px-2 py-1 text-sm bg-gray-800 text-white rounded-md opacity-0 group-hover:opacity-100 whitespace-nowrap"
        >
            Logout
        </span>
        </div>
    </div>
</template>

<style>
@import "primeicons/primeicons.css";
</style>
