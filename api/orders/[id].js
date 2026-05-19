const { readFileSync } = require("fs");
const { join } = require("path");

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
    history: order.history || [],
    created_at: order.created_at,
    updated_at: order.updated_at,
  };
}

module.exports = (req, res) => {
  if (req.method !== "GET") {
    res.status(405).json({ error: "Method not allowed" });
    return;
  }
  const orderId = String(req.query.id || "").trim();
  if (!orderId) {
    res.status(400).json({ error: "Order ID required" });
    return;
  }
  try {
    const storePath = join(process.cwd(), "data", "store.json");
    const store = JSON.parse(readFileSync(storePath, "utf8"));
    const wanted = orderId.toUpperCase();
    const order = (store.orders || []).find(
      (o) => String(o.order_id || "").toUpperCase() === wanted,
    );
    if (!order) {
      res.status(404).json({ error: "Order not found" });
      return;
    }
    res.setHeader("Cache-Control", "no-store");
    res.status(200).json({ order: orderPublic(order) });
  } catch (err) {
    res.status(500).json({ error: "Could not load order" });
  }
};
