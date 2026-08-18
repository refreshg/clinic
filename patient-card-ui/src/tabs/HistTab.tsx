import { T } from "../theme";
import { Card, CardTitle, AddButton, ProgressStat } from "../components/ui";
import { ProcedureRow, DocumentRow } from "../components/Rows";
import type { DemoData, Procedure } from "../data/demo";

interface Props {
  data: DemoData;
  procedures: Procedure[];
  onRemoveProcedure: (id: number) => void;
  onAddProcedure: () => void;
  onAddDocument: () => void;
}

export function HistTab({ data, procedures, onRemoveProcedure, onAddProcedure, onAddDocument }: Props) {
  const pr = data.profile;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 22 }}>
      <Card>
        <CardTitle action={<AddButton onClick={onAddProcedure} />}>პროცედურები</CardTitle>
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {procedures.length === 0 && (
            <div style={{ background: T.bgSoft, borderRadius: T.rInner, padding: 18, textAlign: "center", color: T.textMuted, fontSize: 13 }}>
              პროცედურა ჯერ არ არის.
            </div>
          )}
          {procedures.map((p) => (
            <ProcedureRow key={p.id} p={p} onRemove={onRemoveProcedure} />
          ))}
        </div>
      </Card>

      <div className="dc-grid-1p2-08">
        <Card>
          <CardTitle action={<AddButton onClick={onAddDocument} />}>დოკუმენტები</CardTitle>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {data.documents.map((d) => (
              <DocumentRow key={d.id} d={d} />
            ))}
          </div>
        </Card>

        <Card>
          <CardTitle>პაციენტის პროფილი</CardTitle>
          <div style={{ display: "flex", flexDirection: "column", gap: 12, fontSize: 13 }}>
            <ProgressStat label="გაცდენების %" value={pr.noShowLabel} percent={pr.noShowRate} color={T.primary} />
            <ProgressStat label="LTV პროგნოზი" value={pr.ltvLabel} percent={pr.ltvPercent} color={T.pink} />
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ color: T.textMuted }}>რისკის დონე</span>
              <span style={{ color: T.textMuted }}>{pr.riskLevel}</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ color: T.textMuted }}>რისკის დეტალები</span>
              <span style={{ color: T.textMuted }}>{pr.riskNotes}</span>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
