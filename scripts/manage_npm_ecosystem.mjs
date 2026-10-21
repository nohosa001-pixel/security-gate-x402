#!/usr/bin/env node
/**
 * A.GRID Master NPM Ecosystem Manager & Deployment Orchestrator
 * =============================================================
 * Systematically monitors, verifies, and orchestrates npm packages across:
 * - elizaos-plugin-security-gate (Security Gate ElizaOS Plugin)
 * - minerals-oracle-x402         (Minerals Oracle Official TypeScript SDK)
 * - agrid-sdk                    (A.GRID Master Umbrella SDK)
 * - cleanweb-eliza-plugin        (CleanWeb Intelligence ElizaOS Plugin)
 */

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { execSync } from "node:child_process";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT_DIR = path.resolve(__dirname, "..");

export const ECOSYSTEM_PACKAGES = [
  {
    id: "security-gate",
    name: "elizaos-plugin-security-gate",
    repo: "security-gate-x402",
    localPath: path.resolve(ROOT_DIR, "packages/plugin-security-gate"),
    role: "ElizaOS Security Gate Guardrails & Local Ingress Defense",
    buildCmd: "npm run build",
    testCmd: "npm test"
  },
  {
    id: "minerals-oracle",
    name: "minerals-oracle-x402",
    repo: "minerals-oracle-x402",
    localPath: path.resolve(ROOT_DIR, "../minerals-oracle-x402/sdk/typescript"),
    role: "Critical Minerals Provenance & M2M Trade Protocol SDK",
    buildCmd: "npm run build",
    testCmd: "npm test"
  },
  {
    id: "agrid-sdk",
    name: "agrid-sdk",
    repo: "security-gate-x402",
    localPath: path.resolve(ROOT_DIR, "packages/agrid-sdk"),
    role: "A.GRID Master Umbrella SDK (Security + CleanWeb + Minerals)",
    buildCmd: "npm run build",
    testCmd: "npm test"
  },
  {
    id: "cleanweb-plugin",
    name: "cleanweb-eliza-plugin",
    repo: "x402-micro-agent",
    localPath: path.resolve(ROOT_DIR, "../x402-micro-agent/packages/plugin-cleanweb"),
    role: "CleanWeb 87% Token Compression & Ground Truth Intelligence",
    buildCmd: "npm run build",
    testCmd: "node --test"
  }
];

async function fetchNpmInfo(pkgName) {
  try {
    const res = await fetch(`https://registry.npmjs.org/${pkgName}`, {
      headers: { "User-Agent": "A.GRID-Ecosystem-Manager/1.0" }
    });
    if (!res.ok) {
      return { published: false, error: `HTTP ${res.status} (${res.statusText})` };
    }
    const data = await res.json();
    const latest = data["dist-tags"]?.latest || "unknown";
    const versions = Object.keys(data.versions || {});

    // Fetch downloads
    let monthlyDownloads = 0;
    try {
      const dlRes = await fetch(`https://api.npmjs.org/downloads/point/last-month/${pkgName}`);
      if (dlRes.ok) {
        const dlData = await dlRes.json();
        monthlyDownloads = dlData.downloads || 0;
      }
    } catch {}

    return {
      published: true,
      latestVersion: latest,
      totalVersions: versions.length,
      monthlyDownloads
    };
  } catch (err) {
    return { published: false, error: err.message };
  }
}

function getLocalPackageInfo(pkg) {
  const pkgJsonPath = path.join(pkg.localPath, "package.json");
  if (!fs.existsSync(pkgJsonPath)) {
    return { exists: false, error: "package.json not found" };
  }
  try {
    const raw = fs.readFileSync(pkgJsonPath, "utf8");
    const json = JSON.parse(raw);
    const distExists = fs.existsSync(path.join(pkg.localPath, "dist"));
    return {
      exists: true,
      name: json.name,
      version: json.version,
      hasDist: distExists,
      dependencies: Object.keys(json.dependencies || {}).length,
      devDependencies: Object.keys(json.devDependencies || {}).length
    };
  } catch (err) {
    return { exists: false, error: err.message };
  }
}

export async function getEcosystemStatus() {
  const results = [];
  for (const pkg of ECOSYSTEM_PACKAGES) {
    const local = getLocalPackageInfo(pkg);
    const npm = await fetchNpmInfo(pkg.name);

    let syncStatus = "UNKNOWN";
    if (!local.exists) {
      syncStatus = "LOCAL_MISSING";
    } else if (!npm.published) {
      syncStatus = "PENDING_INITIAL_PUBLISH";
    } else if (local.version === npm.latestVersion) {
      syncStatus = "SYNCED";
    } else {
      syncStatus = "UPDATE_READY";
    }

    results.push({
      id: pkg.id,
      name: pkg.name,
      repo: pkg.repo,
      role: pkg.role,
      localVersion: local.version || "N/A",
      npmVersion: npm.latestVersion || "Not on npm",
      hasDist: local.hasDist,
      monthlyDownloads: npm.monthlyDownloads || 0,
      syncStatus
    });
  }
  return results;
}

export async function printStatusDashboard() {
  console.log("\n==========================================================================================");
  console.log(" 🌐 A.GRID Master NPM Ecosystem Status & Telemetry Dashboard");
  console.log("==========================================================================================");

  const statuses = await getEcosystemStatus();

  console.log("\n| Package Name | Repo | Local Ver | npm Live | Monthly DL | Build (dist) | Sync Status |");
  console.log("| :--- | :---: | :---: | :---: | :---: | :---: | :---: |");

  for (const s of statuses) {
    const distBadge = s.hasDist ? "✅ dist ready" : "⚠️ no dist";
    let statusBadge = s.syncStatus;
    if (s.syncStatus === "SYNCED") statusBadge = "✅ Synced (Live)";
    else if (s.syncStatus === "UPDATE_READY") statusBadge = "🚀 Update Ready";
    else if (s.syncStatus === "PENDING_INITIAL_PUBLISH") statusBadge = "⏳ Pending 1st Publish";

    console.log(`| **\`${s.name}\`** | ${s.repo} | \`v${s.localVersion}\` | \`v${s.npmVersion}\` | **${s.monthlyDownloads.toLocaleString()}** | ${distBadge} | ${statusBadge} |`);
  }

  console.log("\n==========================================================================================");
  console.log(" 🛡️ CI/CD Deployment Architecture:");
  console.log("  • security-gate-x402: .github/workflows/npm-publish.yml (elizaos-plugin-security-gate & agrid-sdk)");
  console.log("  • minerals-oracle-x402: .github/workflows/npm-publish.yml (minerals-oracle-x402)");
  console.log("  • x402-micro-agent:   .github/workflows/npm-publish.yml (cleanweb-eliza-plugin)");
  console.log("  • Provenance: All 3 repositories enforce GitHub OIDC Cryptographic Provenance");
  console.log("==========================================================================================\n");
}

export async function generateMarkdownReport() {
  const statuses = await getEcosystemStatus();
  const dateStr = new Date().toISOString().split("T")[0];

  let md = `# 🌐 A.GRID NPM Ecosystem Comprehensive Status Report\n\n`;
  md += `> **Generated on:** ${dateStr}  \n`;
  md += `> **Standard:** A.GRID AP2/1.0 Sovereign Machine-to-Machine NPM Network  \n`;
  md += `> **Architecture:** OIDC Provenance Cryptographic Publishing & Multi-Repo Master Sync\n\n`;
  md += `---\n\n`;
  md += `## 1. Live NPM Packages Matrix\n\n`;
  md += `| Package | Role | Repo | Local | npm Live | Monthly DL | Dist Status | Sync Status |\n`;
  md += `| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |\n`;

  for (const s of statuses) {
    const distBadge = s.hasDist ? "✅ Ready" : "⚠️ Missing";
    let statusBadge = s.syncStatus;
    if (s.syncStatus === "SYNCED") statusBadge = "🟢 Synced (Live)";
    else if (s.syncStatus === "UPDATE_READY") statusBadge = "🚀 Update Ready";
    else if (s.syncStatus === "PENDING_INITIAL_PUBLISH") statusBadge = "⏳ Pending 1st Publish";

    md += `| **\`${s.name}\`** | ${s.role} | \`${s.repo}\` | \`v${s.localVersion}\` | \`v${s.npmVersion}\` | **${s.monthlyDownloads.toLocaleString()}** | ${distBadge} | ${statusBadge} |\n`;
  }

  md += `\n---\n\n`;
  md += `## 2. CI/CD & Security Invariants\n\n`;
  md += `1. **Zero Secret Leakage via OIDC Provenance**:\n`;
  md += `   - All packages deploy through GitHub Actions using short-lived OpenID Connect tokens directly authenticated with npmjs.org.\n`;
  md += `2. **Safe Pre-Flight Check**:\n`;
  md += `   - Every workflow inspects \`npm view $NAME@$VERSION\` prior to running \`npm publish\` to prevent pipeline failures on non-bumped commits.\n`;
  md += `3. **A.GRID Master Umbrella Architecture**:\n`;
  md += `   - \`agrid-sdk\` aggregates all three functional domains into unified subpaths (\`agrid-sdk/security\`, \`agrid-sdk/cleanweb\`, \`agrid-sdk/minerals\`).\n`;

  const reportPath = path.resolve(ROOT_DIR, "docs/NPM_ECOSYSTEM_STATUS.md");
  fs.writeFileSync(reportPath, md, "utf8");
  console.log(`✅ Markdown report successfully generated: docs/NPM_ECOSYSTEM_STATUS.md`);
}

// CLI Command Parser
const action = process.argv[2] || "status";

if (action === "status") {
  await printStatusDashboard();
} else if (action === "report") {
  await printStatusDashboard();
  await generateMarkdownReport();
} else {
  console.log(`Usage: node scripts/manage_npm_ecosystem.mjs [status|report]`);
}
