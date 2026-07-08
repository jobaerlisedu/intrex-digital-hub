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
        Isotope: "readonly",
        imagesLoaded: "readonly",
        Swiper: "readonly",
        GLightbox: "readonly",
        AOS: "readonly",
        PureCounter: "readonly",
        toggleDropdown: "readonly",
        initPagination: "readonly",
        initSearchFilter: "readonly",
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
