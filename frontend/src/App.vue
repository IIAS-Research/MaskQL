<script setup lang="ts">
import { RouterView } from 'vue-router'
import { useRoute } from 'vue-router'
import CustomParticules from './components/CustomParticules.vue'
import MainSidebar from './components/MainSidebar.vue'

const route = useRoute()
</script>

<template>
  <div class="min-h-screen flex">
    <MainSidebar
      v-if="route.path !== '/login'"
      class="flex-none border-r box-border sticky top-0 h-screen"
    />

    <div class="flex-1 relative overflow-hidden">
      <Toast />
      <RouterView />
      <img
        id="watermark_iias"
        class="fixed inset-auto bottom-4 right-4 opacity-80 pointer-events-none"
        src="/images/IIAS_MINIATURE.png"
      />
      <CustomParticules />
    </div>
  </div>
</template>

<style scoped>
#watermark_iias {
  height: 50px;
  right: 20px;
  bottom: 20px;
}
</style>
