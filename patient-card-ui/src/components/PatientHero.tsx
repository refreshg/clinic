import { T } from "../theme";
import type { Patient } from "../data/demo";

/** Gradient hero card: avatar, name + chips, meta rows, two right-side stats. */
export function PatientHero({ patient }: { patient: Patient }) {
  return (
    <div
      style={{
        background: T.primaryGrad,
        borderRadius: 28,
        padding: "28px 32px",
        color: "#fff",
        display: "flex",
        gap: 28,
        alignItems: "center",
        flexWrap: "wrap",
        boxShadow: T.shadowHero,
      }}
    >
      <div
        style={{
          width: 84,
          height: 84,
          borderRadius: 26,
          background: "rgba(255,255,255,.18)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: 34,
          fontWeight: 800,
          flex: "none",
          backdropFilter: "blur(4px)",
        }}
      >
        {patient.initials}
      </div>

      <div style={{ flex: 1, minWidth: 240 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
          <div style={{ fontSize: 24, fontWeight: 800 }}>
            {patient.firstName} {patient.lastName}
          </div>
          {patient.isRepeat && (
            <span style={{ background: T.pink, borderRadius: T.rPill, padding: "4px 12px", fontSize: 11, fontWeight: 700 }}>
              განმეორებითი
            </span>
          )}
          <span style={{ background: "rgba(255,255,255,.16)", borderRadius: T.rPill, padding: "4px 12px", fontSize: 11, fontWeight: 700 }}>
            {patient.ref}
          </span>
        </div>

        <div style={{ display: "flex", gap: 20, flexWrap: "wrap", fontSize: 13, marginTop: 10, opacity: 0.85 }}>
          <span>
            {patient.birthDate} · {patient.age} წ.
          </span>
          <span>პ/ნ {patient.personalNo}</span>
          <span>{patient.phone}</span>
          <span>{patient.email}</span>
        </div>
        <div style={{ fontSize: 12, marginTop: 6, opacity: 0.65 }}>
          {patient.address} · წყარო: {patient.referralSource} · რეგ. {patient.registeredAt}
        </div>
      </div>

      <div style={{ display: "flex", gap: 24, flex: "none" }}>
        <div style={{ textAlign: "left" }}>
          <div style={{ fontSize: 11, opacity: 0.65 }}>დავალიანება</div>
          <div style={{ fontSize: 22, fontWeight: 800 }}>{patient.debt}</div>
        </div>
        <div style={{ textAlign: "left" }}>
          <div style={{ fontSize: 11, opacity: 0.65 }}>ბოლო ვიზიტი</div>
          <div style={{ fontSize: 22, fontWeight: 800 }}>{patient.lastVisitShort}</div>
        </div>
      </div>
    </div>
  );
}
