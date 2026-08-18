import { Check, X } from "lucide-react";
import { T } from "../theme";
import type { ContactRow } from "../data/demo";

const COLS = "64px 1.4fr .7fr 1fr .8fr .9fr .9fr 44px";
const HEADS = ["ძირით.", "ტელეფონი", "კოდი", "ტიპი", "არხი", "საგანგებო", "ნათესაობა"];

function HeaderCell({ children }: { children: string }) {
  return (
    <div
      style={{
        color: T.textMuted,
        fontSize: 11,
        fontWeight: 700,
        padding: "8px 10px",
        textTransform: "uppercase",
        letterSpacing: ".04em",
      }}
    >
      {children}
    </div>
  );
}

/** Small 18×18 boolean marker used inside the contact rows. */
function Mark({ on, color = T.primary }: { on: boolean; color?: string }) {
  if (on) {
    return (
      <span
        style={{
          width: 18,
          height: 18,
          borderRadius: 6,
          background: color,
          color: "#fff",
          display: "inline-flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <Check size={11} strokeWidth={3} />
      </span>
    );
  }
  return <span style={{ width: 18, height: 18, borderRadius: 6, border: `2px solid ${T.borderInput}`, display: "inline-block" }} />;
}

/** Contact table: header + rows; primary row highlighted; ✕ removes a row. */
export function ContactTable({ rows, onRemove }: { rows: ContactRow[]; onRemove: (id: number) => void }) {
  return (
    <div style={{ overflowX: "auto" }}>
      <div style={{ display: "grid", gridTemplateColumns: COLS, gap: 0, fontSize: 13, minWidth: 640 }}>
        {HEADS.map((h) => (
          <HeaderCell key={h}>{h}</HeaderCell>
        ))}
        <div />

        {rows.map((r) => {
          const bg = r.isPrimary ? T.bgTint : "transparent";
          const cell: React.CSSProperties = { background: bg, padding: "12px 10px" };
          return (
            <div key={r.id} style={{ display: "contents" }}>
              <div style={{ ...cell, borderRadius: r.isPrimary ? "14px 0 0 14px" : 0, display: "flex", alignItems: "center" }}>
                <Mark on={r.isPrimary} />
              </div>
              <div style={{ ...cell, fontWeight: 700 }}>{r.phone}</div>
              <div style={cell}>{r.countryCode}</div>
              <div style={cell}>{r.type}</div>
              <div style={{ ...cell, color: r.channel === "—" ? T.textMuted : T.text }}>{r.channel}</div>
              <div style={cell}>{r.isEmergency ? <Mark on color={T.pink} /> : <span style={{ color: T.textMuted }}>—</span>}</div>
              <div style={{ ...cell, color: r.relation === "—" ? T.textMuted : T.text }}>{r.relation}</div>
              <div style={{ ...cell, borderRadius: r.isPrimary ? "0 14px 14px 0" : 0, color: "#c6c2dd", cursor: "pointer", display: "flex", alignItems: "center" }}>
                <button
                  onClick={() => onRemove(r.id)}
                  aria-label="კონტაქტის წაშლა"
                  style={{ background: "none", border: "none", color: "inherit", cursor: "pointer", display: "flex" }}
                >
                  <X size={14} strokeWidth={1.5} />
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
