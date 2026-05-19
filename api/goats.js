const { readFileSync } = require("fs");
const { join } = require("path");
const { SERVICES } = require("./lib/services");

module.exports = (req, res) => {
  if (req.method !== "GET") {
    res.status(405).json({ error: "Method not allowed" });
    return;
  }
  try {
    const storePath = join(process.cwd(), "data", "store.json");
    const store = JSON.parse(readFileSync(storePath, "utf8"));
    res.setHeader("Cache-Control", "no-store");
    res.status(200).json({
      goats: store.goats || [],
      breeds: store.breeds || [],
      services: Object.values(SERVICES),
    });
  } catch (err) {
    res.status(500).json({ error: "Could not load catalogue" });
  }
};
