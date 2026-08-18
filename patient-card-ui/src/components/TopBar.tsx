import { useState } from "react";
import { Search, Plus } from "lucide-react";
import { T } from "../theme";

/** Top bar: title block + search pill + primary "ახალი ვიზიტი" button. */
export function TopBar() {
  const [query, setQuery] = useState("");
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 18, flexWrap: "wrap" }}>
      <div>
        <div style={{ fontSize: 12, color: T.textMuted }}>დენტა კლინიკა</div>
        <h2 style={{ margin: 0, fontSize: 24, fontWeight: 800, fontFamily: "inherit" }}>პაციენტის ბარათი</h2>
      </div>
      <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 14, flexWrap: "wrap" }}>
        <div
          style={{
            background: "#fff",
            borderRadius: T.rPill,
            padding: "10px 18px",
            boxShadow: T.shadowCard,
            minWidth: 200,
            display: "flex",
            alignItems: "center",
            gap: 8,
          }}
        >
          <Search size={16} strokeWidth={1.5} color={T.textMuted} />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="ძებნა…"
            style={{
              border: "none",
              outline: "none",
              background: "transparent",
              fontFamily: "inherit",
              fontSize: 13,
              color: T.text,
              width: "100%",
            }}
          />
        </div>
        <button
          style={{
            background: T.primary,
            color: "#fff",
            border: "none",
            borderRadius: T.rPill,
            padding: "11px 22px",
            fontFamily: "inherit",
            fontSize: 13,
            fontWeight: 700,
            cursor: "pointer",
            boxShadow: T.shadowPrimary,
            display: "inline-flex",
            alignItems: "center",
            gap: 6,
          }}
        >
          <Plus size={16} strokeWidth={2} />
          ახალი ვიზიტი
        </button>
      </div>
    </div>
  );
}
