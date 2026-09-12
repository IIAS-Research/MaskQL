<script setup lang="ts">
import { RouterLink, useRoute, useRouter } from 'vue-router'

const router = useRouter();
const route = useRoute();

const menuItems = [
    { label: "Home", icon: "pi pi-home", route: "/", activeNames: ["home"] },
    { label: "Users", icon: "pi pi-user", route: "/users", activeNames: ["users", "user", "user-new", "user-rules"] },
    { label: "Databases", icon: "pi pi-book", route: "/catalogs", activeNames: ["catalogs", "catalog", "catalog-new"] }
];

function isActive(item: typeof menuItems[number]) {
    return item.activeNames.includes(String(route.name));
}
</script>

<template>
    <aside class="flex flex-col h-screen w-16 shrink-0 bg-accent-900 text-white items-center justify-between py-4">
    <div class="group relative">
        <RouterLink to="/" aria-label="MaskQL home" class="block rounded-lg focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white">
            <img src="/images/maskql_logo.svg" alt="" class="w-10 h-10" />
        </RouterLink>
        <span
            aria-hidden="true"
            class="pointer-events-none absolute left-14 top-1/2 z-50 -translate-y-1/2 px-2 py-1 text-sm bg-accent-800 text-white rounded-md opacity-0 group-hover:opacity-100 group-focus-within:opacity-100 whitespace-nowrap"
            >
            MaskQL
        </span>
    </div>

    <nav aria-label="Main navigation" class="flex flex-col gap-6">
        <div v-for="item in menuItems" :key="item.label" class="group relative">
            <RouterLink
            :to="item.route"
            :aria-label="item.label"
            :aria-current="isActive(item) ? 'page' : undefined"
            class="p-3 rounded-xl flex items-center justify-center focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
            :class="isActive(item) ? 'bg-brand-600 text-white hover:bg-brand-700' : 'hover:bg-accent-800'"
            >
            <i :class="item.icon" aria-hidden="true"></i>
            </RouterLink>
            <span
            aria-hidden="true"
            class="pointer-events-none absolute left-14 top-1/2 z-50 -translate-y-1/2 px-2 py-1 text-sm bg-accent-800 text-white rounded-md opacity-0 group-hover:opacity-100 group-focus-within:opacity-100 whitespace-nowrap"
            >
            {{ item.label }}
            </span>
        </div>
    </nav>

    <div class="group relative">
        <button
            type="button"
            aria-label="Logout"
            class="p-3 rounded-xl hover:bg-red-600 flex items-center justify-center focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
            @click="router.push('/logout')"
        >
            <i class="pi pi-sign-out" aria-hidden="true"></i>
        </button>
        <span
            aria-hidden="true"
            class="pointer-events-none absolute left-14 top-1/2 z-50 -translate-y-1/2 px-2 py-1 text-sm bg-accent-800 text-white rounded-md opacity-0 group-hover:opacity-100 group-focus-within:opacity-100 whitespace-nowrap"
        >
            Logout
        </span>
        </div>
    </aside>
</template>

<style>
@import "primeicons/primeicons.css";
</style>
