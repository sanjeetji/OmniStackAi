"use client";

import { use, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Check, Lock, Plus, Save, Search, X } from "lucide-react";
import { defaultApiClient, type Icd10Code } from "@careclinic/shared";
import { Shell } from "../../../../components/shell";
import { ConsultFrame, BackToQueue } from "../../../../components/consult-frame";
import { Panel, Badge, Button, DataState, ErrorNote, Field, inputClass } from "../../../../components/ui";
import { useApi, useAction } from "../../../../lib/use-api";
import { useSession } from "../../../../lib/session";

interface PickedDiagnosis {
  icd10Code: string;
  conditionName: string;
  isPrimary: boolean;
}

const SECTIONS = [
  {
    key: "subjective" as const,
    label: "Subjective",
    hint: "What the patient tells you: the complaint, how long, what makes it better or worse.",
    placeholder: "Reports…",
  },
  {
    key: "objective" as const,
    label: "Objective",
    hint: "What you find: the examination, the vitals you acted on, anything measured.",
    placeholder: "On examination…",
  },
  {
    key: "assessment" as const,
    label: "Assessment",
    hint: "Your clinical impression, and what you have ruled out.",
    placeholder: "Impression…",
  },
  {
    key: "plan" as const,
    label: "Plan",
    hint: "Treatment, advice, investigations and when to come back.",
    placeholder: "Plan…",
  },
];

export default function SoapNotes({ params }: { params: Promise<{ appointmentId: string }> }) {
  const { appointmentId } = use(params);
  const router = useRouter();
  const { notify } = useSession();
  const context = useApi(() => defaultApiClient.getConsultContext(appointmentId), [appointmentId]);
  const { run, busy, error } = useAction();

  const [notes, setNotes] = useState({ subjective: "", objective: "", assessment: "", plan: "" });
  const [followUp, setFollowUp] = useState("");
  const [picked, setPicked] = useState<PickedDiagnosis[]>([]);
  const [search, setSearch] = useState("");
  const [loaded, setLoaded] = useState(false);

  const codes = useApi(() => defaultApiClient.searchIcd10(search || undefined), [search]);

  useEffect(() => {
    const data = context.data;
    if (!data || loaded) return;
    setNotes({
      subjective: data.consultation?.subjective ?? "",
      objective: data.consultation?.objective ?? "",
      assessment: data.consultation?.assessment ?? "",
      plan: data.consultation?.plan ?? "",
    });
    setFollowUp(data.consultation?.follow_up_date ? String(data.consultation.follow_up_date).slice(0, 10) : "");
    setPicked(
      data.diagnoses.map((d) => ({
        icd10Code: d.icd10_code,
        conditionName: d.condition_name,
        isPrimary: d.is_primary,
      }))
    );
    setLoaded(true);
  }, [context.data, loaded]);

  function add(code: Icd10Code) {
    setPicked((current) =>
      current.some((d) => d.icd10Code === code.code)
        ? current
        : [
            ...current,
            { icd10Code: code.code, conditionName: code.condition_name, isPrimary: current.length === 0 },
          ]
    );
    setSearch("");
  }

  function remove(code: string) {
    setPicked((current) => {
      const next = current.filter((d) => d.icd10Code !== code);
      if (next.length > 0 && !next.some((d) => d.isPrimary)) next[0].isPrimary = true;
      return [...next];
    });
  }

  async function save() {
    const ok = await run(async () => {
      await defaultApiClient.saveSoapNotes(appointmentId, {
        ...notes,
        followUpDate: followUp || undefined,
        diagnoses: picked,
      });
      context.refresh();
    });
    if (ok) {
      notify({ title: "Notes saved", tone: "good" });
      router.push(`/consult/${appointmentId}`);
    }
  }

  const locked = Boolean(context.data?.consultation?.completed_at);

  return (
    <Shell title="SOAP notes" subtitle="Subjective, objective, assessment, plan" actions={<BackToQueue />}>
      {error && <div className="mb-3"><ErrorNote message={error} /></div>}

      <DataState state={context}>
        {(data) => (
          <ConsultFrame context={data} appointmentId={appointmentId}>
            {locked && (
              <div className="flex items-center gap-2 rounded-lg border border-[var(--color-border)] bg-slate-50 px-3 py-2 text-[12.5px] text-[var(--color-ink-muted)]">
                <Lock size={14} /> This consultation is completed. The notes are kept as written.
              </div>
            )}

            <div className="grid gap-3 lg:grid-cols-[1.5fr_1fr]">
              <Panel title="The note" subtitle="Saved together; the API keeps one note per consultation">
                <div className="space-y-4">
                  {SECTIONS.map((section) => (
                    <Field key={section.key} label={section.label} hint={section.hint}>
                      <textarea
                        className={`${inputClass} min-h-24 leading-relaxed`}
                        value={notes[section.key]}
                        placeholder={section.placeholder}
                        disabled={locked}
                        onChange={(event) => setNotes({ ...notes, [section.key]: event.target.value })}
                      />
                    </Field>
                  ))}

                  <Field label="Follow-up" hint="Leave blank if no review is needed.">
                    <input
                      className={inputClass}
                      type="date"
                      value={followUp}
                      disabled={locked}
                      onChange={(event) => setFollowUp(event.target.value)}
                    />
                  </Field>

                  {!locked && (
                    <Button disabled={busy || !notes.assessment.trim()} onClick={() => void save()}>
                      <Save size={13} /> {busy ? "Saving" : "Save the note"}
                    </Button>
                  )}
                </div>
              </Panel>

              <div className="space-y-3">
                <Panel title="Diagnosis" subtitle="ICD-10, searched from the clinic's catalogue">
                  {picked.length > 0 && (
                    <ul className="mb-3 space-y-1.5">
                      {picked.map((diagnosis) => (
                        <li
                          key={diagnosis.icd10Code}
                          className="flex items-start justify-between gap-2 rounded-lg border border-[var(--color-border)] px-2.5 py-1.5"
                        >
                          <div className="min-w-0">
                            <p className="text-[12.5px] font-medium text-[var(--color-ink)]">
                              {diagnosis.conditionName}
                            </p>
                            <p className="tabular text-[11px] text-[var(--color-ink-subtle)]">{diagnosis.icd10Code}</p>
                          </div>
                          <div className="flex shrink-0 items-center gap-1">
                            <button
                              onClick={() =>
                                setPicked((current) =>
                                  current.map((d) => ({ ...d, isPrimary: d.icd10Code === diagnosis.icd10Code }))
                                )
                              }
                              disabled={locked}
                              title="Mark as the primary diagnosis"
                              className={
                                diagnosis.isPrimary
                                  ? "rounded bg-sky-50 px-1.5 py-0.5 text-[11px] font-semibold text-sky-700 ring-1 ring-inset ring-sky-200"
                                  : "rounded px-1.5 py-0.5 text-[11px] text-slate-400 hover:text-slate-700"
                              }
                            >
                              {diagnosis.isPrimary ? "Primary" : "Set primary"}
                            </button>
                            {!locked && (
                              <button
                                onClick={() => remove(diagnosis.icd10Code)}
                                aria-label="Remove"
                                className="text-slate-400 hover:text-red-600"
                              >
                                <X size={13} />
                              </button>
                            )}
                          </div>
                        </li>
                      ))}
                    </ul>
                  )}

                  {!locked && (
                    <>
                      <div className="relative">
                        <Search size={14} className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
                        <input
                          className={`${inputClass} pl-8`}
                          placeholder="Search a condition or code"
                          value={search}
                          onChange={(event) => setSearch(event.target.value)}
                        />
                      </div>

                      <DataState state={codes}>
                        {(list) => (
                          <ul className="mt-2 max-h-72 divide-y divide-[var(--color-border)] overflow-y-auto rounded-lg border border-[var(--color-border)]">
                            {list.codes.map((code) => (
                              <li key={code.code}>
                                <button
                                  onClick={() => add(code)}
                                  className="flex w-full items-center justify-between gap-2 px-2.5 py-2 text-left hover:bg-slate-50"
                                >
                                  <div className="min-w-0">
                                    <p className="truncate text-[12.5px] text-[var(--color-ink)]">
                                      {code.condition_name}
                                    </p>
                                    <p className="tabular text-[11px] text-[var(--color-ink-subtle)]">
                                      {code.code} · {code.specialty ?? code.chapter}
                                    </p>
                                  </div>
                                  {picked.some((d) => d.icd10Code === code.code) ? (
                                    <Check size={14} className="shrink-0 text-emerald-600" />
                                  ) : (
                                    <Plus size={14} className="shrink-0 text-slate-400" />
                                  )}
                                </button>
                              </li>
                            ))}
                          </ul>
                        )}
                      </DataState>
                    </>
                  )}
                </Panel>

                {data.previousVisits.length > 0 && (
                  <Panel title="What you wrote last time" padded={false}>
                    <ul className="divide-y divide-[var(--color-border)]">
                      {data.previousVisits.slice(0, 3).map((visit) => (
                        <li key={visit.id} className="px-4 py-2.5">
                          <p className="text-[12.5px] font-medium text-[var(--color-ink)]">
                            {visit.assessment ?? "Consultation"}
                          </p>
                          {visit.plan && (
                            <p className="mt-0.5 text-[11.5px] leading-relaxed text-[var(--color-ink-muted)]">
                              {visit.plan}
                            </p>
                          )}
                        </li>
                      ))}
                    </ul>
                  </Panel>
                )}
              </div>
            </div>
          </ConsultFrame>
        )}
      </DataState>
    </Shell>
  );
}
