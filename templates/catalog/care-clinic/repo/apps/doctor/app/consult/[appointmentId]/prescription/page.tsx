"use client";

import { use, useState } from "react";
import { useRouter } from "next/navigation";
import { Lock, Pill, Plus, ShieldCheck, Trash2 } from "lucide-react";
import { defaultApiClient } from "@careclinic/shared";
import { Shell } from "../../../../components/shell";
import { ConsultFrame, BackToQueue } from "../../../../components/consult-frame";
import { Panel, Badge, Button, DataState, ErrorNote, Field, inputClass } from "../../../../components/ui";
import { useApi, useAction } from "../../../../lib/use-api";
import { useSession } from "../../../../lib/session";
import { readFrequency, stamp, titleCase } from "../../../../lib/format";

interface Draft {
  medicineName: string;
  genericName: string;
  dosageForm: string;
  strength: string;
  frequency: string;
  timing: string;
  durationDays: number;
  instructions: string;
}

const EMPTY: Draft = {
  medicineName: "",
  genericName: "",
  dosageForm: "tablet",
  strength: "",
  frequency: "1-0-1",
  timing: "after_food",
  durationDays: 7,
  instructions: "",
};

// The vocabularies the database enforces (migrations/003_clinical.sql).
const FORMS = ["tablet", "capsule", "syrup", "injection", "inhaler", "drops", "ointment"];
const TIMINGS = ["after_food", "before_food", "with_food", "empty_stomach", "as_needed"];
const FREQUENCIES = ["1-0-0", "0-0-1", "1-0-1", "1-1-1", "0-1-0", "1-1-0", "SOS"];

export default function PrescriptionBuilder({ params }: { params: Promise<{ appointmentId: string }> }) {
  const { appointmentId } = use(params);
  const router = useRouter();
  const { notify } = useSession();
  const context = useApi(() => defaultApiClient.getConsultContext(appointmentId), [appointmentId]);
  const { run, busy, error } = useAction();

  const [items, setItems] = useState<Draft[]>([]);
  const [draft, setDraft] = useState<Draft>(EMPTY);
  const [summary, setSummary] = useState("");

  function addDraft() {
    if (!draft.medicineName.trim() || !draft.strength.trim()) return;
    setItems((current) => [...current, draft]);
    setDraft(EMPTY);
  }

  async function sign(diagnosisSummary: string) {
    const ok = await run(async () => {
      await defaultApiClient.issuePrescription(appointmentId, {
        diagnosisSummary,
        items: items.map((item) => ({
          medicineName: item.medicineName.trim(),
          genericName: item.genericName.trim() || undefined,
          dosageForm: item.dosageForm,
          strength: item.strength.trim(),
          frequency: item.frequency,
          timing: item.timing,
          durationDays: item.durationDays,
          instructions: item.instructions.trim() || undefined,
        })),
      });
      context.refresh();
    });
    if (ok) {
      notify({ title: "Prescription signed", detail: "It cannot be edited after this", tone: "good" });
      setItems([]);
      router.push(`/consult/${appointmentId}`);
    }
  }

  return (
    <Shell title="Prescription" subtitle="Signed once, then locked" actions={<BackToQueue />}>
      {error && <div className="mb-3"><ErrorNote message={error} /></div>}

      <DataState state={context}>
        {(data) => {
          const existing = data.prescription;
          const diagnosisSummary =
            summary ||
            data.diagnoses.find((d) => d.is_primary)?.condition_name ||
            data.diagnoses[0]?.condition_name ||
            data.consultation?.assessment ||
            "";

          if (existing) {
            return (
              <ConsultFrame context={data} appointmentId={appointmentId}>
                <Panel
                  title={`Prescription ${existing.prescription_number}`}
                  subtitle={`Signed ${stamp(existing.signed_at)}`}
                  actions={existing.is_immutable ? <Badge tone="good"><Lock size={11} /> Locked</Badge> : undefined}
                >
                  <p className="text-[13px] text-[var(--color-ink)]">
                    <span className="font-semibold">For: </span>
                    {existing.diagnosis_summary}
                  </p>

                  <ul className="mt-3 divide-y divide-[var(--color-border)] rounded-lg border border-[var(--color-border)]">
                    {data.prescriptionItems.map((item) => (
                      <li key={item.id} className="px-3 py-2.5">
                        <div className="flex flex-wrap items-baseline justify-between gap-2">
                          <p className="text-[13px] font-semibold text-[var(--color-ink)]">
                            {item.medicine_name} {item.strength}
                          </p>
                          <span className="tabular text-[12px] text-[var(--color-ink-muted)]">
                            {item.frequency} · {item.duration_days} days
                          </span>
                        </div>
                        <p className="text-[12px] text-[var(--color-ink-muted)]">
                          {titleCase(item.dosage_form)} · {readFrequency(item.frequency)} ·{" "}
                          {titleCase(item.timing)}
                        </p>
                        {item.instructions && (
                          <p className="mt-0.5 text-[11.5px] text-[var(--color-ink-subtle)]">{item.instructions}</p>
                        )}
                      </li>
                    ))}
                  </ul>

                  <p className="mt-3 flex items-center gap-1.5 text-[11.5px] text-[var(--color-ink-muted)]">
                    <ShieldCheck size={13} className="text-emerald-600" />
                    Digitally signed. A correction is a new prescription, never an edit to this one.
                  </p>
                </Panel>
              </ConsultFrame>
            );
          }

          return (
            <ConsultFrame context={data} appointmentId={appointmentId}>
              <div className="grid gap-3 lg:grid-cols-[1fr_1fr]">
                <Panel title="Add a medicine">
                  <div className="space-y-3">
                    <Field label="Medicine">
                      <input
                        className={inputClass}
                        value={draft.medicineName}
                        onChange={(event) => setDraft({ ...draft, medicineName: event.target.value })}
                        placeholder="Brand or generic name"
                      />
                    </Field>
                    <div className="grid grid-cols-2 gap-2">
                      <Field label="Strength">
                        <input
                          className={inputClass}
                          value={draft.strength}
                          onChange={(event) => setDraft({ ...draft, strength: event.target.value })}
                          placeholder="500mg"
                        />
                      </Field>
                      <Field label="Form">
                        <select
                          className={inputClass}
                          value={draft.dosageForm}
                          onChange={(event) => setDraft({ ...draft, dosageForm: event.target.value })}
                        >
                          {FORMS.map((form) => (
                            <option key={form} value={form}>
                              {titleCase(form)}
                            </option>
                          ))}
                        </select>
                      </Field>
                    </div>
                    <div className="grid grid-cols-3 gap-2">
                      <Field label="Frequency">
                        <select
                          className={inputClass}
                          value={draft.frequency}
                          onChange={(event) => setDraft({ ...draft, frequency: event.target.value })}
                        >
                          {FREQUENCIES.map((frequency) => (
                            <option key={frequency} value={frequency}>
                              {frequency}
                            </option>
                          ))}
                        </select>
                      </Field>
                      <Field label="Timing">
                        <select
                          className={inputClass}
                          value={draft.timing}
                          onChange={(event) => setDraft({ ...draft, timing: event.target.value })}
                        >
                          {TIMINGS.map((timing) => (
                            <option key={timing} value={timing}>
                              {titleCase(timing)}
                            </option>
                          ))}
                        </select>
                      </Field>
                      <Field label="Days">
                        <input
                          className={inputClass}
                          type="number"
                          min={1}
                          max={180}
                          value={draft.durationDays}
                          onChange={(event) => setDraft({ ...draft, durationDays: Number(event.target.value) })}
                        />
                      </Field>
                    </div>
                    <Field label="Instructions" hint="Printed on the slip for the patient.">
                      <input
                        className={inputClass}
                        value={draft.instructions}
                        onChange={(event) => setDraft({ ...draft, instructions: event.target.value })}
                        placeholder="Take with warm water"
                      />
                    </Field>

                    <p className="text-[11.5px] text-[var(--color-ink-muted)]">
                      {draft.frequency === "SOS"
                        ? "As needed"
                        : `${readFrequency(draft.frequency)}, ${titleCase(draft.timing).toLowerCase()}`}
                      {draft.durationDays ? `, for ${draft.durationDays} days` : ""}.
                    </p>

                    <Button variant="quiet" onClick={addDraft} disabled={!draft.medicineName.trim() || !draft.strength.trim()}>
                      <Plus size={13} /> Add to the prescription
                    </Button>
                  </div>
                </Panel>

                <Panel title="The prescription" subtitle={`${items.length} medicine${items.length === 1 ? "" : "s"}`}>
                  {data.medicalHistory.allergies?.length > 0 && (
                    <p className="mb-3 rounded-lg border border-red-200 bg-red-50 px-2.5 py-1.5 text-[12px] text-red-800">
                      Allergic to {data.medicalHistory.allergies.join(", ")}
                    </p>
                  )}

                  <Field label="Written for">
                    <input
                      className={inputClass}
                      value={diagnosisSummary}
                      onChange={(event) => setSummary(event.target.value)}
                      placeholder="The condition this prescription treats"
                    />
                  </Field>

                  {items.length === 0 ? (
                    <p className="mt-3 flex items-center gap-2 py-8 text-center text-[12.5px] text-[var(--color-ink-muted)]">
                      <Pill size={15} className="text-slate-400" /> Nothing added yet.
                    </p>
                  ) : (
                    <ul className="mt-3 divide-y divide-[var(--color-border)] rounded-lg border border-[var(--color-border)]">
                      {items.map((item, index) => (
                        <li key={`${item.medicineName}-${index}`} className="flex items-start justify-between gap-2 px-3 py-2.5">
                          <div className="min-w-0">
                            <p className="text-[12.5px] font-semibold text-[var(--color-ink)]">
                              {item.medicineName} {item.strength}
                            </p>
                            <p className="text-[11.5px] text-[var(--color-ink-muted)]">
                              {titleCase(item.dosageForm)} · {item.frequency} · {titleCase(item.timing)} ·{" "}
                              {item.durationDays} days
                            </p>
                          </div>
                          <button
                            onClick={() => setItems((current) => current.filter((_, i) => i !== index))}
                            aria-label="Remove"
                            className="shrink-0 text-slate-400 hover:text-red-600"
                          >
                            <Trash2 size={14} />
                          </button>
                        </li>
                      ))}
                    </ul>
                  )}

                  <div className="mt-4 border-t border-[var(--color-border)] pt-3">
                    <Button
                      disabled={busy || items.length === 0 || !diagnosisSummary.trim() || !data.consultation}
                      onClick={() => void sign(diagnosisSummary.trim())}
                    >
                      <ShieldCheck size={13} /> {busy ? "Signing" : "Sign and issue"}
                    </Button>
                    <p className="mt-1.5 text-[11.5px] text-[var(--color-ink-muted)]">
                      Signing locks the prescription. The patient can read it immediately.
                    </p>
                  </div>
                </Panel>
              </div>
            </ConsultFrame>
          );
        }}
      </DataState>
    </Shell>
  );
}
