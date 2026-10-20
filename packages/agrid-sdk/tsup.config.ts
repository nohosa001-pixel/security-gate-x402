import { defineConfig } from "tsup";

export default defineConfig({
  entry: {
    index: "src/index.ts",
    "security/index": "src/security/index.ts",
    "cleanweb/index": "src/cleanweb/index.ts",
    "minerals/index": "src/minerals/index.ts"
  },
  outDir: "dist",
  format: ["esm"],
  dts: true,
  clean: true,
  sourcemap: true,
  target: "es2022",
  splitting: false,
  treeshake: true,
  external: [
    "@elizaos/core",
    "@elizaos/agent",
    "@safe-global/protocol-kit",
    "viem",
    "node:crypto",
    "node:events",
    "node:fs",
    "node:path",
    "node:os",
    "node:buffer"
  ],
});
