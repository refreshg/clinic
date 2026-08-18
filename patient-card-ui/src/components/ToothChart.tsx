import { X } from "lucide-react";
import { STATUSES, statusById, FDI, T, type ToothStatusId } from "../theme";
import { Card } from "./ui";

export interface TeethState {
  [num: number]: { status: ToothStatusId; note: string };
}

interface Props {
  brush: ToothStatusId;
  teeth: TeethState;
  onBrush: (id: ToothStatusId) => void;
  onPaint: (num: number) => void;
  onRemove: (num: number) => void;
}

/** Color swatch (10×10 in the legend, 12×12 in the list). */
function Swatch({ id, size = 10 }: { id: ToothStatusId; size?: number }) {
  const st = statusById(id);
  return (
    <span
      style={{
        width: size,
        height: size,
        flex: "none",
        borderRadius: 4,
        background: st.color,
        border: st.border ? `1px solid ${st.border}` : "none",
      }}
    />
  );
}

/** One FDI tooth button — marked teeth take the status color + colored shadow. */
function Tooth({ num, teeth, onPaint }: { num: number; teeth: TeethState; onPaint: (n: number) => void }) {
  const rec = teeth[num];
  const st = rec ? statusById(rec.status) : statusById("healthy");
  const marked = !!rec && rec.status !== "healthy";
  return (
    <button
      title={st.label}
      aria-label={`კბილი ${num} — ${st.label}`}
      onClick={() => onPaint(num)}
      style={{
        width: 40,
        height: 40,
        flex: "none",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontSize: 12.5,
        fontWeight: 700,
        cursor: "pointer",
        fontFamily: "inherit",
        borderRadius: T.rTooth,
        background: marked ? st.color : T.bgSoft,
        color: marked ? st.ink : "#7a76a0",
        border: marked ? "none" : `2px solid ${T.borderSoft}`,
        boxShadow: marked ? `0 8px 16px ${st.color}55` : "none",
        boxSizing: "border-box",
        transition: "transform .1s ease",
      }}
      onMouseEnter={(e) => (e.currentTarget.style.transform = "scale(1.05)")}
      onMouseLeave={(e) => (e.currentTarget.style.transform = "scale(1)")}
    >
      {num}
    </button>
  );
}

function ToothRow({ nums, teeth, onPaint }: { nums: readonly number[]; teeth: TeethState; onPaint: (n: number) => void }) {
  return (
    <div style={{ display: "flex", gap: 5 }}>
      {nums.map((n) => (
        <Tooth key={n} num={n} teeth={teeth} onPaint={onPaint} />
      ))}
    </div>
  );
}

export function ToothChart({ brush, teeth, onBrush, onPaint, onRemove }: Props) {
  const selected = Object.keys(teeth)
    .map(Number)
    .sort((a, b) => a - b);

  return (
    <Card pad="26px 28px">
      <div style={{ display: "flex", alignItems: "baseline", gap: 14, flexWrap: "wrap", marginBottom: 16 }}>
        <div style={{ fontSize: 15, fontWeight: 800 }}>კბილის სქემა (FDI)</div>
        <span style={{ fontSize: 12, color: T.textMuted }}>აირჩიეთ სტატუსი და დააწკაპუნეთ კბილზე</span>
      </div>

      {/* legend / brush selector */}
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 20 }}>
        {STATUSES.map((s) => {
          const on = brush === s.id;
          return (
            <button
              key={s.id}
              onClick={() => onBrush(s.id)}
              aria-pressed={on}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 8,
                cursor: "pointer",
                fontFamily: "inherit",
                fontSize: 12,
                fontWeight: 700,
                padding: "7px 14px",
                borderRadius: T.rPill,
                border: "none",
                background: on ? T.text : T.bgSoft,
                color: on ? "#fff" : "#7a76a0",
                boxShadow: on ? "0 8px 16px rgba(58,54,84,.3)" : `inset 0 0 0 2px ${T.borderSoft}`,
              }}
            >
              <Swatch id={s.id} />
              {s.label}
            </button>
          );
        })}
      </div>

      {/* teeth grid */}
      <div style={{ display: "flex", flexDirection: "column", gap: 10, overflowX: "auto", paddingBottom: 4 }}>
        <div style={{ display: "flex", gap: 24, alignItems: "center" }}>
          <span style={{ width: 40, fontSize: 11, color: T.textMuted, fontWeight: 700 }}>ზედა</span>
          <ToothRow nums={FDI.q1} teeth={teeth} onPaint={onPaint} />
          <ToothRow nums={FDI.q2} teeth={teeth} onPaint={onPaint} />
        </div>
        <div style={{ display: "flex", gap: 24, alignItems: "center" }}>
          <span style={{ width: 40, fontSize: 11, color: T.textMuted, fontWeight: 700 }}>ქვედა</span>
          <ToothRow nums={FDI.q4} teeth={teeth} onPaint={onPaint} />
          <ToothRow nums={FDI.q3} teeth={teeth} onPaint={onPaint} />
        </div>
      </div>

      {/* selected teeth list */}
      <div style={{ display: "flex", flexDirection: "column", gap: 8, marginTop: 18 }}>
        {selected.length === 0 && (
          <div style={{ background: T.bgSoft, borderRadius: T.rInner, padding: "18px", textAlign: "center", color: T.textMuted, fontSize: 13 }}>
            მონიშნული კბილი ჯერ არ არის — აირჩიეთ სტატუსი და დააჭირეთ კბილს.
          </div>
        )}
        {selected.map((num) => {
          const rec = teeth[num];
          const st = statusById(rec.status);
          return (
            <div
              key={num}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 14,
                background: T.bgSoft,
                borderRadius: T.rInner,
                padding: "12px 18px",
                fontSize: 13,
              }}
            >
              <span style={{ fontWeight: 800, fontSize: 16, width: 34 }}>{num}</span>
              <Swatch id={rec.status} size={12} />
              <span style={{ fontWeight: 600 }}>{st.label}</span>
              <span style={{ color: T.textMuted }}>{rec.note || "—"}</span>
              <button
                onClick={() => onRemove(num)}
                aria-label={`კბილი ${num} — წაშლა`}
                style={{ marginLeft: "auto", background: "none", border: "none", color: "#c6c2dd", cursor: "pointer", display: "flex" }}
              >
                <X size={16} strokeWidth={1.5} />
              </button>
            </div>
          );
        })}
      </div>
    </Card>
  );
}
