import { T, type ToothStatusId } from "../theme";
import { Card, CardTitle, LabelValueGrid } from "../components/ui";
import { ToggleCard } from "../components/CheckRow";
import { ToothChart, type TeethState } from "../components/ToothChart";
import type { DemoData } from "../data/demo";

export type MedFlagKey = keyof DemoData["medFlags"];

const MED_LABELS: { key: MedFlagKey; label: string }[] = [
  { key: "smoker", label: "მწეველი" },
  { key: "alcohol", label: "ალკოჰოლი" },
  { key: "blood", label: "სისხლის შედედება" },
  { key: "cardio", label: "კარდიო რისკი" },
];

interface Props {
  data: DemoData;
  flags: DemoData["medFlags"];
  onToggleFlag: (key: MedFlagKey) => void;
  brush: ToothStatusId;
  teeth: TeethState;
  onBrush: (id: ToothStatusId) => void;
  onPaint: (num: number) => void;
  onRemoveTooth: (num: number) => void;
}

/** Imaging chip (✓ რენტგენი / ✓ კტ / აქ გადაღებული). */
function ImgChip({ on, children }: { on: boolean; children: string }) {
  return (
    <span
      style={{
        background: on ? T.bgChip : T.bgSoft,
        color: on ? T.primaryDark : T.textMuted,
        borderRadius: T.rPill,
        padding: "6px 14px",
        fontSize: 12,
        fontWeight: 700,
      }}
    >
      {on ? "✓ " : ""}
      {children}
    </span>
  );
}

export function MedTab({ data, flags, onToggleFlag, brush, teeth, onBrush, onPaint, onRemoveTooth }: Props) {
  const a = data.allergy;
  const an = data.anamnesis;
  const d = data.dental;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 22 }}>
      {/* 4 toggle cards */}
      <div className="dc-grid-4">
        {MED_LABELS.map((f) => (
          <ToggleCard key={f.key} label={f.label} on={flags[f.key]} onToggle={() => onToggleFlag(f.key)} />
        ))}
      </div>

      <div className="dc-grid-1p2-08">
        {/* allergies + anamnesis */}
        <Card>
          <CardTitle>ალერგიები და ანამნეზი</CardTitle>
          <div
            style={{
              background: "#fdf2f6",
              borderRadius: T.rInner,
              padding: "14px 18px",
              display: "flex",
              gap: 14,
              alignItems: "center",
              marginBottom: 16,
            }}
          >
            <span
              style={{
                width: 34,
                height: 34,
                borderRadius: 12,
                background: T.pink,
                color: "#fff",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 15,
                flex: "none",
                fontWeight: 800,
              }}
            >
              !
            </span>
            <div style={{ fontSize: 13 }}>
              <b>{a.title}</b> · რეაქცია: {a.reaction} · სიმძიმე: {a.severity}
              <div style={{ color: "#c2748f", fontSize: 12, marginTop: 2 }}>{a.note}</div>
            </div>
          </div>
          <LabelValueGrid
            rows={[
              { label: "ქრონიკული დაავადებები", value: an.chronicDiseases },
              { label: "მიმდ. მედიკამენტები", value: an.medications },
              { label: "ოჯახური ანამნეზი", value: an.familyHistory, muted: an.familyHistory === "—" },
            ]}
          />
        </Card>

        {/* dental gradient card + imaging */}
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div
            style={{
              background: "linear-gradient(135deg,#8478e0,#6d5fd0)",
              borderRadius: T.rCard,
              padding: "22px 24px",
              color: "#fff",
              boxShadow: T.shadowHero.replace(".4)", ".35)"),
            }}
          >
            <div style={{ fontSize: 14, fontWeight: 800, marginBottom: 12 }}>სტომატოლოგია</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 8, fontSize: 13 }}>
              <Line label="ბოლო ვიზიტი" value={<b>{d.lastVisit}</b>} />
              <Line label="ბრუქსიზმი" value={<b>{d.bruxism}</b>} />
              <Line
                label="პაროდონტიტის რისკი"
                value={
                  <span style={{ background: T.pink, borderRadius: T.rPill, padding: "2px 10px", fontSize: 11, fontWeight: 700 }}>
                    {d.periodontitisRisk}
                  </span>
                }
              />
              <Line label="განახლდა" value={<b>{d.updatedAt}</b>} />
            </div>
          </div>

          <Card pad="22px 24px">
            <CardTitle>გამოსახულება</CardTitle>
            <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
              <ImgChip on={d.hasXray}>რენტგენი</ImgChip>
              <ImgChip on={d.hasCt}>კტ</ImgChip>
              <ImgChip on={false}>{d.imagingSource}</ImgChip>
            </div>
          </Card>
        </div>
      </div>

      <ToothChart brush={brush} teeth={teeth} onBrush={onBrush} onPaint={onPaint} onRemove={onRemoveTooth} />
    </div>
  );
}

function Line({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
      <span style={{ opacity: 0.7 }}>{label}</span>
      {value}
    </div>
  );
}
