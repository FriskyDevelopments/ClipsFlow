import http from "node:http";

const port = Number(process.env.BRIDGE_PORT ?? "8088");
const target = process.env.BRIDGE_TARGET ?? "http://127.0.0.1:3000";

function sendJson(res, statusCode, data) {
  res.writeHead(statusCode, {
    "content-type": "application/json; charset=utf-8",
    "cache-control": "no-store",
  });
  res.end(JSON.stringify(data, null, 2));
}

async function proxyRequest(req, res) {
  const targetUrl = new URL(req.url ?? "/", target);
  const headers = new Headers(req.headers);
  headers.delete("host");
  headers.delete("connection");
  headers.delete("content-length");

  const chunks = [];
  for await (const chunk of req) {
    chunks.push(chunk);
  }
  const body = chunks.length > 0 ? Buffer.concat(chunks) : undefined;

  const upstream = await fetch(targetUrl, {
    method: req.method,
    headers,
    body: req.method === "GET" || req.method === "HEAD" ? undefined : body,
    redirect: "manual",
  });

  res.writeHead(upstream.status, Object.fromEntries(upstream.headers));
  if (req.method === "HEAD") {
    res.end();
    return;
  }

  const responseBody = Buffer.from(await upstream.arrayBuffer());
  res.end(responseBody);
}

const server = http.createServer(async (req, res) => {
  try {
    const path = new URL(req.url ?? "/", "http://clipsflow.bridge").pathname;

    if (path === "/bridge") {
      sendJson(res, 200, {
        ok: true,
        bridge: "clipsflow-ngrok-proxy",
        target,
        routes: {
          miniapp: "/miniapp",
          billingCheckout: "/api/billing/checkout",
          stripeWebhook: "/api/stripe/webhook",
        },
      });
      return;
    }

    await proxyRequest(req, res);
  } catch (err) {
    sendJson(res, 502, {
      error: "bridge_proxy_failed",
      message: err instanceof Error ? err.message : "Unknown bridge error",
    });
  }
});

server.listen(port, () => {
  console.log(`ClipsFlow ngrok proxy listening on http://127.0.0.1:${port}`);
  console.log(`Proxy target: ${target}`);
});
