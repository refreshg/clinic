/**
 * Design tokens mirrored from docs/design_handoff_patient_card/tokens.css.
 * Kept as JS constants for inline styles; the CSS variables in tokens.css
 * remain the single source of truth for values used in stylesheets.
 */
export const T = {
  bgPage: "#c6cbdd",
  bgApp: "#f7f8fc",
  bgCard: "#ffffff",
  bgSoft: "#fbfbfe",
  bgTint: "#f7f6fd",
  bgChip: "#efedfb",

  primary: "#7b6fd6",
  primaryDark: "#5e51c4",
  primaryGrad: "linear-gradient(135deg,#8478e0 0%,#6d5fd0 55%,#5f50c6 100%)",
  pink: "#f87ba6",
  pinkGrad: "linear-gradient(135deg,#f98cb1,#f76d9d)",

  text: "#3a3654",
  textMuted: "#a5a1c0",
  borderSoft: "#efedfb",
  borderInput: "#e3e1f0",
  rowLine: "#f0f0f7",

  rApp: "36px",
  rCard: "24px",
  rInner: "16px",
  rTooth: "12px",
  rCheck: "7px",
  rPill: "999px",

  shadowApp: "0 30px 60px rgba(58,54,84,.25)",
  shadowCard: "0 10px 24px rgba(58,54,84,.08)",
  shadowPrimary: "0 10px 22px rgba(123,111,214,.45)",
  shadowHero: "0 20px 40px rgba(109,95,208,.4)",
  shadowPink: "0 16px 32px rgba(247,109,157,.35)",
} as const;

/** FDI tooth status catalogue (id, ka label, fill color, ink, optional border). */
export type ToothStatusId =
  | "healthy"
  | "caries"
  | "filled"
  | "crown"
  | "root"
  | "implant"
  | "missing"
  | "extract"
  | "other";

export interface ToothStatus {
  id: ToothStatusId;
  label: string;
  color: string;
  ink: string;
  border?: string;
}

export const STATUSES: ToothStatus[] = [
  { id: "healthy", label: "ჯანმრთელი", color: "#ffffff", ink: "#3a3654", border: "#e3e1f0" },
  { id: "caries", label: "კარიესი", color: "#f76d9d", ink: "#fff" },
  { id: "filled", label: "დაბჟენილი", color: "#7b6fd6", ink: "#fff" },
  { id: "crown", label: "გვირგვინი", color: "#f5c351", ink: "#3a3654" },
  { id: "root", label: "არხის მკურნალობა", color: "#9d8df1", ink: "#fff" },
  { id: "implant", label: "იმპლანტი", color: "#b3b0c9", ink: "#fff" },
  { id: "missing", label: "არ არის", color: "#3a3654", ink: "#fff" },
  { id: "extract", label: "ამოსაღები", color: "#fb9d5b", ink: "#fff" },
  { id: "other", label: "სხვა", color: "#e3e1f0", ink: "#3a3654" },
];

export const statusById = (id: ToothStatusId): ToothStatus =>
  STATUSES.find((s) => s.id === id) ?? STATUSES[0];

/** FDI numbering: upper 18→11 & 21→28, lower 48→41 & 31→38. */
export const FDI = {
  q1: [18, 17, 16, 15, 14, 13, 12, 11],
  q2: [21, 22, 23, 24, 25, 26, 27, 28],
  q4: [48, 47, 46, 45, 44, 43, 42, 41],
  q3: [31, 32, 33, 34, 35, 36, 37, 38],
} as const;
