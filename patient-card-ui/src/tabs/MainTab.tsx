import { T } from "../theme";
import { Card, CardTitle, LabelValueGrid, AddButton } from "../components/ui";
import { CheckRow } from "../components/CheckRow";
import { ContactTable } from "../components/ContactTable";
import type { DemoData, ContactRow } from "../data/demo";

export type MainFlagKey = keyof DemoData["mainFlags"];

const FLAG_LABELS: { key: MainFlagKey; label: string }[] = [
  { key: "foreign", label: "უცხოელი პაციენტი" },
  { key: "first", label: "პირველადი ვიზიტი" },
  { key: "repeat", label: "განმეორებითი პაციენტი" },
  { key: "permanent", label: "მუდმივი პაციენტი" },
  { key: "minor", label: "არასრულწლოვანი" },
];

interface Props {
  data: DemoData;
  flags: DemoData["mainFlags"];
  onToggleFlag: (key: MainFlagKey) => void;
  contacts: ContactRow[];
  onRemoveContact: (id: number) => void;
  onAddContact: () => void;
  note: string;
  onNote: (v: string) => void;
}

export function MainTab({ data, flags, onToggleFlag, contacts, onRemoveContact, onAddContact, note, onNote }: Props) {
  const p = data.patient;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 22 }}>
      <div className="dc-grid-2">
        <Card>
          <CardTitle>ძირითადი ინფორმაცია</CardTitle>
          <LabelValueGrid
            rows={[
              { label: "სახელი (ლათინურად)", value: p.latinName },
              { label: "მოქალაქეობა", value: p.citizenship },
              { label: "სქესი", value: p.gender },
              { label: "მომართვის წყარო", value: p.referralSource },
              { label: "მეურვე / მშობელი", value: p.guardian },
            ]}
          />
        </Card>

        <Card>
          <CardTitle>სტატუსი</CardTitle>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {FLAG_LABELS.map((f) => (
              <CheckRow key={f.key} label={f.label} on={flags[f.key]} onToggle={() => onToggleFlag(f.key)} />
            ))}
          </div>
        </Card>
      </div>

      <Card>
        <CardTitle action={<AddButton onClick={onAddContact} />}>საკონტაქტო ინფორმაცია</CardTitle>
        <ContactTable rows={contacts} onRemove={onRemoveContact} />
      </Card>

      <Card>
        <CardTitle>შენიშვნა</CardTitle>
        <textarea
          value={note}
          onChange={(e) => onNote(e.target.value)}
          placeholder="შიდა შენიშვნა პაციენტზე…"
          style={{
            width: "100%",
            minHeight: 90,
            border: `2px solid ${T.borderSoft}`,
            borderRadius: T.rInner,
            padding: "14px 16px",
            fontFamily: "inherit",
            fontSize: 13.5,
            color: T.text,
            background: T.bgSoft,
            resize: "vertical",
            boxSizing: "border-box",
          }}
        />
      </Card>
    </div>
  );
}
