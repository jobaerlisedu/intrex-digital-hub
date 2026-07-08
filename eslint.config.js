import js from "@eslint/js";
import globals from "globals";

export default [
  js.configs.recommended,
  {
    languageOptions: {
      ecmaVersion: "latest",
      sourceType: "module",
      globals: {
        ...globals.browser,
        ...globals.es2021,
      },
    },
    rules: {
      "no-unused-vars": ["warn", { args: "none" }],
      "no-console": "off",
      "prefer-const": "warn",
      "no-var": "off",
    },
  },
  {
    files: ["static/js/*.js"],
    languageOptions: {
      sourceType: "script",
    },
  },
  {
    ignores: [
      "static/vendors/",
      "static/dist/",
      "node_modules/",
      "staticfiles/",
    ],
  },
];
