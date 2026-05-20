/** @type {import("stylelint").Config} */
export default {
  extends: ["stylelint-config-standard"],
  rules: {
    // Django templates / legacy class names use single-word or BEM-like blocks; keep readable.
    "selector-class-pattern": null,
  },
};
