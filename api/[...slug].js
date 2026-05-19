import crypto from "node:crypto";
import { SERVICES, ORDER_STATUSES } from "../lib/services.js";
import { loadStore, saveStore } from "../lib/store.js";

const ADMIN_USERNAME = process.env.BAKRA_ADMIN_USERNAME || "BakraSellers";
const ADMIN_PASSWORD_HASH =
  process.env.BAKRA_ADMIN_PASSWORD_HASH ||
  "VIbN9t9+aI1AeREVEPJ05PnEoJli2fdWpB3zATvkUhU=";
const ADMIN_SALT = Buffer.from("bakra-bazaar-admin-v1");
const SESSION_COOKIE = "bb_session";
const SESSION_TTL_MS = 8 * 60 * 60 * 1000;

const sessions = new Map();

function json(res, status, payload, headers = {}) {
  res.statusCode = status;
  res.setHeader("Content-Type", "application/json; charset=utf-8");
  res.setHeader("Cache-Control", "no-store");
  for (const [k, v] of Object.entries(headers)) res.setHeader(k, v);
  res.end(JSON.stringify(payload));
}

async function readJson(req) {
  const chunks = [];
  for await (const chunk of req) chunks.push(chunk);
  const body = Buffer.concat(chunks).toString("utf8");
  return body ? JSON.parse(body) : {};
}

function cleanText(value, fallback = "") {
  if (value == null) return fallback;
  return String(value).trim();
}

function cleanPrice(value) {
  const price = Number.parseInt(value, 10);
  if (!Number.isFinite(price) || price < 0 || price > 10_000_000) return null;
  return price;
}

function makeOrderId() {
  const stamp = new Date().toISOString().slice(0, 10).replace(/-/g, "");
  return `BB-${stamp}-${crypto.randomBytes(3).toString("hex").toUpperCase()}`;
}

function orderPublic(order) {
  return {
    order_id: order.order_id,
    goat_id: order.goat_id,
    goat_name: order.goat_name,
    goat_breed: order.goat_breed,
    goat_img: order.goat_img,
    service: order.service,
    total_price: order.total_price,
    customer_name: order.customer_name,
    phone: order.phone,
    address: order.address,
    notes: order.notes,
    status: order.status,
    history: order.history,
    created_at: order.created_at,
    updated_at: order.updated_at,
  };
}

function parseCookies(header = "") {
  return Object.fromEntries(
    header
      .split(";")
      .map((part) => part.trim().split("="))
      .filter(([k]) => k)
      .map(([k, ...v]) => [k, decodeURIComponent(v.join("="))]),
  );
}

async function checkPassword(password) {
  const expected = Buffer.from(ADMIN_PASSWORD_HASH, "base64");
  const actual = crypto.pbkdf2Sync(password, ADMIN_SALT, 200_000, 32, "sha256");
  return crypto.timingSafeEqual(expected, actual);
}

function currentAdmin(req) {
  const sid = parseCookies(req.headers.cookie || "")[SESSION_COOKIE];
  if (!sid) return null;
  const session = sessions.get(sid);
  if (!session || session.expires_at < Date.now()) {
    sessions.delete(sid);
    return null;
  }
  session.expires_at = Date.now() + SESSION_TTL_MS;
  return session;
}

function requireAdmin(req, res) {
  if (currentAdmin(req)) return true;
  json(res, 401, { error: "Admin login required" });
  return false;
}

export default async function handler(req, res) {
  const slug = Array.isArray(req.query.slug)
    ? req.query.slug
    : req.query.slug
      ? [req.query.slug]
      : [];
  const path = "/" + slug.join("/");

  try {
    if (req.method === "GET" && path === "/goats") {
      const store = await loadStore();
      return json(res, 200, {
        goats: store.goats || [],
        breeds: store.breeds || [],
        services: Object.values(SERVICES),
      });
    }

    if (req.method === "GET" && path.startsWith("/orders/")) {
      const orderId = path.slice("/orders/".length);
      const store = await loadStore();
      const order = (store.orders || []).find(
        (o) => String(o.order_id || "").toUpperCase() === orderId.toUpperCase(),
      );
      if (!order) return json(res, 404, { error: "Order not found" });
      return json(res, 200, { order: orderPublic(order) });
    }

    if (req.method === "GET" && path === "/admin/session") {
      const session = currentAdmin(req);
      return json(res, 200, {
        authenticated: Boolean(session),
        username: session?.username || null,
      });
    }

    if (req.method === "GET" && path === "/admin/orders") {
      if (!requireAdmin(req, res)) return;
      const store = await loadStore();
      return json(res, 200, {
        orders: [...(store.orders || [])].reverse(),
        statuses: ORDER_STATUSES,
      });
    }

    if (req.method === "POST" && path === "/orders") {
      const body = await readJson(req);
      const goatId = cleanPrice(body.goatId);
      const serviceId = cleanText(body.serviceId, "alive");
      const customerName = cleanText(body.customerName);
      const phone = cleanText(body.phone);
      const address = cleanText(body.address);
      const notes = cleanText(body.notes);
      if (!goatId || !SERVICES[serviceId]) {
        return json(res, 400, { error: "Choose a valid goat and service" });
      }
      if (!customerName || !phone) {
        return json(res, 400, { error: "Customer name and phone are required" });
      }
      const store = await loadStore();
      const goat = (store.goats || []).find((g) => g.id === goatId);
      if (!goat) return json(res, 404, { error: "Goat not found" });
      const service = SERVICES[serviceId];
      const flatFee = service.flat_fee;
      const totalPrice =
        flatFee != null
          ? Number(flatFee)
          : Number(goat.price) + Number(service.extra || 0);
      const createdAt = new Date().toISOString();
      const order = {
        order_id: makeOrderId(),
        goat_id: goat.id,
        goat_name: goat.name_en,
        goat_name_ur: goat.name_ur || goat.name_en,
        goat_breed: goat.breed,
        goat_img: goat.img || "",
        service,
        base_price: flatFee != null ? 0 : Number(goat.price),
        total_price: totalPrice,
        customer_name: customerName,
        phone,
        address,
        notes,
        status: "WhatsApp confirmation pending",
        history: [
          {
            status: "WhatsApp confirmation pending",
            note: "Order saved. Please confirm on WhatsApp: Maulana Munavvar Husain Rashadi +91 99867 64178 or Hafiz Riyaz Maseehi +91 99806 06870.",
            at: createdAt,
          },
        ],
        created_at: createdAt,
        updated_at: createdAt,
      };
      store.orders = store.orders || [];
      store.orders.push(order);
      await saveStore(store);
      return json(res, 201, { order: orderPublic(order) });
    }

    if (req.method === "POST" && path === "/admin/login") {
      const body = await readJson(req);
      const username = cleanText(body.username);
      const password = cleanText(body.password);
      if (
        username === ADMIN_USERNAME &&
        (await checkPassword(password))
      ) {
        const sid = crypto.randomBytes(24).toString("base64url");
        sessions.set(sid, {
          username: ADMIN_USERNAME,
          expires_at: Date.now() + SESSION_TTL_MS,
        });
        return json(
          res,
          200,
          { ok: true, username: ADMIN_USERNAME },
          {
            "Set-Cookie": `${SESSION_COOKIE}=${sid}; HttpOnly; SameSite=Strict; Path=/; Max-Age=${SESSION_TTL_MS / 1000}`,
          },
        );
      }
      return json(res, 401, { error: "Invalid username or password" });
    }

    if (req.method === "POST" && path === "/admin/logout") {
      const sid = parseCookies(req.headers.cookie || "")[SESSION_COOKIE];
      if (sid) sessions.delete(sid);
      return json(
        res,
        200,
        { ok: true },
        {
          "Set-Cookie": `${SESSION_COOKIE}=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0`,
        },
      );
    }

    return json(res, 404, { error: "Route not found" });
  } catch (err) {
    console.error(err);
    return json(res, 500, { error: "Server error" });
  }
}
