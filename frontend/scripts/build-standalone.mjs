import { build } from "esbuild";
import { readFile, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";

// Vite's "?raw" imports (the shared requirement-simulator template) as plain text for esbuild.
const rawPlugin = { name: "raw", setup(b) {
  b.onResolve({ filter: /\?raw$/ }, args => ({ path: path.resolve(args.resolveDir, args.path.replace(/\?raw$/, "")), namespace: "raw" }));
  b.onLoad({ filter: /.*/, namespace: "raw" }, async args => ({ contents: await readFile(args.path, "utf8"), loader: "text" }));
} };

const frontend = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const result = await build({
  absWorkingDir: frontend, entryPoints: ["src/main.jsx"], bundle: true, write: false,
  outfile: "bundle.js", format: "iife", jsx: "automatic", minify: true, plugins: [rawPlugin],
  define: { "process.env.NODE_ENV": '"production"', "import.meta.env": JSON.stringify({ VITE_API_BASE: process.env.VITE_API_BASE || "http://localhost:8000" }) },
});
const js = result.outputFiles.find(f => f.path.endsWith(".js")).text.replace(/<\/script/gi, "<\\/script");
const css = result.outputFiles.find(f => f.path.endsWith(".css")).text;
const html = `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Vaani · Voice to action</title><style>${css}</style></head><body><div id="root"></div><script>${js}</script></body></html>\n`;
const output = path.resolve(frontend, "../vaani-prototype.html");
await writeFile(output, html);
console.log("Built standalone file from React source (" + html.length + " characters): " + output);

