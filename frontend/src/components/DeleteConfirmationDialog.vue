<script setup lang="ts">
import { watch } from "vue";
import { useRoute } from "vue-router";
import ConfirmDialog from "primevue/confirmdialog";
import { useConfirm } from "primevue/useconfirm";
import { clearConfirmationFocus, restoreConfirmationFocus } from "../composables/useDeleteConfirmation";

const route = useRoute();
const confirmation = useConfirm();
watch(() => route.fullPath, () => {
  clearConfirmationFocus();
  confirmation.close();
});
</script>

<template>
  <ConfirmDialog group="delete" :draggable="false" class="delete-confirmation" aria-describedby="delete-confirmation-message" @after-hide="restoreConfirmationFocus">
    <template #message="{ message }">
      <div class="flex items-start gap-4">
        <span class="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-red-50 text-red-600" aria-hidden="true"><i class="pi pi-trash"></i></span>
        <p id="delete-confirmation-message" class="min-w-0 text-sm leading-relaxed text-slate-600" style="overflow-wrap: anywhere">{{ message?.message }}</p>
      </div>
    </template>
  </ConfirmDialog>
</template>

<style>
.delete-confirmation.p-dialog { @apply w-[28rem] max-w-[calc(100vw-2rem)] overflow-hidden rounded-2xl border border-slate-200 shadow-xl; }
.delete-confirmation.p-dialog .p-dialog-header { @apply px-5 pb-4 pt-5; }
.delete-confirmation.p-dialog .p-dialog-title { @apply text-lg font-semibold text-slate-900; }
.delete-confirmation.p-dialog .p-dialog-header-icon { @apply h-8 w-8 rounded-lg text-slate-400 hover:bg-slate-100 hover:text-slate-700; }
.delete-confirmation.p-dialog .p-dialog-content { @apply px-5 pb-6; }
.delete-confirmation.p-dialog .p-dialog-footer { @apply flex flex-wrap justify-end gap-3 border-t border-slate-100 bg-slate-50 px-5 py-4; }
.delete-confirmation.p-dialog .p-dialog-footer .p-button { @apply m-0 rounded-lg px-3 py-2 text-sm shadow-none; }
.delete-confirmation.p-dialog .p-dialog-footer .p-button-icon { @apply hidden; }
.delete-confirmation.p-dialog .p-dialog-footer .p-button-label { @apply font-medium; }
.delete-confirmation.p-dialog .p-confirm-dialog-reject { @apply border border-slate-200 bg-white text-slate-700 hover:bg-slate-100; }
.delete-confirmation.p-dialog .p-confirm-dialog-accept { @apply border border-red-600 bg-red-600 text-white hover:border-red-700 hover:bg-red-700; }
.delete-confirmation.p-dialog .p-button:focus-visible,
.delete-confirmation.p-dialog .p-dialog-header-icon:focus-visible { @apply outline outline-2 outline-offset-2 outline-accent-600; }
</style>
