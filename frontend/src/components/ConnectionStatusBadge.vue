<script setup lang="ts">
import { computed } from "vue";
import type { CatalogConnectionStatus } from "../types/catalog";

const props = defineProps<{ status?: CatalogConnectionStatus; checking?: boolean }>();
const appearance = computed(() => {
  if (props.checking) return { label: "Checking", icon: "pi-spinner pi-spin", tone: "bg-slate-100 text-slate-500" };
  if (props.status?.state === "ok") return { label: "Connected", icon: "pi-check-circle", tone: "bg-emerald-50 text-emerald-700" };
  if (props.status?.state === "error") return { label: "Failed", icon: "pi-exclamation-circle", tone: "bg-red-50 text-red-700" };
  return { label: "Unknown", icon: "pi-question-circle", tone: "bg-slate-100 text-slate-500" };
});
const title = computed(() => props.checking ? "Checking database connection" : props.status?.message || "Connection status unavailable");
</script>

<template>
  <span class="inline-flex shrink-0 items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium" :class="appearance.tone" :title="title">
    <i class="pi text-[10px]" :class="appearance.icon" aria-hidden="true"></i>{{ appearance.label }}
  </span>
</template>
