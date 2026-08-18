import { useState } from "react";
import type { ToothStatusId } from "./theme";
import { demo, type ContactRow, type Procedure } from "./data/demo";
import { Sidebar } from "./components/Sidebar";
import { TopBar } from "./components/TopBar";
import { PatientHero } from "./components/PatientHero";
import { PillTabs, type TabId } from "./components/PillTabs";
import { MainTab, type MainFlagKey } from "./tabs/MainTab";
import { MedTab, type MedFlagKey } from "./tabs/MedTab";
import { FinTab } from "./tabs/FinTab";
import { HistTab } from "./tabs/HistTab";

export function App() {
  // ── local UI state ──────────────────────────────────────────────
  const [tab, setTab] = useState<TabId>("main");
  const [brush, setBrush] = useState<ToothStatusId>("caries");
  const [teeth, setTeeth] = useState(demo.teeth);
  const [mainFlags, setMainFlags] = useState(demo.mainFlags);
  const [medFlags, setMedFlags] = useState(demo.medFlags);
  const [contacts, setContacts] = useState<ContactRow[]>(demo.contacts);
  const [procedures, setProcedures] = useState<Procedure[]>(demo.procedures);
  const [note, setNote] = useState("");

  // ── handlers ────────────────────────────────────────────────────
  const toggleMain = (k: MainFlagKey) => setMainFlags((s) => ({ ...s, [k]: !s[k] }));
  const toggleMed = (k: MedFlagKey) => setMedFlags((s) => ({ ...s, [k]: !s[k] }));

  const paintTooth = (num: number) =>
    setTeeth((s) => ({ ...s, [num]: { status: brush, note: s[num]?.note ?? "" } }));
  const removeTooth = (num: number) =>
    setTeeth((s) => {
      const next = { ...s };
      delete next[num];
      return next;
    });

  const removeContact = (id: number) => setContacts((s) => s.filter((c) => c.id !== id));
  const addContact = () =>
    setContacts((s) => [
      ...s,
      { id: Math.max(0, ...s.map((c) => c.id)) + 1, isPrimary: false, phone: "", countryCode: "+995", type: "მობილური", channel: "—", isEmergency: false, relation: "—" },
    ]);

  const removeProcedure = (id: number) => setProcedures((s) => s.filter((p) => p.id !== id));
  const addProcedure = () =>
    setProcedures((s) => [
      ...s,
      { id: Math.max(0, ...s.map((p) => p.id)) + 1, status: "დაგეგმილი", name: "—", qty: "1.00", date: "—", performer: "clinic", tooth: "—" },
    ]);
  const addDocument = () => {
    /* placeholder — wire to a document picker / API later */
  };

  return (
    <div className="dc-page">
      <div className="dc-app">
        <Sidebar />
        <div className="dc-main">
          <TopBar />
          <PatientHero patient={demo.patient} />
          <PillTabs active={tab} onChange={setTab} />

          {tab === "main" && (
            <MainTab
              data={demo}
              flags={mainFlags}
              onToggleFlag={toggleMain}
              contacts={contacts}
              onRemoveContact={removeContact}
              onAddContact={addContact}
              note={note}
              onNote={setNote}
            />
          )}
          {tab === "med" && (
            <MedTab
              data={demo}
              flags={medFlags}
              onToggleFlag={toggleMed}
              brush={brush}
              teeth={teeth}
              onBrush={setBrush}
              onPaint={paintTooth}
              onRemoveTooth={removeTooth}
            />
          )}
          {tab === "fin" && <FinTab data={demo} />}
          {tab === "hist" && (
            <HistTab
              data={demo}
              procedures={procedures}
              onRemoveProcedure={removeProcedure}
              onAddProcedure={addProcedure}
              onAddDocument={addDocument}
            />
          )}
        </div>
      </div>
    </div>
  );
}
