const { createApp, reactive } = Vue;

const $root = reactive({
  showConfirm: () => {},
  showToast: () => {},
});

const app = createApp(App);

app.component("chat-page", ChatPage);
app.component("notes-page", NotesPage);
app.component("skills-page", SkillsPage);
app.component("config-page", ConfigPage);
app.component("dashboard-page", DashboardMonitor);

app.provide("$root", $root);

const vm = app.mount("#app");

vm.$options.name = "App";

window.$root = $root;

Object.keys(vm).forEach((key) => {
  if (typeof vm[key] === "function") {
    $root[key] = vm[key].bind(vm);
  } else if (key !== "$" && key !== "_") {
    try {
      Object.defineProperty($root, key, {
        get: () => vm[key],
        set: (val) => {
          vm[key] = val;
        },
        enumerable: true,
        configurable: true,
      });
    } catch (e) {}
  }
});
