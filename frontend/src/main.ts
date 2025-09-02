import './assets/main.css'

import { createApp } from 'vue';
import { createPinia } from 'pinia';

import DataTable from 'primevue/datatable';
import Column from 'primevue/column';
import Button from 'primevue/button';

import App from './App.vue';
import router from './router';
import PrimeVue from 'primevue/config';

import 'primeicons/primeicons.css';
import 'primevue/resources/primevue.min.css';
import "primevue/resources/themes/lara-light-blue/theme.css";
import ToastService from "primevue/toastservice";
import Sidebar from 'primevue/sidebar';
import InputText from "primevue/inputtext";
import Toast from 'primevue/toast';
import axios from "axios";
import VueAxios from "vue-axios";
import Particles from "vue3-particles";

// VueTyper
import VueTyper from 'vue3-typer'
import "vue3-typer/dist/vue-typer.css"


export const app = createApp(App)

app.use(createPinia())
app.use(VueAxios, axios)
app.use(PrimeVue, { styled: true })
app.use(ToastService)
app.use(Particles);
app.use(VueTyper)

app.component("DataTable", DataTable)
app.component("Column", Column)
app.component("Button", Button)
app.component("Toast", Toast)
app.component('Sidebar', Sidebar)
app.component("InputText", InputText)
app.use(router)

app.mount('#app')
