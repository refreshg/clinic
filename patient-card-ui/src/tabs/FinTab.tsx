import { T } from "../theme";
import { Card, CardTitle, LabelValueGrid, StatCard } from "../components/ui";
import type { DemoData } from "../data/demo";

export function FinTab({ data }: { data: DemoData }) {
  const f = data.financials;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 22 }}>
      <div className="dc-grid-3">
        <StatCard label="დავალიანება" value={f.debt} variant="primary" />
        <StatCard label="ავანსი" value={f.advance} variant="pink" />
        <StatCard label="სულ ინვოისები" value={f.totalInvoiced} variant="white" />
      </div>

      <div className="dc-grid-2">
        <Card>
          <CardTitle>გადახდა და ლოიალობა</CardTitle>
          <LabelValueGrid
            rows={[
              { label: "გადახდის პირობები", value: f.paymentTerms, muted: f.paymentTerms === "—" },
              { label: "სასურველი მეთოდი", value: f.preferredMethod, muted: f.preferredMethod === "—" },
              { label: "ფასდაკლება (%)", value: f.discountPercent },
              { label: "ფასდაკლება (თანხა)", value: f.discountAmount },
              { label: "ლოიალობის სტატუსი", value: f.loyalty, muted: f.loyalty === "არ არის" },
            ]}
          />
        </Card>

        <Card>
          <CardTitle>დაზღვევა</CardTitle>
          <LabelValueGrid
            rows={[
              { label: "კომპანია", value: f.insuranceCompany, muted: f.insuranceCompany === "—" },
              { label: "პოლისის ნომერი", value: f.policyNo },
              { label: "ვადა", value: f.insuranceValidUntil },
              { label: "შენიშვნები", value: f.insuranceNotes },
            ]}
          />
        </Card>
      </div>

      <Card>
        <CardTitle>ინვოისები და გადახდები</CardTitle>
        <div
          style={{
            background: T.bgSoft,
            borderRadius: T.rInner,
            padding: 32,
            textAlign: "center",
            color: T.textMuted,
            fontSize: 13,
          }}
        >
          ინვოისები ჯერ არ არის — პირველი ინვოისი შეიქმნება ვიზიტის დასრულებისას
        </div>
      </Card>
    </div>
  );
}
