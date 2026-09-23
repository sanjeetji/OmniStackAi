/** Deterministic generator for the ICD-10 catalogue seed (seed/002_icd10.sql). */

function esc(value) {
  if (value === null || value === undefined) return "NULL";
  if (typeof value === "boolean") return value ? "TRUE" : "FALSE";
  return `'${String(value).replace(/'/g, "''")}'`;
}

// [code, condition, chapter, specialty, commonly used]
const CODES = [
  ["I10", "Essential (primary) hypertension", "Circulatory system", "Cardiology", true],
  ["I20.9", "Angina pectoris, unspecified", "Circulatory system", "Cardiology", true],
  ["I25.10", "Atherosclerotic heart disease without angina", "Circulatory system", "Cardiology", false],
  ["I48.91", "Atrial fibrillation, unspecified", "Circulatory system", "Cardiology", false],
  ["I50.9", "Heart failure, unspecified", "Circulatory system", "Cardiology", false],
  ["E11.9", "Type 2 diabetes mellitus without complications", "Endocrine and metabolic", "General Medicine", true],
  ["E11.65", "Type 2 diabetes mellitus with hyperglycaemia", "Endocrine and metabolic", "General Medicine", false],
  ["E03.9", "Hypothyroidism, unspecified", "Endocrine and metabolic", "General Medicine", true],
  ["E05.90", "Thyrotoxicosis, unspecified", "Endocrine and metabolic", "General Medicine", false],
  ["E78.5", "Hyperlipidaemia, unspecified", "Endocrine and metabolic", "General Medicine", true],
  ["E66.9", "Obesity, unspecified", "Endocrine and metabolic", "General Medicine", false],
  ["E55.9", "Vitamin D deficiency, unspecified", "Endocrine and metabolic", "General Medicine", true],
  ["D50.9", "Iron deficiency anaemia, unspecified", "Blood and immune", "General Medicine", true],
  ["D51.9", "Vitamin B12 deficiency anaemia, unspecified", "Blood and immune", "General Medicine", false],
  ["J06.9", "Acute upper respiratory infection, unspecified", "Respiratory system", "General Medicine", true],
  ["J02.9", "Acute pharyngitis, unspecified", "Respiratory system", "ENT", true],
  ["J01.90", "Acute sinusitis, unspecified", "Respiratory system", "ENT", true],
  ["J20.9", "Acute bronchitis, unspecified", "Respiratory system", "General Medicine", true],
  ["J45.909", "Unspecified asthma, uncomplicated", "Respiratory system", "General Medicine", true],
  ["J44.9", "Chronic obstructive pulmonary disease, unspecified", "Respiratory system", "General Medicine", false],
  ["J30.9", "Allergic rhinitis, unspecified", "Respiratory system", "ENT", true],
  ["K21.9", "Gastro-oesophageal reflux disease without oesophagitis", "Digestive system", "General Medicine", true],
  ["K29.70", "Gastritis, unspecified, without bleeding", "Digestive system", "General Medicine", true],
  ["K58.9", "Irritable bowel syndrome without diarrhoea", "Digestive system", "General Medicine", false],
  ["K59.00", "Constipation, unspecified", "Digestive system", "General Medicine", true],
  ["A09", "Infectious gastroenteritis and colitis, unspecified", "Infectious disease", "General Medicine", true],
  ["B34.9", "Viral infection, unspecified", "Infectious disease", "General Medicine", true],
  ["A90", "Dengue fever (classical dengue)", "Infectious disease", "General Medicine", true],
  ["B54", "Unspecified malaria", "Infectious disease", "General Medicine", false],
  ["A01.00", "Typhoid fever, unspecified", "Infectious disease", "General Medicine", false],
  ["N39.0", "Urinary tract infection, site not specified", "Genitourinary system", "General Medicine", true],
  ["N18.9", "Chronic kidney disease, unspecified", "Genitourinary system", "General Medicine", false],
  ["N20.0", "Calculus of kidney", "Genitourinary system", "General Medicine", false],
  ["M54.5", "Low back pain", "Musculoskeletal", "Orthopaedics", true],
  ["M54.2", "Cervicalgia (neck pain)", "Musculoskeletal", "Orthopaedics", true],
  ["M17.9", "Osteoarthritis of knee, unspecified", "Musculoskeletal", "Orthopaedics", true],
  ["M25.511", "Pain in right shoulder", "Musculoskeletal", "Orthopaedics", false],
  ["M79.7", "Fibromyalgia", "Musculoskeletal", "Orthopaedics", false],
  ["M81.0", "Age-related osteoporosis without fracture", "Musculoskeletal", "Orthopaedics", false],
  ["L20.9", "Atopic dermatitis, unspecified", "Skin", "Dermatology", true],
  ["L30.9", "Dermatitis, unspecified", "Skin", "Dermatology", true],
  ["L40.0", "Psoriasis vulgaris", "Skin", "Dermatology", false],
  ["L70.0", "Acne vulgaris", "Skin", "Dermatology", true],
  ["B35.4", "Tinea corporis", "Skin", "Dermatology", true],
  ["L50.9", "Urticaria, unspecified", "Skin", "Dermatology", false],
  ["G43.909", "Migraine, unspecified, without status migrainosus", "Nervous system", "General Medicine", true],
  ["G44.209", "Tension-type headache, unspecified", "Nervous system", "General Medicine", true],
  ["G47.00", "Insomnia, unspecified", "Nervous system", "Psychiatry", true],
  ["F41.1", "Generalised anxiety disorder", "Mental and behavioural", "Psychiatry", true],
  ["F32.9", "Major depressive disorder, single episode, unspecified", "Mental and behavioural", "Psychiatry", true],
  ["F43.12", "Post-traumatic stress disorder, chronic", "Mental and behavioural", "Psychiatry", false],
  ["H10.9", "Unspecified conjunctivitis", "Eye", "General Medicine", true],
  ["H66.90", "Otitis media, unspecified", "Ear", "ENT", true],
  ["H61.20", "Impacted cerumen, unspecified ear", "Ear", "ENT", false],
  ["N94.6", "Dysmenorrhoea, unspecified", "Genitourinary system", "Gynaecology", true],
  ["N91.2", "Amenorrhoea, unspecified", "Genitourinary system", "Gynaecology", false],
  ["E28.2", "Polycystic ovarian syndrome", "Endocrine and metabolic", "Gynaecology", true],
  ["O26.90", "Pregnancy-related condition, unspecified", "Pregnancy", "Gynaecology", false],
  ["Z34.90", "Supervision of normal pregnancy, unspecified", "Pregnancy", "Gynaecology", true],
  ["P07.30", "Preterm newborn, unspecified weeks", "Perinatal", "Paediatrics", false],
  ["J21.9", "Acute bronchiolitis, unspecified", "Respiratory system", "Paediatrics", true],
  ["R50.9", "Fever, unspecified", "Symptoms and signs", "Paediatrics", true],
  ["R05.9", "Cough, unspecified", "Symptoms and signs", "General Medicine", true],
  ["R10.9", "Abdominal pain, unspecified", "Symptoms and signs", "General Medicine", true],
  ["R51.9", "Headache, unspecified", "Symptoms and signs", "General Medicine", true],
  ["R53.83", "Other fatigue", "Symptoms and signs", "General Medicine", true],
  ["R42", "Dizziness and giddiness", "Symptoms and signs", "General Medicine", true],
  ["Z00.00", "General adult medical examination without abnormal findings", "Health status", "General Medicine", true],
  ["Z23", "Encounter for immunisation", "Health status", "Paediatrics", true],
  ["Z71.3", "Dietary counselling and surveillance", "Health status", "General Medicine", false],
];

const lines = [
  "-- ====================================================================",
  "-- CareClinic ICD-10 catalogue (generated by scripts/generate-icd10.mjs)",
  "-- ====================================================================",
  "",
];

for (const [code, name, chapter, specialty, common] of CODES) {
  lines.push(
    `INSERT INTO icd10_catalog (code, condition_name, chapter, specialty, is_common) VALUES (${esc(code)}, ${esc(name)}, ${esc(chapter)}, ${esc(specialty)}, ${esc(common)}) ON CONFLICT (code) DO NOTHING;`
  );
}
lines.push("");
lines.push(`-- ${CODES.length} codes`);

console.log(lines.join("\n"));
