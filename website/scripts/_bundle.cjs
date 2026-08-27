const { build } = require("esbuild");
const entry = "scripts/engine_smoke.ts";
build({
  entryPoints: [entry], bundle: true, platform: "node",
  outfile: "scripts/_smoke.cjs", format: "cjs", logLevel: "silent",
}).then(() => console.log("bundled"));
