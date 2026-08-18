import { useState } from "react";
import { Bell, User, FileText, BarChart3, Calendar, LogOut, type LucideIcon } from "lucide-react";
import { T } from "../theme";

interface NavItem {
  id: string;
  icon: LucideIcon;
  title: string;
}

const TOP: NavItem[] = [
  { id: "bell", icon: Bell, title: "შეტყობინებები" },
  { id: "patient", icon: User, title: "პაციენტი" },
  { id: "records", icon: FileText, title: "ჩანაწერები" },
  { id: "stats", icon: BarChart3, title: "სტატისტიკა" },
  { id: "calendar", icon: Calendar, title: "კალენდარი" },
];

/** Vertical primary pill rail with 40×40 icon buttons (active = white). */
export function Sidebar() {
  const [active, setActive] = useState("patient");
  const btn = (item: NavItem) => {
    const on = active === item.id;
    return (
      <button
        key={item.id}
        title={item.title}
        aria-label={item.title}
        aria-pressed={on}
        onClick={() => setActive(item.id)}
        style={{
          width: 40,
          height: 40,
          border: "none",
          borderRadius: 14,
          cursor: "pointer",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: on ? "#fff" : "transparent",
          color: on ? T.primary : "#cfc8ff",
          boxShadow: on ? "0 6px 14px rgba(40,30,90,.25)" : "none",
        }}
      >
        <item.icon size={19} strokeWidth={1.5} />
      </button>
    );
  };

  return (
    <div
      style={{
        flex: "none",
        padding: "28px 20px",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 14,
      }}
    >
      <div
        style={{
          width: 64,
          background: T.primary,
          borderRadius: 32,
          padding: "18px 0",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 10,
          boxShadow: "0 14px 28px rgba(123,111,214,.4)",
        }}
      >
        {TOP.map(btn)}
        <div style={{ height: 110 }} />
        <button
          title="გასვლა"
          aria-label="გასვლა"
          onClick={() => setActive("logout")}
          style={{
            width: 40,
            height: 40,
            border: "none",
            borderRadius: 14,
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            background: "transparent",
            color: "#cfc8ff",
          }}
        >
          <LogOut size={19} strokeWidth={1.5} />
        </button>
      </div>
    </div>
  );
}
