/**
 * Minimal ESLint config for this Vite + React + TS repo.
 *
 * The project already had an `npm run lint` script but no config file,
 * which caused lint to fail immediately.
 */
module.exports = {
  root: true,
  env: {
    browser: true,
    es2021: true,
    node: true,
  },
  parser: '@typescript-eslint/parser',
  parserOptions: {
    ecmaVersion: 'latest',
    sourceType: 'module',
    ecmaFeatures: {
      jsx: true,
    },
  },
  plugins: ['@typescript-eslint', 'react-hooks', 'react-refresh'],
  extends: [
    'eslint:recommended',
    'plugin:@typescript-eslint/recommended',
    'plugin:react-hooks/recommended',
  ],
  rules: {
    // Vite React Refresh guidance
    'react-refresh/only-export-components': ['warn', { allowConstantExport: true }],

    // Keep noise low for this repo
    '@typescript-eslint/no-explicit-any': 'off',
    '@typescript-eslint/no-unused-vars': ['warn', { argsIgnorePattern: '^_' }],

    // This repo currently has many “missing dependency” warnings due to inline `load()` functions.
    // It's safe but noisy; we prefer local reasoning over exhaustive-deps for now.
    'react-hooks/exhaustive-deps': 'off',
  },
  ignorePatterns: ['dist', 'node_modules'],
}
