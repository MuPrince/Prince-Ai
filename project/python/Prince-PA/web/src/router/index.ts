import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'board', component: () => import('@/views/TaskBoard.vue') },
    { path: '/tasks/:id/note', name: 'note', component: () => import('@/views/NoteEditor.vue') }
  ]
})

export default router
