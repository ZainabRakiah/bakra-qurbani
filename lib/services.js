export const SERVICES = {
  alive: {
    id: "alive",
    en: "Delivered Alive to Home",
    ur: "زندہ گھر پر ڈیلیور",
    extra: 0,
    flat_fee: null,
    available: "15–27 May",
    note_en:
      "Open 15–27 May only. Tell us how many kg goat you want; delivery fee is charged separately. Door delivery within 25 km of Munireddy Palya, JC Nagar.",
    note_ur:
      "صرف 15 تا 27 مئی کھلا۔ بتا دیں آپ کتنے کلو کا بکرا چاہتے ہیں؛ ڈیلیوری فیس الگ وصول ہوگی۔ Munireddy Palya,\nJC Nagar سے 25 کلومیٹر کے اندر گھر ڈیلیوری۔",
  },
  cut: {
    id: "cut",
    en: "Cut & Delivered to Home",
    ur: "ذبح کر کے گھر ڈیلیور",
    extra: 26500,
    flat_fee: 26500,
    available: "Eid 28–30 May",
    note_en:
      "Fixed price ₹26,500 — not per kg. Minimum 18 kg meat guaranteed on all three Eid days (28–30 May 2026). Free door delivery within 25 km of Munireddy Palya, JC Nagar.",
    note_ur:
      "مقررہ قیمت ₹26,500 — فی کلو نہیں۔ عید کے تینوں دنوں (28–30 مئی 2026) کم از کم 18 کلو گوشت کی ضمانت۔ Munireddy Palya,\nJC Nagar سے 25 کلومیٹر کے اندر مفت گھر ڈیلیوری۔",
  },
  poor: {
    id: "poor",
    en: "Cut & Distributed to Poor",
    ur: "ذبح کر کے غریبوں میں تقسیم",
    extra: 26500,
    flat_fee: 26500,
    available: "Eid 28–30 May",
    note_en:
      "Fixed price ₹26,500 — not per kg. Minimum 18 kg meat guaranteed on all three Eid days (28–30 May 2026). Cut and distributed to the poor.",
    note_ur:
      "مقررہ قیمت ₹26,500 — فی کلو نہیں۔ عید کے تینوں دنوں (28–30 مئی 2026) کم از کم 18 کلو گوشت کی تقسیم کی ضمانت۔ ذبح کر کے غریبوں میں تقسیم۔",
  },
};

export const ORDER_STATUSES = [
  "WhatsApp confirmation pending",
  "Booked",
  "Confirmed",
  "Preparing",
  "Out for delivery",
  "Delivered",
  "Cancelled",
];
