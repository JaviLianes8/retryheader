// Captures the rate limit headers that express-rate-limit sends from a real HTTP server.
// Run from a folder with `npm install express express-rate-limit`:
//   node capture_express_rate_limit.js
// tests/test_real_server.py holds the output of one run.
const http = require("http");
const express = require("express");
const { rateLimit } = require("express-rate-limit");
const out = [];
async function run(draft, limit, windowMs, extra) {
  const app = express();
  app.use(rateLimit({ windowMs, limit, standardHeaders: draft, legacyHeaders: false, ...extra }));
  app.get("/", (req, res) => res.send("ok"));
  const server = http.createServer(app);
  await new Promise((r) => server.listen(0, "127.0.0.1", r));
  const port = server.address().port;
  for (let i = 0; i < limit + 2; i++) {
    const res = await fetch(`http://127.0.0.1:${port}/`);
    await res.text();
    const h = {};
    for (const [k, v] of res.headers) if (/^(ratelimit|retry-after)/i.test(k)) h[k] = v;
    out.push({ draft, limit, windowMs, status: res.status, headers: h });
  }
  server.close();
}
(async () => {
  await run("draft-8", 3, 60000, {});
  await run("draft-8", 2, 3600000, { identifier: "hourly" });
  await run("draft-7", 2, 60000, {});
  await run("draft-6", 2, 60000, {});
  for (const o of out) console.log(JSON.stringify(o));
})();
