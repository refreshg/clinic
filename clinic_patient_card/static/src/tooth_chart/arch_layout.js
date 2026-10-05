/** @odoo-module **/
// "Arch" view of the tooth chart (clinic design 2): the teeth are laid along a
// curve with the gum band behind them (side view) and as two horseshoes seen
// from above. Same tooth drawings / geometry as the classic row view, only the
// placement differs, so every overlay (disease / treatment) works unchanged.
const UP = [18, 17, 16, 15, 14, 13, 12, 11, 21, 22, 23, 24, 25, 26, 27, 28];
const LOW = [48, 47, 46, 45, 44, 43, 42, 41, 31, 32, 33, 34, 35, 36, 37, 38];
const S = 1.45; // side-view scale
const CX = 500;
const r1 = (n) => Math.round(n * 10) / 10;
const deg = (r) => (r * 180) / Math.PI;

function slots(order, byF, gap) {
    // x offsets (from the centre) of every tooth, widths in side-view scale
    const ws = order.map((f) => (byF[f].g.x1 - byF[f].g.x0) * S);
    const total = ws.reduce((a, b) => a + b, 0) + gap * (order.length - 1) + 10;
    let acc = 0;
    return {
        total,
        xs: order.map((f, i) => {
            const mid = acc + ws[i] / 2 + (i >= 8 ? 10 : 0);
            acc += ws[i] + gap;
            return mid - total / 2;
        }),
    };
}

function gumBand(up, Yc, A, half, xs0, xs1) {
    const pts = [];
    for (let x = xs0; x <= xs1; x += 20) {
        const d = x / half;
        pts.push([CX + x, up ? Yc - A * d * d + 3 : Yc + A * d * d - 3]);
    }
    const far = up ? -112 : 112;
    const top = pts.map(([x, y]) => [x, y + far]).reverse();
    const path = (a) => a.map((p, i) => (i ? "L" : "M") + r1(p[0]) + "," + r1(p[1])).join(" ");
    const id = up ? "tcGumU" : "tcGumL";
    return `<defs><linearGradient id="${id}" x1="0" y1="${up ? 0 : 1}" x2="0" y2="${up ? 1 : 0}">`
        + `<stop offset="0" stop-color="#fbe3e8"/><stop offset="1" stop-color="#f0a9ba"/></linearGradient></defs>`
        + `<path d="${path(pts)} ${path(top).replace("M", "L")}Z" fill="url(#${id})"/>`;
}

function archSide(up, parts, byF) {
    const order = up ? UP : LOW;
    const Yc = up ? 250 : 440;
    const A = 70;
    const { total, xs } = slots(order, byF, 4);
    const half = total / 2;
    let out = gumBand(up, Yc, A, half, xs[0] - 30, xs[xs.length - 1] + 30);
    order.forEach((f, i) => {
        const t = byF[f];
        const x = xs[i];
        const d = x / half;
        const y = up ? Yc - A * d * d : Yc + A * d * d;
        const slope = ((up ? -1 : 1) * 2 * A * d) / half;
        const th = Math.atan(slope);
        const X = CX + x;
        const flip = up ? `scale(${S})` : `scale(${S},${-S})`;
        const tr = `translate(${r1(X)},${r1(y)}) rotate(${r1(deg(th))}) ${flip} translate(${-t.g.cx},0)`;
        // label beyond the root tip, along the tooth axis
        const L = (-t.g.apex + 30) * S;
        const lx = up ? X + Math.sin(th) * L : X - Math.sin(th) * L;
        const ly = up ? y - Math.cos(th) * L : y + Math.cos(th) * L;
        out += `<g class="${parts[f].cls}" data-f="${f}"><title>${parts[f].tip}</title>`
            + `<g transform="${tr}">${parts[f].side}</g>`
            + `<text x="${r1(lx)}" y="${r1(ly + 4)}" class="tc_lbl" text-anchor="middle">${f}</text></g>`;
    });
    return out;
}

function archOcc(up, cx, parts, byF) {
    const a = 185;
    const b = 130;
    const cy = up ? 850 : 722;
    const pt = (t) => [cx + a * Math.cos(t), up ? cy - b * Math.sin(t) : cy + b * Math.sin(t)];
    // arc-length table from t=PI (left) to t=0 (right)
    const N = 400;
    const tab = [];
    let len = 0;
    let prev = pt(Math.PI);
    for (let k = 0; k <= N; k++) {
        const t = Math.PI * (1 - k / N);
        const p = pt(t);
        len += Math.hypot(p[0] - prev[0], p[1] - prev[1]);
        tab.push([t, len]);
        prev = p;
    }
    const tAt = (s) => {
        for (const [t, l] of tab) {
            if (l >= s) { return t; }
        }
        return 0;
    };
    const order = up ? UP : LOW;
    const ws = order.map((f) => byF[f].g.x1 - byF[f].g.x0);
    const sum = ws.reduce((x, y) => x + y, 0);
    const arc = tab.filter((_, k) => k % 8 === 0).map(([t]) => pt(t));
    const dArc = arc.map((p, i) => (i ? "L" : "M") + r1(p[0]) + "," + r1(p[1])).join(" ");
    let out = `<path d="${dArc} Z" fill="#f8cfd9"/>`;
    if (!up) {
        out += `<ellipse cx="${cx}" cy="${cy + 60}" rx="62" ry="78" fill="#f1b2c0" opacity=".8"/>`;
    }
    out += `<path d="${dArc}" fill="none" stroke="#f0a7b9" stroke-width="54" stroke-linecap="round" stroke-linejoin="round"/>`;
    let acc = 0;
    order.forEach((f, i) => {
        const s = ((acc + ws[i] / 2) / sum) * len;
        acc += ws[i];
        const t = tAt(s);
        const [px, py] = pt(t);
        const ang = up
            ? Math.atan2(b * Math.cos(t), a * Math.sin(t))
            : Math.atan2(-b * Math.cos(t), a * Math.sin(t));
        const g = byF[f].g;
        const nx = (px - cx) / a;
        const ny = (py - cy) / b;
        const nl = Math.hypot(nx, ny) || 1;
        const lx = px + (nx / nl) * 42;
        const ly = py + (ny / nl) * 42;
        out += `<g class="${parts[f].cls}" data-f="${f}"><title>${parts[f].tip}</title>`
            + `<g transform="translate(${r1(px)},${r1(py)}) rotate(${r1(deg(ang))}) translate(${-g.cx},0)">${parts[f].occ}</g>`
            + `<text x="${r1(lx)}" y="${r1(ly + 4)}" class="tc_lbl" text-anchor="middle">${f}</text></g>`;
    });
    return out;
}

export const ARCH_VIEWBOX = "0 0 1000 910";

export function archChart(parts, teeth) {
    const byF = {};
    teeth.forEach((t) => { byF[t.f] = t; });
    return archSide(true, parts, byF) + archSide(false, parts, byF)
        + archOcc(true, 250, parts, byF) + archOcc(false, 750, parts, byF);
}
