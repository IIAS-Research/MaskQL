<script setup lang="ts">
import { RouterLink } from "vue-router";
import "../assets/directory.css";

defineProps<{ userId: number; username: string }>();
</script>

<template>
  <RouterLink :to="{ name: 'user-rules', params: { id: userId } }" :aria-label="`Manage access for ${username}`" class="directory-secondary directory-access">
    <i class="pi pi-shield" aria-hidden="true"></i>Manage access
  </RouterLink>
</template>
