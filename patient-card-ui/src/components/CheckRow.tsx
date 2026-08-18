import { Check } from "lucide-react";
import { T } from "../theme";

/** 20×20 rounded checkbox: on = primary fill + white check + shadow. */
function CheckBox({ on }: { on: boolean }) {
  if (on) {
    return (
      <span
        style={{
          width: 20,
          height: 20,
          flex: "none",
          borderRadius: T.rCheck,
          display: "inline-flex",
          alignItems: "center",
          justifyContent: "center",
          background: T.primary,
          color: "#fff",
          boxShadow: "0 4px 10px rgba(123,111,214,.4)",
        }}
      >
        <Check size={13} strokeWidth={3} />
      </span>
    );
  }
  return (
    <span
      style={{
        width: 20,
        height: 20,
        flex: "none",
        borderRadius: T.rCheck,
        display: "inline-block",
        border: `2px solid ${T.borderInput}`,
        background: "#fff",
        boxSizing: "border-box",
      }}
    />
  );
}

/** Status tab checkbox row: checked row gets a tinted background. */
export function CheckRow({ label, on, onToggle }: { label: string; on: boolean; onToggle: () => void }) {
  return (
    <label
      onClick={onToggle}
      style={{
        display: "flex",
        alignItems: "center",
        gap: 12,
        cursor: "pointer",
        background: on ? T.bgTint : "transparent",
        borderRadius: 14,
        padding: "10px 14px",
      }}
    >
      <CheckBox on={on} />
      <span style={{ color: on ? T.text : T.textMuted, fontWeight: on ? 700 : 500, fontSize: 13.5 }}>{label}</span>
    </label>
  );
}

/** Medical toggle card: on = white + shadow, off = translucent. */
export function ToggleCard({ label, on, onToggle }: { label: string; on: boolean; onToggle: () => void }) {
  return (
    <label
      onClick={onToggle}
      style={{
        display: "flex",
        alignItems: "center",
        gap: 12,
        cursor: "pointer",
        padding: "16px 18px",
        borderRadius: 20,
        background: on ? "#fff" : "rgba(255,255,255,.5)",
        boxShadow: on ? "0 10px 24px rgba(58,54,84,.1)" : "none",
        color: on ? T.text : T.textMuted,
      }}
    >
      <CheckBox on={on} />
      <span style={{ fontSize: 13, fontWeight: 700 }}>{label}</span>
    </label>
  );
}
