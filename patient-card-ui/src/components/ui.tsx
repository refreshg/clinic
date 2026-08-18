import type { CSSProperties, ReactNode } from "react";
import { T } from "../theme";

/** White rounded card with the standard soft shadow. */
export function Card({
  children,
  style,
  pad = "24px 26px",
}: {
  children: ReactNode;
  style?: CSSProperties;
  pad?: string;
}) {
  return (
    <div
      style={{
        background: T.bgCard,
        borderRadius: T.rCard,
        padding: pad,
        boxShadow: T.shadowCard,
        ...style,
      }}
    >
      {children}
    </div>
  );
}

/** 15px/800 card heading, optional right-aligned action (e.g. + დამატება). */
export function CardTitle({ children, action }: { children: ReactNode; action?: ReactNode }) {
  if (!action) {
    return <div style={{ fontSize: 15, fontWeight: 800, marginBottom: 16 }}>{children}</div>;
  }
  return (
    <div style={{ display: "flex", alignItems: "center", marginBottom: 14 }}>
      <div style={{ fontSize: 15, fontWeight: 800 }}>{children}</div>
      <div style={{ marginLeft: "auto" }}>{action}</div>
    </div>
  );
}

/** The light-lilac pill add button ("+ დამატება"). */
export function AddButton({ children = "+ დამატება", onClick }: { children?: ReactNode; onClick?: () => void }) {
  return (
    <button
      onClick={onClick}
      style={{
        background: T.bgChip,
        color: T.primary,
        border: "none",
        borderRadius: T.rPill,
        padding: "8px 16px",
        fontFamily: "inherit",
        fontSize: 12,
        fontWeight: 700,
        cursor: "pointer",
      }}
    >
      {children}
    </button>
  );
}

export interface LabelValue {
  label: string;
  value: ReactNode;
  muted?: boolean; // render the value in muted color (e.g. "—")
}

/**
 * 180px + 1fr label/value grid with a 1px row divider (last row has none).
 * Matches the reference "ძირითადი ინფორმაცია" / insurance grids.
 */
export function LabelValueGrid({ rows, labelWidth = 180 }: { rows: LabelValue[]; labelWidth?: number }) {
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: `${labelWidth}px 1fr`,
        fontSize: 13.5,
      }}
    >
      {rows.map((r, i) => {
        const last = i === rows.length - 1;
        const line = last ? undefined : `1px solid ${T.rowLine}`;
        return (
          <div key={r.label} style={{ display: "contents" }}>
            <span style={{ color: T.textMuted, padding: "9px 0", borderBottom: line }}>{r.label}</span>
            <span
              style={{
                padding: "9px 0",
                borderBottom: line,
                fontWeight: r.muted ? 400 : 600,
                color: r.muted ? T.textMuted : T.text,
              }}
            >
              {r.value}
            </span>
          </div>
        );
      })}
    </div>
  );
}

/** Small lilac chip (e.g. "კბილი 32"). */
export function Chip({ children, style }: { children: ReactNode; style?: CSSProperties }) {
  return (
    <span
      style={{
        background: T.bgChip,
        color: T.primaryDark,
        borderRadius: 12,
        padding: "4px 12px",
        fontWeight: 800,
        ...style,
      }}
    >
      {children}
    </span>
  );
}

/** Financial stat card. variant controls the background + ink. */
export function StatCard({
  label,
  value,
  variant = "white",
}: {
  label: string;
  value: string;
  variant?: "primary" | "pink" | "white";
}) {
  const isColored = variant !== "white";
  const bg =
    variant === "primary" ? "linear-gradient(135deg,#8478e0,#6d5fd0)" : variant === "pink" ? T.pinkGrad : T.bgCard;
  const shadow =
    variant === "primary" ? T.shadowHero.replace(".4)", ".35)") : variant === "pink" ? T.shadowPink : T.shadowCard;
  return (
    <div
      style={{
        background: bg,
        borderRadius: T.rCard,
        padding: "22px 24px",
        color: isColored ? "#fff" : T.text,
        boxShadow: shadow,
      }}
    >
      <div style={{ fontSize: 12, opacity: isColored ? (variant === "pink" ? 0.75 : 0.7) : 1, color: isColored ? "#fff" : T.textMuted }}>
        {label}
      </div>
      <div style={{ fontSize: 30, fontWeight: 800, marginTop: 4 }}>{value}</div>
    </div>
  );
}

/** Progress bar stat (გაცდენების % / LTV) — 8px pill track + fill. */
export function ProgressStat({
  label,
  value,
  percent,
  color = T.primary,
}: {
  label: string;
  value: string;
  percent: number;
  color?: string;
}) {
  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 5 }}>
        <span style={{ color: T.textMuted }}>{label}</span>
        <b>{value}</b>
      </div>
      <div style={{ height: 8, background: T.bgChip, borderRadius: T.rPill }}>
        <div style={{ width: `${Math.max(0, Math.min(100, percent))}%`, height: 8, background: color, borderRadius: T.rPill }} />
      </div>
    </div>
  );
}
