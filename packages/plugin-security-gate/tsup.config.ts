import { defineConfig } from "tsup";

export default defineConfig({
	entry: ["src/index.ts"],
	outDir: "dist",
	sourcemap: true,
	clean: true,
	format: ["esm"],
	dts: true,
	external: ["@elizaos/core", "@safe-global/protocol-kit", "viem", "node:crypto", "node:events"],
});
