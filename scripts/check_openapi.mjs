import {readFileSync} from "node:fs";
import {spawnSync} from "node:child_process";
const paths = ["openapi.json", "lib/api/schema.d.ts"];
const before = paths.map((path) => readFileSync(path, "utf8"));
const npm = process.platform === "win32" ? "npm.cmd" : "npm";
for (const script of ["api:export", "api:generate"]) {
  const result = spawnSync(npm, ["run", script], {stdio: "inherit", shell: process.platform === "win32"});
  if (result.status !== 0) process.exit(result.status ?? 1);
}
const after = paths.map((path) => readFileSync(path, "utf8"));
if (before.some((value, i) => value.replace(/\r\n/g,"\n") !== after[i].replace(/\r\n/g,"\n"))) {
  console.error("OpenAPI artifacts changed; review the generated contract and run this check again.");
  process.exit(1);
}
console.log("OpenAPI artifacts are synchronized.");
