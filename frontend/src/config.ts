// This file is REPLACED at deploy time (see .github/workflows/deploy-reusable.yml): public/js/config.js is
// written with the AWS data. To run locally, use local/server.py, which answers its own config.js
// pointing at itself, with `skipLogin: true` (no Cognito, in-memory API; local use only).
export interface Config { region: string; clientId: string; apiUrl: string; skipLogin?: boolean }

export const CONFIG: Config = { region: "", clientId: "", apiUrl: "" };
