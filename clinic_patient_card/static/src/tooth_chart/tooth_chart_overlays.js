/** @odoo-module **/
// Condition (14) and treatment (8) pictures drawn over the healthy tooth.
// Side-view overlays live in the tooth's local coordinates: the gum line is y=0,
// the crown reaches down to y=g.h, the roots point to g.apex (negative y). The
// lower-jaw teeth are mirrored by their own group, so one drawing serves both.
// Occlusal overlays are centred on (g.cx, 0).

const f = (n) => Math.round(n * 10) / 10;

function crownPath(g, grow = 0) {
    const { x0, x1, h } = g;
    const a = x0 - grow;
    const b = x1 + grow;
    return `M${f(a + 3)},${-grow} L${f(b - 3)},${-grow} C${f(b + 1)},${f(h * 0.35)} ${f(b)},${f(h * 0.8)} ${f(b - 4)},${f(h + grow)} L${f(a + 4)},${f(h + grow)} C${f(a)},${f(h * 0.8)} ${f(a - 1)},${f(h * 0.35)} ${f(a + 3)},${-grow}Z`;
}

function rootXs(g) {
    const w = g.x1 - g.x0;
    if (w > 33) { return [g.cx - w * 0.24, g.cx + w * 0.24]; }
    if (w > 24) { return [g.cx - w * 0.2, g.cx + w * 0.2]; }
    return [g.cx];
}

export const CONDITION_SIDE = {
    caries: (g) => `<ellipse cx="${f(g.cx - (g.x1 - g.x0) * 0.2)}" cy="${f(g.h * 0.5)}" rx="${f((g.x1 - g.x0) * 0.13)}" ry="${f(g.h * 0.14)}" fill="#6a3b1f"/>`,
    deep_caries: (g) => `<ellipse cx="${f(g.cx - (g.x1 - g.x0) * 0.08)}" cy="${f(g.h * 0.45)}" rx="${f((g.x1 - g.x0) * 0.24)}" ry="${f(g.h * 0.26)}" fill="#3e2112"/><ellipse cx="${f(g.cx)}" cy="${f(g.h * 0.4)}" rx="${f((g.x1 - g.x0) * 0.08)}" ry="${f(g.h * 0.1)}" fill="#c0392b"/>`,
    pulpitis: (g) => `<path d="M${f(g.cx)},${f(g.h * 0.75)} L${f(g.cx)},${f(g.apex * 0.8)}" stroke="#d6303a" stroke-width="2.6" stroke-linecap="round"/><ellipse cx="${f(g.cx)}" cy="${f(g.h * 0.55)}" rx="${f((g.x1 - g.x0) * 0.18)}" ry="${f(g.h * 0.2)}" fill="#e0525a" opacity=".85"/>`,
    periapical: (g) => `<circle cx="${f(g.cx)}" cy="${f(g.apex + 1)}" r="6" fill="#d6303a" opacity=".75"/><path d="M${f(g.cx)},${f(g.h * 0.7)} L${f(g.cx)},${f(g.apex * 0.8)}" stroke="#d6303a" stroke-width="2" stroke-linecap="round"/>`,
    cyst: (g) => `<circle cx="${f(g.cx)}" cy="${f(g.apex - 2)}" r="10" fill="#e8a0a8" fill-opacity=".45" stroke="#b83a4b" stroke-width="1.6" stroke-dasharray="3 2"/>`,
    parodontitis: (g) => `<path d="M${f(g.x0 - 3)},-6 L${f(g.x1 + 3)},-6 L${f(g.x1 + 3)},4 L${f(g.x0 - 3)},4Z" fill="#c4505c" opacity=".7"/><path d="M${f(g.x0 - 3)},9 L${f(g.x1 + 3)},9" stroke="#8d2f3a" stroke-width="1.6" stroke-dasharray="3 2"/>`,
    gingivitis: (g) => `<path d="M${f(g.x0 - 2)},-5 Q${f(g.cx)},-9 ${f(g.x1 + 2)},-5 L${f(g.x1 + 2)},3 Q${f(g.cx)},-1 ${f(g.x0 - 2)},3Z" fill="#e0525a" opacity=".8"/>`,
    fracture: (g) => `<path d="M${f(g.cx - 4)},2 L${f(g.cx + 3)},${f(g.h * 0.3)} L${f(g.cx - 3)},${f(g.h * 0.55)} L${f(g.cx + 4)},${f(g.h * 0.95)}" fill="none" stroke="#3a2a26" stroke-width="2" stroke-linejoin="round"/>`,
    defect: (g) => `<path d="M${f(g.x0 - 0.5)},3 L${f(g.x0 + (g.x1 - g.x0) * 0.32)},8 L${f(g.x0 - 0.5)},15Z" fill="#6a3b1f"/>`,
    attrition: (g) => `<path d="M${f(g.x0 + 2)},${f(g.h - 5)} L${f(g.x1 - 2)},${f(g.h - 5)} L${f(g.x1 - 4)},${f(g.h + 1)} L${f(g.x0 + 4)},${f(g.h + 1)}Z" fill="#b69d72"/>`,
    calculus: (g) => `<path d="M${f(g.x0 + 1)},2 Q${f(g.x0 + 4)},11 ${f(g.cx - 2)},7 Q${f(g.cx + 3)},13 ${f(g.x1 - 4)},8 Q${f(g.x1 - 1)},9 ${f(g.x1 - 1)},2Z" fill="#b8903a" opacity=".9"/>`,
    mobility: (g) => `<path d="M${f(g.x0 - 7)},${f(g.h * 0.5)} L${f(g.x0 - 1)},${f(g.h * 0.5)} M${f(g.x1 + 1)},${f(g.h * 0.5)} L${f(g.x1 + 7)},${f(g.h * 0.5)}" stroke="#e08a00" stroke-width="2.4" stroke-linecap="round"/><path d="M${f(g.x0 - 7)},${f(g.h * 0.5)} l3,-3 m-3,3 l3,3 M${f(g.x1 + 7)},${f(g.h * 0.5)} l-3,-3 m3,3 l-3,3" stroke="#e08a00" stroke-width="2" fill="none" stroke-linecap="round"/>`,
    retained: (g) => `<rect x="${f(g.x0 - 5)}" y="${f(g.apex - 5)}" width="${f(g.x1 - g.x0 + 10)}" height="${f(g.h - g.apex + 10)}" rx="8" fill="none" stroke="#3f6fd1" stroke-width="2" stroke-dasharray="4 3"/>`,
    root_remnant: (g) => `<path d="${crownPath(g, 1)}" fill="#ffffff" stroke="none"/><path d="M${f(g.x0 + 3)},0 L${f(g.x1 - 3)},0 L${f(g.x1 - 6)},7 Q${f(g.cx)},10 ${f(g.x0 + 6)},7Z" fill="#8b6a3a"/>`,
};

export const CONDITION_OCC = {
    caries: (g) => `<circle cx="${f(g.cx - 3)}" cy="-2" r="3.2" fill="#6a3b1f"/>`,
    deep_caries: (g) => `<circle cx="${f(g.cx)}" cy="0" r="${f(Math.max(5, (g.x1 - g.x0) * 0.22))}" fill="#3e2112"/>`,
    pulpitis: (g) => `<circle cx="${f(g.cx)}" cy="0" r="4" fill="#d6303a"/>`,
    fracture: (g) => `<path d="M${f(g.cx - 8)},-5 L${f(g.cx)},0 L${f(g.cx + 8)},5" stroke="#3a2a26" stroke-width="2" fill="none"/>`,
    defect: (g) => `<path d="M${f(g.x0 + 2)},-3 L${f(g.x0 + 8)},0 L${f(g.x0 + 2)},3Z" fill="#6a3b1f"/>`,
    attrition: (g) => `<circle cx="${f(g.cx)}" cy="0" r="${f(Math.max(4, (g.x1 - g.x0) * 0.25))}" fill="#b69d72" opacity=".8"/>`,
    calculus: (g) => `<circle cx="${f(g.cx + 4)}" cy="3" r="3" fill="#b8903a"/>`,
    retained: (g) => `<circle cx="${f(g.cx)}" cy="0" r="${f((g.x1 - g.x0) / 2 + 3)}" fill="none" stroke="#3f6fd1" stroke-width="1.8" stroke-dasharray="3 2"/>`,
    root_remnant: (g) => `<circle cx="${f(g.cx)}" cy="0" r="${f((g.x1 - g.x0) / 2 - 1)}" fill="#8b6a3a" opacity=".9"/>`,
};

export const TREATMENT_SIDE = {
    filling: (g) => `<path d="M${f(g.x0 + 4)},${f(g.h * 0.12)} L${f(g.x1 - 4)},${f(g.h * 0.12)} L${f(g.x1 - 6)},${f(g.h * 0.62)} L${f(g.x0 + 6)},${f(g.h * 0.62)}Z" fill="#7f93b8" stroke="#56688c" stroke-width="1"/>`,
    canal_filled: (g) => rootXs(g).map((x) => `<path d="M${f(x)},${f(g.h * 0.2)} L${f(x)},${f(g.apex * 0.88)}" stroke="#2f3e6b" stroke-width="2.8" stroke-linecap="round"/>`).join(""),
    crown: (g) => `<path d="${crownPath(g, 1.5)}" fill="#f0c94e" stroke="#b8902a" stroke-width="1.3"/><path d="M${f(g.x0 + 5)},${f(g.h * 0.2)} L${f(g.x0 + 5)},${f(g.h * 0.6)}" stroke="#fff6cf" stroke-width="2" stroke-linecap="round"/>`,
    bridge: (g) => `<path d="${crownPath(g, 1.5)}" fill="#9fb4d6" stroke="#566b94" stroke-width="1.3"/><rect x="${f(g.x0 - 8)}" y="${f(g.h * 0.38)}" width="${f(g.x1 - g.x0 + 16)}" height="6" rx="2" fill="#566b94"/>`,
    implant: (g) => `<rect x="${f(g.x0 - 1)}" y="${f(g.apex - 3)}" width="${f(g.x1 - g.x0 + 2)}" height="${f(-g.apex + 2)}" fill="#f3b9c8"/><path d="M${f(g.cx - 5)},0 L${f(g.cx + 5)},0 L${f(g.cx + 4)},${f(g.apex * 0.85)} L${f(g.cx)},${f(g.apex * 0.95)} L${f(g.cx - 4)},${f(g.apex * 0.85)}Z" fill="#8a94a6" stroke="#4d5668" stroke-width="1"/><path d="M${f(g.cx - 5)},-6 H${f(g.cx + 5)} M${f(g.cx - 5)},-13 H${f(g.cx + 5)} M${f(g.cx - 4)},-20 H${f(g.cx + 4)} M${f(g.cx - 4)},-27 H${f(g.cx + 4)} M${f(g.cx - 3.5)},-34 H${f(g.cx + 3.5)}" stroke="#4d5668" stroke-width="1.2"/>`,
    veneer: (g) => `<path d="M${f(g.x0 + 3)},${f(g.h * 0.08)} L${f(g.cx + 1)},${f(g.h * 0.08)} L${f(g.cx + 1)},${f(g.h - 2)} L${f(g.x0 + 5)},${f(g.h - 2)}Z" fill="#8fd6cf" opacity=".85" stroke="#4aa59d" stroke-width="1"/>`,
    missing: () => "",
    extracted: (g) => `<path d="M${f(g.x0 + 3)},${f(g.h * 0.2)} L${f(g.x1 - 3)},${f(g.h * 0.85)} M${f(g.x1 - 3)},${f(g.h * 0.2)} L${f(g.x0 + 3)},${f(g.h * 0.85)}" stroke="#c0392b" stroke-width="3" stroke-linecap="round"/>`,
};

export const TREATMENT_OCC = {
    filling: (g) => `<circle cx="${f(g.cx)}" cy="0" r="${f(Math.max(4, (g.x1 - g.x0) * 0.2))}" fill="#7f93b8" stroke="#56688c" stroke-width="1"/>`,
    canal_filled: (g) => `<circle cx="${f(g.cx)}" cy="0" r="2.6" fill="#2f3e6b"/>`,
    crown: (g) => `<circle cx="${f(g.cx)}" cy="0" r="${f((g.x1 - g.x0) / 2 - 1)}" fill="#f0c94e" stroke="#b8902a" stroke-width="1.2"/>`,
    bridge: (g) => `<circle cx="${f(g.cx)}" cy="0" r="${f((g.x1 - g.x0) / 2 - 1)}" fill="#9fb4d6" stroke="#566b94" stroke-width="1.2"/>`,
    implant: (g) => `<circle cx="${f(g.cx)}" cy="0" r="4.5" fill="#8a94a6" stroke="#4d5668" stroke-width="1.2"/>`,
    veneer: (g) => `<path d="M${f(g.x0 + 2)},-3 Q${f(g.cx)},-9 ${f(g.x1 - 2)},-3" fill="none" stroke="#4aa59d" stroke-width="2.4"/>`,
    missing: () => "",
    extracted: (g) => `<path d="M${f(g.cx - 5)},-5 L${f(g.cx + 5)},5 M${f(g.cx + 5)},-5 L${f(g.cx - 5)},5" stroke="#c0392b" stroke-width="2.4" stroke-linecap="round"/>`,
};

export const CONDITION_LABELS = {
    caries: "კარიესი", deep_caries: "ღრმა კარიესი", pulpitis: "პულპიტი",
    periapical: "პერიოდონტიტი", cyst: "კისტა / გრანულომა", parodontitis: "პაროდონტიტი",
    gingivitis: "გინგივიტი", fracture: "მოტეხილობა / ბზარი", defect: "სოლისებრი დეფექტი",
    attrition: "ცვეთა", calculus: "კბილის ქვა", mobility: "მოძრაობა",
    retained: "რეტინირებული", root_remnant: "ფესვის ნარჩენი",
};
export const TREATMENT_LABELS = {
    filling: "ბეჭედი (პლომბა)", canal_filled: "არხი დაბჟენილია", crown: "გვირგვინი",
    bridge: "ხიდი", implant: "იმპლანტი", veneer: "ვინირი", missing: "აკლია",
    extracted: "ამოღებული",
};
