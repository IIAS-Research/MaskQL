<script setup lang="ts">
import { ref } from 'vue'
// particles
import type { Engine } from 'tsparticles-engine';
import { loadFull } from 'tsparticles';
import { particlesJSConfig } from '../utils/particles';


const particlesOptions = ref(particlesJSConfig);
async function particlesInit(engine: Engine) {
    await loadFull(engine);
}
</script>

<template>
    <Particles
        id="tsparticles"
        :options="particlesOptions"
        :particlesInit="particlesInit"
    />
</template>

<style scoped>

</style>