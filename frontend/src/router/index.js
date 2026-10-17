import { createMemoryHistory, createRouter, createWebHistory } from 'vue-router'
import HomePage from '../pages/HomePage.vue'
import ProductPage from '../pages/ProductPage.vue'
import CheckoutPage from '../pages/CheckoutPage.vue'
import LoginPage from '../pages/LoginPage.vue'
import AdminDashboardPage from '../pages/admin/AdminDashboardPage.vue'
import AdminOrdersPage from '../pages/admin/AdminOrdersPage.vue'
import AdminOrderPage from '../pages/admin/AdminOrderPage.vue'
import AdminOrderCreatePage from '../pages/admin/AdminOrderCreatePage.vue'
import AdminCustomersPage from '../pages/admin/AdminCustomersPage.vue'
import AdminProductsPage from '../pages/admin/AdminProductsPage.vue'
import AdminCategoriesPage from '../pages/admin/AdminCategoriesPage.vue'
import AdminProductEditorPage from '../pages/admin/AdminProductEditorPage.vue'
import AdminSettingsPage from '../pages/admin/AdminSettingsPage.vue'
import AdminStorefrontPage from '../pages/admin/AdminStorefrontPage.vue'
import AdminIconsPage from '../pages/admin/AdminIconsPage.vue'
import AdminUsersPage from '../pages/admin/AdminUsersPage.vue'
import AdminLogsPage from '../pages/admin/AdminLogsPage.vue'
import AdminAboutPage from '../pages/admin/AdminAboutPage.vue'
import NotFoundPage from '../pages/NotFoundPage.vue'
import InstallPage from '../pages/InstallPage.vue'

export function createAppRouter() {
  return createRouter({
    history: import.meta.env.SSR ? createMemoryHistory() : createWebHistory(),
    routes: [
      { path: '/install', name: 'install', component: InstallPage, meta: { layout: 'installer', public: true, noindex: true } },
      { path: '/', name: 'home', component: HomePage, meta: { layout: 'store', public: true } },
      { path: '/product/:slug', name: 'product', component: ProductPage, meta: { layout: 'store', public: true } },
      { path: '/checkout/:slug', name: 'checkout', component: CheckoutPage, meta: { layout: 'store', public: true, noindex: true } },
      { path: '/login', name: 'login', component: LoginPage, meta: { layout: 'auth', public: true, noindex: true } },
      { path: '/admin', name: 'admin-dashboard', component: AdminDashboardPage, meta: { layout: 'admin', auth: true, noindex: true } },
      { path: '/admin/orders', name: 'admin-orders', component: AdminOrdersPage, meta: { layout: 'admin', auth: true, noindex: true } },
      { path: '/admin/orders/new', name: 'admin-order-new', component: AdminOrderCreatePage, meta: { layout: 'admin', auth: true, noindex: true } },
      { path: '/admin/orders/:id', name: 'admin-order', component: AdminOrderPage, meta: { layout: 'admin', auth: true, noindex: true } },
      { path: '/admin/customers', name: 'admin-customers', component: AdminCustomersPage, meta: { layout: 'admin', auth: true, noindex: true } },
      { path: '/admin/products', name: 'admin-products', component: AdminProductsPage, meta: { layout: 'admin', auth: true, noindex: true } },
      { path: '/admin/categories', name: 'admin-categories', component: AdminCategoriesPage, meta: { layout: 'admin', auth: true, noindex: true } },
      { path: '/admin/products/new', name: 'admin-product-new', component: AdminProductEditorPage, meta: { layout: 'admin', auth: true, noindex: true } },
      { path: '/admin/products/:id', name: 'admin-product-edit', component: AdminProductEditorPage, meta: { layout: 'admin', auth: true, noindex: true } },
      { path: '/admin/storefront', name: 'admin-storefront', component: AdminStorefrontPage, meta: { layout: 'admin', auth: true, adminOnly: true, noindex: true } },
      { path: '/admin/settings', name: 'admin-settings', component: AdminSettingsPage, meta: { layout: 'admin', auth: true, adminOnly: true, noindex: true } },
      { path: '/admin/icons', name: 'admin-icons', component: AdminIconsPage, meta: { layout: 'admin', auth: true, adminOnly: true, noindex: true } },
      { path: '/admin/users', name: 'admin-users', component: AdminUsersPage, meta: { layout: 'admin', auth: true, adminOnly: true, noindex: true } },
      { path: '/admin/logs', name: 'admin-logs', component: AdminLogsPage, meta: { layout: 'admin', auth: true, adminOnly: true, noindex: true } },
      { path: '/admin/about', name: 'admin-about', component: AdminAboutPage, meta: { layout: 'admin', auth: true, adminOnly: true, noindex: true } },
      { path: '/:pathMatch(.*)*', name: 'not-found', component: NotFoundPage, meta: { layout: 'store', public: true, noindex: true } }
    ],
    scrollBehavior(to, from, savedPosition) {
      if (savedPosition) return savedPosition
      if (to.hash) return { el: to.hash, behavior: 'smooth', top: 110 }
      return { top: 0 }
    }
  })
}
