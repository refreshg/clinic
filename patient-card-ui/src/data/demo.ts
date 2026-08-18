/**
 * Typed demo data for the patient card. Values mirror the design reference
 * (docs/design_handoff_patient_card/reference-design.html). Replace this whole
 * module with an API-backed loader later — the shapes match the intended
 * Odoo (res.partner + related) fields.
 */
import type { ToothStatusId } from "../theme";

export interface Patient {
  firstName: string;
  lastName: string;
  initials: string;
  ref: string; // patient_ref, e.g. P000002
  isRepeat: boolean;
  latinName: string;
  birthDate: string; // 24.08.1982
  age: number;
  personalNo: string; // vat / პ/ნ
  phone: string;
  email: string;
  address: string;
  citizenship: string;
  gender: string;
  referralSource: string;
  guardian: string;
  registeredAt: string;
  debt: string; // formatted ₾ 0.00
  lastVisitShort: string; // 3 ივლ
}

export interface ContactRow {
  id: number;
  isPrimary: boolean;
  phone: string;
  countryCode: string;
  type: string; // მობილური
  channel: string; // ზარი
  isEmergency: boolean;
  relation: string; // — or a relation
}

export interface Allergy {
  title: string; // მედიკამენტი — ანესთეტიკი
  reaction: string; // არა
  severity: string; // მსუბუქი
  note: string;
}

export interface Anamnesis {
  chronicDiseases: string;
  medications: string;
  familyHistory: string;
}

export interface DentalSummary {
  lastVisit: string;
  bruxism: string;
  periodontitisRisk: string; // საშუალო
  updatedAt: string;
  hasXray: boolean;
  hasCt: boolean;
  imagingSource: string; // აქ გადაღებული
}

export interface Financials {
  debt: string;
  advance: string;
  totalInvoiced: string;
  paymentTerms: string;
  preferredMethod: string;
  discountPercent: string;
  discountAmount: string;
  loyalty: string;
  insuranceCompany: string;
  policyNo: string;
  insuranceValidUntil: string;
  insuranceNotes: string;
}

export interface Procedure {
  id: number;
  status: string; // დაგეგმილი
  name: string; // — when empty
  qty: string; // 1.00
  date: string; // 30 ივლ
  performer: string; // clinic
  tooth: string; // 32
}

export interface DocumentRecord {
  id: number;
  title: string; // თანხმობის ფორმა #444
  date: string; // 5 აგვ
  note: string; // შენიშვნა
  href: string;
}

export interface Profile {
  noShowRate: number; // percent 0..100
  noShowLabel: string; // 0.00
  ltvPercent: number; // for the bar width proxy
  ltvLabel: string; // 0.00
  riskLevel: string;
  riskNotes: string;
}

export interface DemoData {
  patient: Patient;
  contacts: ContactRow[];
  allergy: Allergy;
  anamnesis: Anamnesis;
  dental: DentalSummary;
  financials: Financials;
  procedures: Procedure[];
  documents: DocumentRecord[];
  profile: Profile;
  /** Initial FDI teeth state: 18 healthy, 44 extract (per spec). */
  teeth: Record<number, { status: ToothStatusId; note: string }>;
  mainFlags: { foreign: boolean; first: boolean; repeat: boolean; permanent: boolean; minor: boolean };
  medFlags: { smoker: boolean; alcohol: boolean; blood: boolean; cardio: boolean };
}

export const demo: DemoData = {
  patient: {
    firstName: "გიორგი",
    lastName: "ბიჭაშვილი",
    initials: "გბ",
    ref: "P000002",
    isRepeat: true,
    latinName: "giorgi bichashvili",
    birthDate: "24.08.1982",
    age: 43,
    personalNo: "01027020520",
    phone: "577 00 62 00",
    email: "giorgi.b1982@gmail.com",
    address: "ჭავჭავაძის 83, თბილისი 0160",
    citizenship: "საქართველო",
    gender: "მამრობითი",
    referralSource: "Facebook",
    guardian: "დავით ჩახუნაშვილი",
    registeredAt: "30.07.2026",
    debt: "₾ 0.00",
    lastVisitShort: "3 ივლ",
  },
  contacts: [
    { id: 1, isPrimary: true, phone: "577 006 200", countryCode: "+995", type: "მობილური", channel: "ზარი", isEmergency: true, relation: "—" },
    { id: 2, isPrimary: false, phone: "599 593 434", countryCode: "+995", type: "მობილური", channel: "—", isEmergency: false, relation: "—" },
  ],
  allergy: {
    title: "მედიკამენტი — ანესთეტიკი",
    reaction: "არა",
    severity: "მსუბუქი",
    note: "განსაკუთრებული სიფრთხილე ანესთეზიისას",
  },
  anamnesis: {
    chronicDiseases: "ბიპოლარული აშლილობა",
    medications: "მძიმე ფსიქოტროპული",
    familyHistory: "—",
  },
  dental: {
    lastVisit: "3 ივლ, 2026",
    bruxism: "დიახ",
    periodontitisRisk: "საშუალო",
    updatedAt: "5 აგვ · clinic",
    hasXray: true,
    hasCt: true,
    imagingSource: "აქ გადაღებული",
  },
  financials: {
    debt: "₾ 0.00",
    advance: "₾ 0.00",
    totalInvoiced: "₾ 0.00",
    paymentTerms: "—",
    preferredMethod: "—",
    discountPercent: "0.00",
    discountAmount: "0.00",
    loyalty: "არ არის",
    insuranceCompany: "—",
    policyNo: "010101",
    insuranceValidUntil: "5 აგვ, 2026",
    insuranceNotes: "შენიშვნა",
  },
  procedures: [
    { id: 1, status: "დაგეგმილი", name: "—", qty: "1.00", date: "30 ივლ", performer: "clinic", tooth: "32" },
    { id: 2, status: "დაგეგმილი", name: "—", qty: "1.00", date: "5 აგვ", performer: "clinic", tooth: "55" },
  ],
  documents: [
    { id: 1, title: "თანხმობის ფორმა #444", date: "5 აგვ", note: "შენიშვნა", href: "#დოკ" },
  ],
  profile: {
    noShowRate: 3,
    noShowLabel: "0.00",
    ltvPercent: 3,
    ltvLabel: "0.00",
    riskLevel: "—",
    riskNotes: "—",
  },
  teeth: {
    18: { status: "healthy", note: "" },
    44: { status: "extract", note: "ამოღება დაგეგმილია" },
  },
  mainFlags: { foreign: false, first: false, repeat: true, permanent: false, minor: false },
  medFlags: { smoker: true, alcohol: true, blood: true, cardio: true },
};
