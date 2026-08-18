import { T } from "../theme";

export type TabId = "main" | "med" | "fin" | "hist";

const TABS: { id: TabId; label: string }[] = [
  { id: "main", label: "ძირითადი" },
  { id: "med", label: "სამედიცინო" },
  { id: "fin", label: "ფინანსური" },
  { id: "hist", label: "ისტორია" },
];

/** White pill container with 4 tab buttons; active = primary fill. */
export function PillTabs({ active, onChange }: { active: TabId; onChange: (t: TabId) => void }) {
  return (
    <div
      role="tablist"
      style={{
        display: "flex",
        gap: 8,
        background: "#fff",
        borderRadius: T.rPill,
        padding: 6,
        boxShadow: T.shadowCard,
        alignSelf: "flex-start",
        maxWidth: "100%",
        overflowX: "auto",
      }}
    >
      {TABS.map((tab) => {
        const on = tab.id === active;
        return (
          <button
            key={tab.id}
            role="tab"
            aria-selected={on}
            onClick={() => onChange(tab.id)}
            style={{
              fontFamily: "inherit",
              fontSize: 13,
              fontWeight: 700,
              cursor: "pointer",
              background: on ? T.primary : "transparent",
              border: "none",
              borderRadius: T.rPill,
              padding: "10px 22px",
              color: on ? "#fff" : T.textMuted,
              boxShadow: on ? "0 8px 18px rgba(123,111,214,.4)" : "none",
              whiteSpace: "nowrap",
              transition: "background .15s ease, color .15s ease",
            }}
          >
            {tab.label}
          </button>
        );
      })}
    </div>
  );
}
