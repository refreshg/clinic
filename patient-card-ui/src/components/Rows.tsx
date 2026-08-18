import { X, FileText } from "lucide-react";
import { T } from "../theme";
import { Chip } from "./ui";
import type { Procedure, DocumentRecord } from "../data/demo";

/** History → procedure row: status badge, meta, tooth chip, remove. */
export function ProcedureRow({ p, onRemove }: { p: Procedure; onRemove: (id: number) => void }) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 16,
        background: T.bgSoft,
        borderRadius: T.rInner,
        padding: "14px 18px",
        fontSize: 13,
        flexWrap: "wrap",
      }}
    >
      <span
        style={{
          background: "#fff3d6",
          color: "#c08a00",
          borderRadius: T.rPill,
          padding: "4px 12px",
          fontSize: 11,
          fontWeight: 700,
          flex: "none",
        }}
      >
        {p.status}
      </span>
      <span style={{ color: T.textMuted }}>პროცედურა: {p.name}</span>
      <span>
        რაოდ. <b>{p.qty}</b>
      </span>
      <span>
        თარიღი <b>{p.date}</b>
      </span>
      <span>
        შემსრ. <b>{p.performer}</b>
      </span>
      <Chip style={{ marginLeft: "auto" }}>კბილი {p.tooth}</Chip>
      <button
        onClick={() => onRemove(p.id)}
        aria-label="პროცედურის წაშლა"
        style={{ background: "none", border: "none", color: "#c6c2dd", cursor: "pointer", display: "flex" }}
      >
        <X size={16} strokeWidth={1.5} />
      </button>
    </div>
  );
}

/** History → document row: icon badge, title/meta, view link. */
export function DocumentRow({ d }: { d: DocumentRecord }) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 14,
        background: T.bgSoft,
        borderRadius: T.rInner,
        padding: "14px 18px",
        fontSize: 13,
      }}
    >
      <span
        style={{
          width: 38,
          height: 38,
          borderRadius: 12,
          background: T.primary,
          color: "#fff",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          flex: "none",
        }}
      >
        <FileText size={17} strokeWidth={1.5} />
      </span>
      <div>
        <b>{d.title}</b>
        <div style={{ color: T.textMuted, fontSize: 12 }}>
          {d.date} · {d.note}
        </div>
      </div>
      <a href={d.href} style={{ marginLeft: "auto", fontSize: 12, fontWeight: 700 }}>
        ნახვა
      </a>
    </div>
  );
}
