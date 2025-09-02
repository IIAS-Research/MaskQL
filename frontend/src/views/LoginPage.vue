<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { useToast } from "primevue/usetoast";
import { adminLogin } from "../auth"; 

const username = ref("");
const password = ref("");
const loading = ref(false);

const toast = useToast();
const router = useRouter();

async function handleLogin() {
  if (!username.value || !password.value) {
    toast.add({ severity: "warn", summary: "Erreur", detail: "Veuillez remplir tous les champs.", life: 3000 });
    return;
  }

  loading.value = true;
  try {
    await adminLogin(username.value, password.value);
    toast.add({ severity: "success", summary: "Connexion réussie", detail: "Bienvenue !", life: 2000 });
    router.push("/");
  } catch (err) {
    toast.add({ severity: "error", summary: "Échec", detail: "Identifiants invalides.", life: 3000 });
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div class="flex items-center justify-center min-h-screen">
    <div class="w-full max-w-md p-8 bg-white rounded-2xl shadow-lg">
        <img src="/images/maskql_logo.svg" alt="Logo" class="block mx-auto w-[85px] h-[85px] object-contain" />
        <h1 class="text-2xl font-bold text-center text-gray-800 mt-1">MaskQL</h1>
        <h2 class="text-l italic text-center text-gray-800 mb-6">Protecting Gotham's citizens... and your database.</h2>

      <div class="mb-4">
        <label class="block text-gray-700 mb-1">Username</label>
        <input
          v-model="username"
          type="text"
          placeholder="theDarkKnight"
          class="w-full px-4 py-2 border rounded-lg focus:ring focus:ring-indigo-300 focus:outline-none"
        />
      </div>

      <div class="mb-6">
        <label class="block text-gray-700 mb-1">Password</label>
        <input
          v-model="password"
          type="password"
          placeholder="••••••••"
          class="w-full px-4 py-2 border rounded-lg focus:ring focus:ring-indigo-300 focus:outline-none"
          @keyup.enter="handleLogin"
        />
      </div>

      <!-- Button -->
      <button
        @click="handleLogin"
        :disabled="loading"
        class="w-full py-2 px-4 bg-[#6EC384] text-white font-semibold rounded-lg shadow hover:bg-[#61D07D] disabled:opacity-50"
      >
        <span v-if="!loading">Login</span>
        <span v-else>Loading...</span>
      </button>
    </div>
  </div>
</template>

<style scoped>
</style>
