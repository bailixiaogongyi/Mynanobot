import { createRouter, createWebHistory } from "vue-router";

const routes = [
  {
    path: "/",
    redirect: "/chat",
  },
  {
    path: "/",
    component: () => import("@/components/layout/AppLayout.vue"),
    children: [
      {
        path: "chat",
        name: "chat",
        component: () => import("@/components/chat/ChatPage.vue"),
        meta: { title: "AI助手" },
      },
      {
        path: "tasks",
        name: "tasks",
        component: () => import("@/components/tasks/TasksPage.vue"),
        meta: { title: "任务" },
      },
      {
        path: "notes",
        name: "notes",
        component: () => import("@/components/notes/NotesPage.vue"),
        meta: { title: "笔记" },
      },
      {
        path: "skills",
        name: "skills",
        component: () => import("@/components/skills/SkillsPage.vue"),
        meta: { title: "技能" },
      },
      {
        path: "config/:section?",
        name: "config",
        component: () => import("@/components/config/ConfigPage.vue"),
        meta: { title: "配置" },
      },
      {
        path: "upload",
        name: "upload",
        component: () => import("@/components/upload/UploadPage.vue"),
        meta: { title: "文件上传" },
      },
    ],
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.beforeEach((to, _from, next) => {
  document.title = `${to.meta.title || "AiMate"} - AiMate`;
  next();
});

export default router;
