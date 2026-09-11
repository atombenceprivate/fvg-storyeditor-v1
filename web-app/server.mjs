import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { extname, join, normalize } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(fileURLToPath(new URL(".", import.meta.url)), "public");
const mime = { ".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8", ".json": "application/json; charset=utf-8" };
const port = Number(process.env.PORT || 4173);

createServer(async (request, response) => {
  const pathname = request.url?.split("?")[0] || "/";
  const relative = pathname === "/" ? "index.html" : pathname.replace(/^\/+/, "");
  const target = normalize(join(root, relative));
  if (!target.startsWith(root)) { response.writeHead(403); response.end("Forbidden"); return; }
  try {
    response.writeHead(200, { "Content-Type": mime[extname(target)] || "application/octet-stream", "Cache-Control": "no-store" });
    response.end(await readFile(target));
  } catch {
    response.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" }); response.end("Not found");
  }
}).listen(port, "127.0.0.1", () => console.log(`FVG Story Editor web: http://127.0.0.1:${port}`));
