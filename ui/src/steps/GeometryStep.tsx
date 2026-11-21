import { NumberField } from "../components/Field";
import { BeamDiagram } from "../components/BeamDiagram";
import { SectionView } from "../components/SectionView";
import { Beam3D } from "../components/Beam3D";
import type { BeamInput } from "../model";

interface Props {
  beam: BeamInput;
  update: (patch: Partial<BeamInput>) => void;
}

export function GeometryStep({ beam, update }: Props) {
  const coverTooBig = beam.cover_mm >= beam.h_mm / 2;
  return (
    <div className="step-grid">
      <section className="card">
        <h2>Balk och stöd</h2>
        <NumberField
          label="Spännvidd"
          symbol="L"
          unit="m"
          step={0.1}
          value={beam.span_m}
          help="Teoretisk spännvidd mellan stödens centrum. EN 1992-1-1 5.3.2.2."
          onChange={(v) => update({ span_m: v })}
        />
        <p className="muted small">Fritt upplagd balk. Konsoler och kontinuerliga balkar kommer senare.</p>

        <h2>Tvärsnitt</h2>
        <div className="row">
          <NumberField label="Bredd" symbol="b" unit="mm" step={10} value={beam.b_mm} onChange={(v) => update({ b_mm: v })} />
          <NumberField label="Höjd" symbol="h" unit="mm" step={10} value={beam.h_mm} onChange={(v) => update({ h_mm: v })} />
        </div>

        <h2>Täckande betongskikt</h2>
        <NumberField
          label="Täckskikt"
          symbol="c_{nom}"
          unit="mm"
          value={beam.cover_mm}
          help="c_nom = c_min + Δc_dev. EN 1992-1-1 4.4.1. Beräknas från exponeringsklass i en senare version."
          onChange={(v) => update({ cover_mm: v })}
        />
        {coverTooBig && <p className="warning">Täckskiktet är större än halva höjden.</p>}
      </section>

      <section className="card visual">
        <h2>Balkvy</h2>
        <BeamDiagram span_m={beam.span_m} />
        <div className="visual-row">
          <div>
            <h2>Tvärsnitt</h2>
            <SectionView b_mm={beam.b_mm} h_mm={beam.h_mm} cover_mm={beam.cover_mm} />
          </div>
          <div className="grow">
            <h2>3D</h2>
            <Beam3D span_m={beam.span_m} b_mm={beam.b_mm} h_mm={beam.h_mm} cover_mm={beam.cover_mm} />
          </div>
        </div>
      </section>
    </div>
  );
}
