// eslint-config-next@16.3.5 exports a native ESLint flat-config array directly (no legacy
// `.eslintrc`-style shareable config needing the `@eslint/eslintrc` FlatCompat shim) - using it
// directly avoids a real, reproduced crash in that shim's schema-error formatter (a circular
// self-reference inside eslint-plugin-react's own flat config export made
// `@eslint/eslintrc`'s `ConfigValidator.formatErrors` throw trying to JSON.stringify it).
import nextConfig from "eslint-config-next";

const eslintConfig = [
  ...nextConfig,
  {
    ignores: [".next/**", "node_modules/**"],
  },
];

export default eslintConfig;
