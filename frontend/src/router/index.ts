import { createRouter, createWebHistory } from 'vue-router'
import LoginPage from '../views/LoginPage.vue';
import { getAdminHealth, adminLogout } from "../auth";
import CatalogsPage from '../views/CatalogsPage.vue';
import CatalogPage from '../views/CatalogPage.vue';
import CatalogCreatePage from '../views/CatalogCreatePage.vue';
import UserListPage from '../views/UserListPage.vue';
import UserEditPage from '../views/UserEditPage.vue';
import UserCreatePage from '../views/UserCreatePage.vue';
import UserRulesPage from '../views/UserRulesPage.vue';

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      redirect: '/catalogs'
    },
    {
      path: '/catalogs',
      name: 'catalogs',
      meta: { requiresAdmin: true },
      component: CatalogsPage,
    },
    {
      path: '/catalog/:id',
      name: 'catalog',
      meta: { requiresAdmin: true },
      component: CatalogPage,
    },
    { 
      path: '/catalogs/new',
      name: 'catalog-new',
      meta: { requiresAdmin: true },
      component: CatalogCreatePage 
    },
    {
      path: '/users',
      name: 'users',
      meta: { requiresAdmin: true },
      component: UserListPage,
    },
    {
      path: '/user/:id',
      name: 'user',
      meta: { requiresAdmin: true },
      component: UserEditPage,
    },
    {
      path: '/user/:id/rules',
      name: 'user-rules',
      meta: { requiresAdmin: true },
      component: UserRulesPage,
    },
    { 
      path: '/users/new',
      name: 'user-new',
      meta: { requiresAdmin: true },
      component: UserCreatePage 
    },
    {
      path: '/login',
      name: 'login',
      component: LoginPage
    },
    {
      path: '/logout',
      name: 'logout',
      beforeEnter: async () => {
        try {
          await adminLogout()
        } catch (e) {
          console.error("Erreur logout:", e)
        }
        return { name: 'login' }
      }
    }
  ]
})


router.beforeEach(async (to) => {
  if (!to.meta?.requiresAdmin) return true;
  try {
    await getAdminHealth();
    return true;
  } catch {
    return { name: "login", query: { redirect: to.fullPath } };
  }
});

router.afterEach((to) => {
  const base = 'MaskQL - '
  const local_title = to.meta.title
  document.title = base + (local_title ?  local_title : "Protecting Gotham's citizens... and your database.")
})


export default router
