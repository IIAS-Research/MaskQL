<script setup lang="ts">
import { computed, ref } from "vue";
import type { User, UserCreate } from "../types/user";
import "../assets/directory.css";
import "../assets/settings.css";

const props = withDefaults(defineProps<{
  modelValue: UserCreate | User;
  saving?: boolean;
  mode?: "create" | "edit";
  error?: string;
}>(), {
  saving: false,
  mode: "create",
  error: "",
});

const emit = defineEmits<{
  (e: "update:modelValue", value: UserCreate | User): void;
  (e: "submit", value: UserCreate | User): void;
  (e: "cancel"): void;
}>();

const username = computed({
  get: () => props.modelValue.username,
  set: (value: string) => emit("update:modelValue", { ...props.modelValue, username: value }),
});
const password = computed({
  get: () => props.modelValue.password,
  set: (value: string) => emit("update:modelValue", { ...props.modelValue, password: value }),
});
const showPassword = ref(false);
const errors = ref<{ username?: string; password?: string }>({});

function onSubmit() {
  if (props.saving) return;
  errors.value = {};
  if (!username.value.trim()) errors.value.username = "Enter a username.";
  if (props.mode === "create" && !password.value) errors.value.password = "Enter a password.";
  if (Object.keys(errors.value).length) return;
  emit("submit", { ...props.modelValue });
}
</script>

<template>
  <form class="directory-panel settings-form" :aria-busy="saving" novalidate @submit.prevent="onSubmit">
    <section class="settings-section" aria-labelledby="user-account-heading">
      <div class="settings-section-heading">
        <h2 id="user-account-heading">
          <i class="pi pi-user" aria-hidden="true"></i>Account details
        </h2>
        <p class="settings-hint">Used to sign in to MaskQL.</p>
      </div>
      <div class="min-w-0">
        <label for="user-username" class="settings-label">Username</label>
        <input
          id="user-username"
          v-model="username"
          name="username"
          type="text"
          autocomplete="username"
          class="settings-input"
          :disabled="saving"
          :aria-invalid="!!errors.username"
          :aria-describedby="errors.username ? 'user-username-error' : undefined"
          required
          @input="errors.username = undefined"
        />
        <p v-if="errors.username" id="user-username-error" class="settings-field-error" role="alert">{{ errors.username }}</p>
      </div>
    </section>

    <section class="settings-section" aria-labelledby="user-password-heading">
      <div class="settings-section-heading">
        <h2 id="user-password-heading">
          <i class="pi pi-lock" aria-hidden="true"></i>Password
        </h2>
      </div>
      <div class="min-w-0">
        <label for="user-password" class="settings-label">
          {{ mode === 'edit' ? 'New password' : 'Password' }}
          <span v-if="mode === 'edit'" class="ml-2 text-xs font-normal text-slate-400">Optional</span>
        </label>
        <div class="settings-password">
          <input
            id="user-password"
            v-model="password"
            name="password"
            :type="showPassword ? 'text' : 'password'"
            autocomplete="new-password"
            class="settings-input"
            :disabled="saving"
            :required="mode === 'create'"
            :aria-invalid="!!errors.password"
            :aria-describedby="[mode === 'edit' ? 'user-password-hint' : '', errors.password ? 'user-password-error' : ''].filter(Boolean).join(' ') || undefined"
            @input="errors.password = undefined"
          />
          <button
            type="button"
            class="settings-password-toggle"
            :aria-label="showPassword ? 'Hide password' : 'Show password'"
            :aria-pressed="showPassword"
            :disabled="saving"
            @click="showPassword = !showPassword"
          >
            <i :class="showPassword ? 'pi pi-eye-slash' : 'pi pi-eye'" aria-hidden="true"></i>
          </button>
        </div>
        <p v-if="mode === 'edit'" id="user-password-hint" class="settings-hint">Leave blank to keep the current password.</p>
        <p v-if="errors.password" id="user-password-error" class="settings-field-error" role="alert">{{ errors.password }}</p>
      </div>
    </section>

    <p v-if="error" class="settings-error" role="alert">{{ error }}</p>
    <footer class="settings-footer">
      <button type="button" class="directory-secondary" :disabled="saving" @click="emit('cancel')">Cancel</button>
      <button type="submit" :disabled="saving" class="directory-primary">
        <i class="pi" :class="saving ? 'pi-spinner pi-spin' : 'pi-check'" aria-hidden="true"></i>
        {{ saving ? 'Saving...' : mode === 'create' ? 'Create user' : 'Save changes' }}
      </button>
    </footer>
  </form>
</template>
