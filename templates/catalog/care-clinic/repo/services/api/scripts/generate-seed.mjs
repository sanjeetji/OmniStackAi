/** Deterministic seed data generator for CareClinic Healthcare & Telemedicine Platform. */

function esc(val) {
  if (val === null || val === undefined) return "NULL";
  if (typeof val === "boolean") return val ? "TRUE" : "FALSE";
  if (typeof val === "number") return String(val);
  return `'${String(val).replace(/'/g, "''")}'`;
}

function escArray(arr) {
  if (!arr || arr.length === 0) return "'{}'";
  return `ARRAY[${arr.map(esc).join(", ")}]::text[]`;
}

const HASH_PATIENT =
  "4580f7bd428f4850f60bec1504ab34de:20b0fa498343480052b457d34438d0a89fbac8dfaf77435f93fe5c6306a71b885bb6b0854a9965812ec9f5f43916013ed316bb04f2aaf10b61e323827045b7d7";
const HASH_DOCTOR =
  "7dc45678e08cb148099ac26b8fe7ef00:ef955f33dd77210561efa29c3456403d247561a7dfc2062938a033d7565fbc5e7a64d0a8e2a6dea3b621f1677748aad4038979fc092b78f7e8313b5f1b14ecc0";
const HASH_ADMIN =
  "e94cad3dbf2f554dc09cdd3b9c8608c0:37d49a6c1d9d1ffd34658c3686ba86517793a65c9d7ae617ae38e81e675474e154df4dca1d8b3cc002a629ef7056c510c826850de45df2069fa1585f6492b189";

const lines = [];
function out(str) {
  lines.push(str);
}

out(`-- ====================================================================`);
out(`-- CareClinic Healthcare & Telemedicine: Deterministic Demo Seed Data`);
out(`-- ====================================================================`);
out(``);

// 1. Clinic
const CLINIC_ID = "20000000-0000-0000-0000-000000000001";
out(`-- 1. Primary Clinic`);
out(`INSERT INTO clinics (id, name, slug, code, address, city, pincode, phone, email, lat, lng, opening_time, closing_time)`);
out(`VALUES (`);
out(`  ${esc(CLINIC_ID)},`);
out(`  'CareClinic Indiranagar',`);
out(`  'careclinic-indiranagar',`);
out(`  'CC-INDIRA-01',`);
out(`  '742, 100 Feet Road, HAL 2nd Stage, Indiranagar',`);
out(`  'Bengaluru',`);
out(`  '560038',`);
out(`  '+91 80 4912 3000',`);
out(`  'care.indiranagar@careclinic.test',`);
out(`  12.9784, 77.6408, '08:00:00', '21:00:00'`);
out(`) ON CONFLICT (id) DO NOTHING;`);
out(``);

// 2. Staff (Admin & Receptionist)
out(`-- 2. Clinic Staff & Operations`);
const STAFF = [
  {
    id: "30000000-0000-0000-0000-000000000001",
    email: "admin@careclinic.test",
    passwordHash: HASH_ADMIN,
    fullName: "Kavita Nair",
    phone: "+91 98450 11223",
    role: "admin",
  },
  {
    id: "30000000-0000-0000-0000-000000000002",
    email: "suresh.gowda@careclinic.test",
    passwordHash: HASH_ADMIN,
    fullName: "Suresh Gowda",
    phone: "+91 98450 22334",
    role: "receptionist",
  },
];

for (const s of STAFF) {
  out(
    `INSERT INTO users (id, email, password_hash, full_name, phone, role) VALUES (${esc(s.id)}, ${esc(s.email)}, ${esc(s.passwordHash)}, ${esc(s.fullName)}, ${esc(s.phone)}, ${esc(s.role)}) ON CONFLICT (id) DO NOTHING;`
  );
}
out(``);

// 3. 12 Doctors across 8 Specialties
out(`-- 3. Physicians & Doctor Profiles`);
const DOCTORS = [
  {
    id: "40000000-0000-0000-0000-000000000001",
    email: "dr.rajesh@careclinic.test",
    passwordHash: HASH_DOCTOR,
    fullName: "Dr. Rajesh Varma, MD, DM",
    phone: "+91 98860 10001",
    license: "KMC-42918",
    qualification: "MBBS, MD (Medicine), DM (Cardiology)",
    specialties: ["Cardiology", "Internal Medicine"],
    experience: 18,
    clinicFee: 900,
    videoFee: 800,
    bio: "Senior Consultant Cardiologist and Head of Clinical Care. Specializes in preventive cardiology, hypertension, and ischemic heart disease.",
    room: "OPD Room 101",
    rating: 4.94,
    ratingCount: 184,
  },
  {
    id: "40000000-0000-0000-0000-000000000002",
    email: "meera.nambiar@careclinic.test",
    passwordHash: HASH_DOCTOR,
    fullName: "Dr. Meera Nambiar, MD",
    phone: "+91 98860 10002",
    license: "KMC-51042",
    qualification: "MBBS, MD (Pediatrics), DNB",
    specialties: ["Pediatrics", "Neonatology"],
    experience: 14,
    clinicFee: 750,
    videoFee: 650,
    bio: "Chief Pediatrician dedicated to adolescent healthcare, pediatric vaccinations, and childhood developmental milestones.",
    room: "OPD Room 102",
    rating: 4.96,
    ratingCount: 220,
  },
  {
    id: "40000000-0000-0000-0000-000000000003",
    email: "vikramaditya.sen@careclinic.test",
    passwordHash: HASH_DOCTOR,
    fullName: "Dr. Vikramaditya Sen, MS",
    phone: "+91 98860 10003",
    license: "KMC-38914",
    qualification: "MBBS, MS (Orthopedics), MCh",
    specialties: ["Orthopedics", "Sports Medicine"],
    experience: 20,
    clinicFee: 850,
    videoFee: 750,
    bio: "Consultant Orthopedic Surgeon specializing in arthroscopic sports injury repair, degenerative joint arthritis, and spine posture correction.",
    room: "OPD Room 103",
    rating: 4.88,
    ratingCount: 142,
  },
  {
    id: "40000000-0000-0000-0000-000000000004",
    email: "priya.swaminathan@careclinic.test",
    passwordHash: HASH_DOCTOR,
    fullName: "Dr. Priya Swaminathan, MD",
    phone: "+91 98860 10004",
    license: "KMC-60219",
    qualification: "MBBS, MD (Dermatology, Venereology & Leprosy)",
    specialties: ["Dermatology", "Cosmetology"],
    experience: 11,
    clinicFee: 700,
    videoFee: 650,
    bio: "Dermatologist and aesthetic specialist focusing on chronic eczema, psoriasis, acne management, and pediatric skin conditions.",
    room: "OPD Room 104",
    rating: 4.92,
    ratingCount: 198,
  },
  {
    id: "40000000-0000-0000-0000-000000000005",
    email: "arjun.kapoor@careclinic.test",
    passwordHash: HASH_DOCTOR,
    fullName: "Dr. Arjun Kapoor, MBBS, DNB",
    phone: "+91 98860 10005",
    license: "KMC-71930",
    qualification: "MBBS, DNB (Family Medicine)",
    specialties: ["General Medicine", "Preventive Healthcare"],
    experience: 9,
    clinicFee: 600,
    videoFee: 500,
    bio: "Primary Care Physician committed to holistic family wellness, annual preventive health screenings, and seasonal infectious fever control.",
    room: "OPD Room 105",
    rating: 4.85,
    ratingCount: 110,
  },
  {
    id: "40000000-0000-0000-0000-000000000006",
    email: "sunita.kulkarni@careclinic.test",
    passwordHash: HASH_DOCTOR,
    fullName: "Dr. Sunita Kulkarni, MS, DGO",
    phone: "+91 98860 10006",
    license: "KMC-44812",
    qualification: "MBBS, MS (Obstetrics & Gynecology), FICOG",
    specialties: ["Obstetrics & Gynecology"],
    experience: 16,
    clinicFee: 800,
    videoFee: 700,
    bio: "Senior Obstetrician & Gynecologist specializing in high-risk antenatal care, PCOS hormonal balance, and menopausal wellness.",
    room: "OPD Room 106",
    rating: 4.95,
    ratingCount: 230,
  },
  {
    id: "40000000-0000-0000-0000-000000000007",
    email: "rohan.joshi@careclinic.test",
    passwordHash: HASH_DOCTOR,
    fullName: "Dr. Rohan Joshi, MS",
    phone: "+91 98860 10007",
    license: "KMC-53110",
    qualification: "MBBS, MS (ENT / Otorhinolaryngology)",
    specialties: ["ENT"],
    experience: 12,
    clinicFee: 700,
    videoFee: 600,
    bio: "Ear, Nose and Throat surgeon focusing on chronic allergic sinusitis, vertigo balance disorders, and pediatric tonsillitis.",
    room: "OPD Room 107",
    rating: 4.87,
    ratingCount: 94,
  },
  {
    id: "40000000-0000-0000-0000-000000000008",
    email: "alistair.fernandez@careclinic.test",
    passwordHash: HASH_DOCTOR,
    fullName: "Dr. Alistair Fernandez, MD",
    phone: "+91 98860 10008",
    license: "KMC-62341",
    qualification: "MBBS, MD (Psychiatry)",
    specialties: ["Psychiatry", "Behavioral Health"],
    experience: 10,
    clinicFee: 1000,
    videoFee: 900,
    bio: "Consultant Psychiatrist offering empathetic clinical therapy for adult anxiety, depression, corporate burnout, and sleep disorders.",
    room: "OPD Room 108",
    rating: 4.93,
    ratingCount: 165,
  },
  {
    id: "40000000-0000-0000-0000-000000000009",
    email: "ananya.sengupta@careclinic.test",
    passwordHash: HASH_DOCTOR,
    fullName: "Dr. Ananya Sengupta, MD, DM",
    phone: "+91 98860 10009",
    license: "KMC-48902",
    qualification: "MBBS, MD, DM (Endocrinology)",
    specialties: ["Endocrinology", "Diabetology"],
    experience: 15,
    clinicFee: 850,
    videoFee: 750,
    bio: "Endocrinologist specializing in comprehensive Type-2 Diabetes reversal programs, thyroid disorders, and metabolic health.",
    room: "OPD Room 109",
    rating: 4.91,
    ratingCount: 140,
  },
  {
    id: "40000000-0000-0000-0000-000000000010",
    email: "deepa.chawla@careclinic.test",
    passwordHash: HASH_DOCTOR,
    fullName: "Dr. Deepa Chawla, MD, DNB",
    phone: "+91 98860 10010",
    license: "KMC-56722",
    qualification: "MBBS, MD (Pulmonary Medicine)",
    specialties: ["Pulmonology"],
    experience: 13,
    clinicFee: 750,
    videoFee: 650,
    bio: "Pulmonologist specializing in bronchial asthma, allergic bronchitis, chronic obstructive pulmonary disease (COPD), and sleep apnea.",
    room: "OPD Room 110",
    rating: 4.89,
    ratingCount: 118,
  },
  {
    id: "40000000-0000-0000-0000-000000000011",
    email: "karthik.ramanathan@careclinic.test",
    passwordHash: HASH_DOCTOR,
    fullName: "Dr. Karthik Ramanathan, DM",
    phone: "+91 98860 10011",
    license: "KMC-39180",
    qualification: "MBBS, MD (Medicine), DM (Neurology)",
    specialties: ["Neurology"],
    experience: 17,
    clinicFee: 950,
    videoFee: 850,
    bio: "Neurologist specializing in headache and migraine therapy, peripheral neuropathy, epilepsy, and movement disorders.",
    room: "OPD Room 111",
    rating: 4.94,
    ratingCount: 156,
  },
  {
    id: "40000000-0000-0000-0000-000000000012",
    email: "shalini.verma@careclinic.test",
    passwordHash: HASH_DOCTOR,
    fullName: "Dr. Shalini Verma, MS",
    phone: "+91 98860 10012",
    license: "KMC-64819",
    qualification: "MBBS, MS (Ophthalmology)",
    specialties: ["Ophthalmology"],
    experience: 11,
    clinicFee: 700,
    videoFee: 600,
    bio: "Ophthalmic surgeon specializing in digital eye strain, glaucoma screening, dry eye syndrome, and refractive errors.",
    room: "OPD Room 112",
    rating: 4.90,
    ratingCount: 104,
  },
];

for (const d of DOCTORS) {
  out(
    `INSERT INTO users (id, email, password_hash, full_name, phone, role) VALUES (${esc(d.id)}, ${esc(d.email)}, ${esc(d.passwordHash)}, ${esc(d.fullName)}, ${esc(d.phone)}, 'doctor') ON CONFLICT (id) DO NOTHING;`
  );
  out(
    `INSERT INTO doctor_profiles (doctor_id, clinic_id, license_number, qualification, specialties, experience_years, consultation_fee_inr, video_fee_inr, bio, room_number, rating_avg, rating_count) VALUES (${esc(d.id)}, ${esc(CLINIC_ID)}, ${esc(d.license)}, ${esc(d.qualification)}, ${escArray(d.specialties)}, ${d.experience}, ${d.clinicFee}, ${d.videoFee}, ${esc(d.bio)}, ${esc(d.room)}, ${d.rating}, ${d.ratingCount}) ON CONFLICT (doctor_id) DO NOTHING;`
  );

  // Availability schedules (Monday through Saturday, 09:00 to 13:00 and 16:00 to 20:00)
  for (let dow = 1; dow <= 6; dow++) {
    out(
      `INSERT INTO doctor_availability (doctor_id, day_of_week, start_time, end_time, slot_duration_mins, is_available) VALUES (${esc(d.id)}, ${dow}, '09:00:00', '13:00:00', 20, TRUE);`
    );
    out(
      `INSERT INTO doctor_availability (doctor_id, day_of_week, start_time, end_time, slot_duration_mins, is_available) VALUES (${esc(d.id)}, ${dow}, '16:00:00', '20:00:00', 20, TRUE);`
    );
  }
}
out(``);

// 4. Diagnostic Lab Catalog
out(`-- 4. Diagnostic Lab Catalog`);
const LAB_TESTS = [
  {
    code: "CBC-01",
    name: "Complete Blood Count (CBC) with ESR",
    category: "hematology",
    fee: 350,
    hours: 12,
    sample: "Whole Blood EDTA",
  },
  {
    code: "LIPID-01",
    name: "Lipid Profile Comprehensive",
    category: "biochemistry",
    fee: 650,
    hours: 12,
    sample: "Fasting Blood Serum",
  },
  {
    code: "HBA1C-01",
    name: "HbA1c (Glycated Hemoglobin)",
    category: "biochemistry",
    fee: 450,
    hours: 8,
    sample: "Whole Blood EDTA",
  },
  {
    code: "THYROID-01",
    name: "Thyroid Profile Total (T3, T4, TSH)",
    category: "endocrinology",
    fee: 550,
    hours: 24,
    sample: "Blood Serum",
  },
  {
    code: "ECG-01",
    name: "12-Lead Electrocardiogram (ECG)",
    category: "cardiology",
    fee: 300,
    hours: 1,
    sample: "Electrode Tracing",
  },
  {
    code: "LFT-01",
    name: "Liver Function Test (LFT)",
    category: "biochemistry",
    fee: 700,
    hours: 12,
    sample: "Blood Serum",
  },
  {
    code: "KFT-01",
    name: "Kidney Function Test / Renal Profile",
    category: "biochemistry",
    fee: 650,
    hours: 12,
    sample: "Blood Serum",
  },
  {
    code: "VITD-01",
    name: "Vitamin D 25-Hydroxy Total",
    category: "biochemistry",
    fee: 1100,
    hours: 24,
    sample: "Blood Serum",
  },
  {
    code: "VITB12-01",
    name: "Vitamin B12 Cyanocobalamin",
    category: "biochemistry",
    fee: 900,
    hours: 24,
    sample: "Blood Serum",
  },
  {
    code: "URINE-01",
    name: "Urine Routine & Microscopy (R/M)",
    category: "microbiology",
    fee: 250,
    hours: 6,
    sample: "Midstream Urine",
  },
];

// Reference ranges the lab reports quote, and the result values the demo data draws from.
// Each entry is [value, flag]; the flags are what the patient and doctor apps colour.
const LAB_RESULTS = {
  "CBC-01": { unit: "g/dL", range: "12.0 - 15.5 (Hb)", values: [["13.4", "normal"], ["11.2", "low"], ["14.6", "normal"], ["10.1", "low"], ["13.9", "normal"]] },
  "LIPID-01": { unit: "mg/dL", range: "< 200 (Total cholesterol)", values: [["186", "normal"], ["241", "high"], ["198", "normal"], ["272", "high"], ["174", "normal"]] },
  "HBA1C-01": { unit: "%", range: "4.0 - 5.6", values: [["5.4", "normal"], ["6.8", "high"], ["5.1", "normal"], ["9.2", "critical"], ["6.1", "high"]] },
  "THYROID-01": { unit: "uIU/mL", range: "0.4 - 4.0 (TSH)", values: [["2.1", "normal"], ["7.6", "high"], ["1.8", "normal"], ["0.2", "low"], ["3.4", "normal"]] },
  "ECG-01": { unit: "bpm", range: "60 - 100 (Sinus rhythm)", values: [["74", "normal"], ["112", "high"], ["68", "normal"], ["54", "low"], ["81", "normal"]] },
  "LFT-01": { unit: "U/L", range: "7 - 56 (ALT)", values: [["28", "normal"], ["78", "high"], ["34", "normal"], ["41", "normal"], ["96", "high"]] },
  "KFT-01": { unit: "mg/dL", range: "0.6 - 1.2 (Creatinine)", values: [["0.9", "normal"], ["1.7", "high"], ["0.8", "normal"], ["1.1", "normal"], ["2.4", "critical"]] },
  "VITD-01": { unit: "ng/mL", range: "30 - 100", values: [["18", "low"], ["42", "normal"], ["12", "low"], ["36", "normal"], ["24", "low"]] },
  "VITB12-01": { unit: "pg/mL", range: "211 - 911", values: [["388", "normal"], ["162", "low"], ["512", "normal"], ["143", "low"], ["604", "normal"]] },
  "URINE-01": { unit: "—", range: "No growth / nil albumin", values: [["Nil albumin, 2-3 pus cells", "normal"], ["Albumin 1+, 12-15 pus cells", "high"], ["Nil albumin, clear", "normal"], ["Trace albumin", "normal"], ["Albumin 2+, RBC present", "critical"]] },
};

const LAB_TEST_IDS = LAB_TESTS.map(
  (_, i) => `a0000000-0000-0000-0000-${(i + 1).toString().padStart(12, "0")}`
);

LAB_TESTS.forEach((t, i) => {
  out(
    `INSERT INTO lab_test_catalog (id, code, name, category, standard_fee_inr, turnaround_hours, sample_type) VALUES (${esc(LAB_TEST_IDS[i])}, ${esc(t.code)}, ${esc(t.name)}, ${esc(t.category)}, ${t.fee}, ${t.hours}, ${esc(t.sample)}) ON CONFLICT (code) DO NOTHING;`
  );
});
out(``);

// 5. Patients (150 patients including demo Ananya Deshmukh)
out(`-- 5. Patients & Medical Histories`);
const FIRST_NAMES = [
  "Ananya", "Rohan", "Sneha", "Aditya", "Pooja", "Vikram", "Deepika", "Karthik", "Divya", "Rahul",
  "Swati", "Naveen", "Meenakshi", "Gaurav", "Shreya", "Abhishek", "Kavya", "Varun", "Neha", "Arun",
  "Rashmi", "Manoj", "Pallavi", "Siddharth", "Aishwarya", "Rajesh", "Tanvi", "Sunil", "Preeti", "Sanjay",
  "Priyanka", "Harish", "Vidya", "Pradeep", "Gayatri", "Vinay", "Bhavana", "Ajay", "Radha", "Sachin",
  "Archana", "Vijay", "Aparna", "Santosh", "Monika", "Dinesh", "Suma", "Chetan", "Lakshmi", "Mahesh"
];

const LAST_NAMES = [
  "Deshmukh", "Sharma", "Varma", "Patil", "Iyer", "Rao", "Nair", "Reddy", "Kulkarni", "Hegde",
  "Menon", "Bhat", "Shenoy", "Kamath", "Murthy", "Shetty", "Pai", "Gowda", "Joshi", "Bhattacharya",
  "Mukherjee", "Chatterjee", "Gupta", "Aggarwal", "Chopra", "Malhotra", "Mehta", "Shah", "Parekh", "Trivedi"
];

const BLOOD_GROUPS = ["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"];

// Demo Patient: Ananya Deshmukh
const DEMO_PATIENT_ID = "50000000-0000-0000-0000-000000000001";
out(
  `INSERT INTO users (id, email, password_hash, full_name, phone, role) VALUES (${esc(DEMO_PATIENT_ID)}, 'ananya@careclinic.test', ${esc(HASH_PATIENT)}, 'Ananya Deshmukh', '+91 99000 88123', 'patient') ON CONFLICT (id) DO NOTHING;`
);
out(
  `INSERT INTO patient_profiles (patient_id, dob, gender, blood_group, height_cm, weight_kg, emergency_contact, emergency_phone, address) VALUES (${esc(DEMO_PATIENT_ID)}, '1992-06-14', 'female', 'B+', 164, 58.5, 'Siddharth Deshmukh (Spouse)', '+91 99000 88124', 'Flat 402, Palm Meadows, Indiranagar, Bengaluru') ON CONFLICT (patient_id) DO NOTHING;`
);
out(
  `INSERT INTO medical_histories (patient_id, allergies, chronic_conditions, current_medications, past_surgeries, family_history, lifestyle_notes) VALUES (${esc(DEMO_PATIENT_ID)}, ARRAY['Penicillin', 'Dust Mites']::text[], ARRAY['Mild Seasonal Asthma']::text[], ARRAY['Levocetirizine 5mg (PRN)']::text[], ARRAY['Appendectomy (2018)']::text[], 'Maternal history of Type-2 Diabetes and Hypertension.', 'Sedentary desk job in IT; walks 30 mins 4 days/week.') ON CONFLICT (patient_id) DO NOTHING;`
);

// Family Members for Ananya
const AARAV_ID = "50000000-0000-0000-0000-000000000002";
out(
  `INSERT INTO family_members (id, primary_patient_id, full_name, relationship, dob, gender, blood_group) VALUES (${esc(AARAV_ID)}, ${esc(DEMO_PATIENT_ID)}, 'Aarav Deshmukh', 'child', '2020-04-12', 'male', 'B+') ON CONFLICT (id) DO NOTHING;`
);
out(
  `INSERT INTO family_members (primary_patient_id, full_name, relationship, dob, gender, blood_group) VALUES (${esc(DEMO_PATIENT_ID)}, 'Siddharth Deshmukh', 'spouse', '1989-11-28', 'male', 'O+') ON CONFLICT DO NOTHING;`
);

// Remaining 149 patients
const PATIENT_IDS = [DEMO_PATIENT_ID];
for (let i = 2; i <= 150; i++) {
  const patId = `50000000-0000-0000-0000-${i.toString().padStart(12, "0")}`;
  PATIENT_IDS.push(patId);

  // 50 first names and 30 surnames. Stepping the surname by a co-prime of its length spreads them
  // across the roll instead of giving 50 consecutive patients the same family name.
  const fn = FIRST_NAMES[(i - 1) % FIRST_NAMES.length];
  const ln = LAST_NAMES[((i - 1) * 7) % LAST_NAMES.length];
  const name = `${fn} ${ln}`;
  const email = `${fn.toLowerCase()}.${ln.toLowerCase()}${i}@careclinic.test`;
  const phone = `+91 99000 ${i.toString().padStart(5, "0")}`;
  const gender = i % 2 === 0 ? "female" : "male";
  const bg = BLOOD_GROUPS[i % BLOOD_GROUPS.length];
  const birthYear = 1960 + (i % 42); // ages 24 to 66
  const dob = `${birthYear}-0${(i % 9) + 1}-15`;
  const ht = 150 + (i % 35);
  const wt = 50 + (i % 45);

  out(
    `INSERT INTO users (id, email, password_hash, full_name, phone, role) VALUES (${esc(patId)}, ${esc(email)}, ${esc(HASH_PATIENT)}, ${esc(name)}, ${esc(phone)}, 'patient') ON CONFLICT (id) DO NOTHING;`
  );
  out(
    `INSERT INTO patient_profiles (patient_id, dob, gender, blood_group, height_cm, weight_kg) VALUES (${esc(patId)}, ${esc(dob)}, ${esc(gender)}, ${esc(bg)}, ${ht}, ${wt}) ON CONFLICT (patient_id) DO NOTHING;`
  );

  const allergies = i % 5 === 0 ? ["Sulfa Drugs"] : i % 7 === 0 ? ["Peanuts"] : [];
  const chronic = i % 4 === 0 ? ["Type 2 Diabetes"] : i % 3 === 0 ? ["Essential Hypertension"] : [];
  out(
    `INSERT INTO medical_histories (patient_id, allergies, chronic_conditions) VALUES (${esc(patId)}, ${escArray(allergies)}, ${escArray(chronic)}) ON CONFLICT (patient_id) DO NOTHING;`
  );
}
out(``);

// 6. Appointments over the last 90 days and the next 14, with their clinical and billing trail
out(`-- 6. Appointments, Consultations, SOAP Notes, Prescriptions, Labs & Invoices`);

const SLOTS = [
  "09:00:00", "09:20:00", "09:40:00", "10:00:00", "10:20:00", "10:40:00",
  "11:00:00", "11:20:00", "11:40:00", "12:00:00", "12:20:00", "12:40:00",
  "16:00:00", "16:20:00", "16:40:00", "17:00:00", "17:20:00", "17:40:00",
  "18:00:00", "18:20:00", "18:40:00", "19:00:00", "19:20:00", "19:40:00"
];

const ICD_DIAGNOSES = [
  { code: "I10", name: "Essential (primary) hypertension", meds: [{ name: "Telmisartan", dose: "40mg", form: "tablet", freq: "1-0-0", timing: "before_food" }, { name: "Amlodipine", dose: "5mg", form: "tablet", freq: "0-0-1", timing: "after_food" }] },
  { code: "E11.9", name: "Type 2 diabetes mellitus without complications", meds: [{ name: "Metformin HCl", dose: "500mg", form: "tablet", freq: "1-0-1", timing: "after_food" }, { name: "Glimepiride", dose: "1mg", form: "tablet", freq: "1-0-0", timing: "before_food" }] },
  { code: "J06.9", name: "Acute upper respiratory infection", meds: [{ name: "Paracetamol", dose: "650mg", form: "tablet", freq: "1-1-1", timing: "after_food" }, { name: "Cetirizine", dose: "10mg", form: "tablet", freq: "0-0-1", timing: "after_food" }] },
  { code: "M54.5", name: "Low back pain / lumbar strain", meds: [{ name: "Aceclofenac + Paracetamol", dose: "100/325mg", form: "tablet", freq: "1-0-1", timing: "after_food" }, { name: "Thiocolchicoside", dose: "4mg", form: "capsule", freq: "1-0-1", timing: "after_food" }] },
  { code: "L20.9", name: "Atopic dermatitis, unspecified", meds: [{ name: "Hydrocortisone 1% Cream", dose: "15g", form: "ointment", freq: "1-0-1", timing: "after_food" }, { name: "Levocetirizine", dose: "5mg", form: "tablet", freq: "0-0-1", timing: "after_food" }] },
  { code: "J45.909", name: "Unspecified asthma, uncomplicated", meds: [{ name: "Budesonide + Formoterol Inhaler", dose: "200/6mcg", form: "inhaler", freq: "1-0-1", timing: "before_food" }, { name: "Montelukast", dose: "10mg", form: "tablet", freq: "0-0-1", timing: "after_food" }] },
  { code: "K21.9", name: "Gastro-esophageal reflux disease without esophagitis", meds: [{ name: "Pantoprazole", dose: "40mg", form: "tablet", freq: "1-0-0", timing: "empty_stomach" }, { name: "Domperidone", dose: "10mg", form: "tablet", freq: "1-0-0", timing: "empty_stomach" }] },
  { code: "F41.1", name: "Generalized anxiety disorder", meds: [{ name: "Escitalopram", dose: "10mg", form: "tablet", freq: "0-0-1", timing: "after_food" }, { name: "Clonazepam", dose: "0.25mg", form: "tablet", freq: "0-0-1", timing: "after_food" }] },
];

let aptCounter = 0;

// Everything the closing section needs to write vitals, labs, refunds, reviews, video sessions
// and notifications without walking the SQL again.
const COMPLETED_VISITS = [];
const CANCELLED_VISITS = [];
const VIDEO_VISITS = [];
const TODAY_VISITS = [];
const RECEPTION_ID = STAFF[1].id; // Suresh Gowda, front desk

// Invoices are read newest-first by the cashier screen, so every row carries its own created_at.
function emitInvoice({ invId, invNum, patientId, aptId, amount, status, method, paidAt, createdAt, label, itemType }) {
  out(
    `INSERT INTO invoices (id, invoice_number, patient_id, appointment_id, total_amount, net_payable, payment_status, payment_method, transaction_ref, paid_at, created_at) VALUES (${esc(invId)}, ${esc(invNum)}, ${esc(patientId)}, ${esc(aptId)}, ${amount}, ${amount}, ${esc(status)}, ${esc(method)}, ${esc(method ? "TXN-" + invNum.replace("INV-", "") : null)}, ${paidAt}, ${createdAt});`
  );
  out(
    `INSERT INTO invoice_items (invoice_id, description, item_type, quantity, unit_price, amount) VALUES (${esc(invId)}, ${esc(label)}, ${esc(itemType)}, 1, ${amount}, ${amount});`
  );
}

function pad12(n) {
  return n.toString().padStart(12, "0");
}


// appointments.queue_status has its own vocabulary (see migrations/002_scheduling.sql); a
// no-show voids the token, so it maps to "cancelled", not to the appointment status itself.
const QUEUE_STATUS_FOR = {
  completed: "done",
  cancelled: "cancelled",
  no_show: "cancelled",
  booked: "waiting",
  checked_in: "called",
  in_consult: "with_doctor",
};

function queueStatusFor(status) {
  return QUEUE_STATUS_FOR[status] || "waiting";
}

function getEndSlot(slotStr) {
  const [h, m] = slotStr.split(":").map(Number);
  const totalM = h * 60 + m + 20;
  const endH = Math.floor(totalM / 60);
  const endM = totalM % 60;
  return `${endH.toString().padStart(2, "0")}:${endM.toString().padStart(2, "0")}:00`;
}

// Past appointments: 8 per weekday over the last 90 days (the clinic is closed on Sundays)
for (let dayOffset = 90; dayOffset >= 1; dayOffset--) {
  const d = new Date();
  d.setDate(d.getDate() - dayOffset);
  const dateStr = d.toISOString().slice(0, 10);
  const isWeekend = d.getDay() === 0;
  if (isWeekend) continue; // Clinic OPD closed on Sundays

  // 8 appointments per weekday across doctors
  for (let sIdx = 0; sIdx < 8; sIdx++) {
    aptCounter++;

    const aptId = `60000000-0000-0000-0000-${aptCounter.toString().padStart(12, "0")}`;
    const aptNumber = `APT-2026-${aptCounter.toString().padStart(5, "0")}`;
    const doctor = DOCTORS[aptCounter % DOCTORS.length];
    const patientId = PATIENT_IDS[aptCounter % PATIENT_IDS.length];
    const slot = SLOTS[sIdx * 3]; // 09:00, 10:00, 11:00, 12:00, 16:00, 17:00, 18:00, 19:00
    const endSlot = getEndSlot(slot);
    const isVideo = aptCounter % 4 === 0;
    const fee = isVideo ? doctor.videoFee : doctor.clinicFee;

    // Mostly completed, 5% cancelled, 5% no_show
    let status = "completed";
    if (aptCounter % 20 === 0) status = "cancelled";
    else if (aptCounter % 25 === 0) status = "no_show";

    out(
      `INSERT INTO appointments (id, appointment_number, patient_id, doctor_id, clinic_id, appointment_type, scheduled_date, start_time, end_time, status, token_number, queue_status, fee_amount, is_paid, payment_method) VALUES (${esc(aptId)}, ${esc(aptNumber)}, ${esc(patientId)}, ${esc(doctor.id)}, ${esc(CLINIC_ID)}, ${esc(isVideo ? "video" : "in_clinic")}, ${esc(dateStr)}, ${esc(slot)}, ${esc(endSlot)}, ${esc(status)}, ${sIdx + 1}, ${esc(queueStatusFor(status))}, ${fee}, TRUE, 'upi');`
    );

    // Invoice: a cancelled visit was refunded (the refund rows follow in section 7), a no-show
    // keeps the fee, and everything else was collected on the day.
    const invId = `70000000-0000-0000-0000-${pad12(aptCounter)}`;
    const invNum = `INV-2026-${aptCounter.toString().padStart(5, "0")}`;
    emitInvoice({
      invId,
      invNum,
      patientId,
      aptId,
      amount: fee,
      status: status === "cancelled" ? "refunded" : "paid",
      method: "upi",
      paidAt: esc(dateStr + " 09:05:00"),
      createdAt: esc(dateStr + " 08:55:00"),
      label: `${isVideo ? "Video consultation" : "OPD consultation"} — ${doctor.fullName}`,
      itemType: isVideo ? "video_fee" : "consultation_fee",
    });

    if (isVideo && status === "completed") {
      VIDEO_VISITS.push({ aptId, dateStr, slot, endSlot, ended: true });
    }
    if (status === "cancelled") {
      CANCELLED_VISITS.push({ aptId, invId, invNum, patientId, doctorId: doctor.id, dateStr, fee });
    }

    // If completed: consultation + diagnosis + prescription
    if (status === "completed") {
      const diag = ICD_DIAGNOSES[aptCounter % ICD_DIAGNOSES.length];
      const consultId = `80000000-0000-0000-0000-${aptCounter.toString().padStart(12, "0")}`;

      out(
        `INSERT INTO consultations (id, appointment_id, doctor_id, patient_id, started_at, completed_at, subjective, objective, assessment, plan, follow_up_date) VALUES (${esc(consultId)}, ${esc(aptId)}, ${esc(doctor.id)}, ${esc(patientId)}, ${esc(dateStr + " " + slot)}, ${esc(dateStr + " " + endSlot)}, 'Patient presents with persistent symptoms and fatigue. Vitals evaluated.', 'Physical examination unremarkable. Blood pressure and SpO2 within normal limits.', ${esc(diag.name)}, 'Prescribed medication course. Advised lifestyle modifications and follow-up in 14 days.', ${esc(dateStr)});`
      );

      out(
        `INSERT INTO diagnoses (consultation_id, icd10_code, condition_name, is_primary) VALUES (${esc(consultId)}, ${esc(diag.code)}, ${esc(diag.name)}, TRUE);`
      );

      // Prescription
      const rxId = `90000000-0000-0000-0000-${aptCounter.toString().padStart(12, "0")}`;
      const rxNum = `RX-2026-${aptCounter.toString().padStart(5, "0")}`;
      out(
        `INSERT INTO prescriptions (id, prescription_number, consultation_id, patient_id, doctor_id, diagnosis_summary, signed_at, is_immutable, digital_signature) VALUES (${esc(rxId)}, ${esc(rxNum)}, ${esc(consultId)}, ${esc(patientId)}, ${esc(doctor.id)}, ${esc(diag.name)}, ${esc(dateStr + " " + endSlot)}, TRUE, ${esc("SIG-CC-" + doctor.id.slice(0, 8))});`
      );

      for (const m of diag.meds) {
        out(
          `INSERT INTO prescription_items (prescription_id, medicine_name, generic_name, dosage_form, strength, frequency, timing, duration_days, instructions) VALUES (${esc(rxId)}, ${esc(m.name)}, ${esc(m.name)}, ${esc(m.form)}, ${esc(m.dose)}, ${esc(m.freq)}, ${esc(m.timing)}, 7, 'Take as prescribed with warm water.');`
        );
      }

      // Chart access log
      out(
        `INSERT INTO chart_access_logs (patient_id, accessed_by_user_id, access_type, resource_id, accessed_at) VALUES (${esc(patientId)}, ${esc(doctor.id)}, 'issue_prescription', ${esc(rxId)}, ${esc(dateStr + " " + endSlot)});`
      );

      COMPLETED_VISITS.push({
        n: aptCounter,
        aptId,
        consultId,
        patientId,
        doctorId: doctor.id,
        doctorName: doctor.fullName,
        dateStr,
        slot,
        endSlot,
        isVideo,
        diag,
      });
    }
  }
}

out(``);
out(`-- 6b. Ananya Deshmukh's own clinical history (the account the demo signs in with)`);

// The demo patient needs a chart worth opening: visits across several specialties, each with a
// signed prescription, and two paediatric visits booked for her son Aarav. These use the :20 slots
// the bulk loop never touches, so the doctor/date/time uniqueness rule still holds.
function weekdayBefore(days) {
  const d = new Date();
  d.setDate(d.getDate() - days);
  while (d.getDay() === 0) d.setDate(d.getDate() - 1);
  return d.toISOString().slice(0, 10);
}

const DEMO_HISTORY = [
  {
    daysAgo: 82, doctor: 0, slot: "09:20:00", video: false, icd: 0,
    subjective: "Reports early-morning headaches and occasional palpitations over the last three weeks. Family history of hypertension on the maternal side.",
    objective: "BP 148/94 mmHg (repeat 146/92). Pulse 84/min regular. S1 S2 normal, no murmurs. No pedal oedema. BMI 21.7.",
    assessment: "Newly detected stage 1 hypertension. No end-organ damage on initial screen.",
    plan: "Start Telmisartan 40mg once daily. Salt restriction under 5g/day, brisk walk 30 minutes five days a week. Home BP diary. Baseline lipid profile and renal function. Review in four weeks.",
    forChild: false, labs: true, review: true,
  },
  {
    daysAgo: 61, doctor: 0, slot: "10:20:00", video: true, icd: 0,
    subjective: "Follow-up on antihypertensive therapy. Home readings averaging 128/82. No dizziness or dry cough.",
    objective: "Teleconsultation. Home BP log reviewed: 14-day average 128/82 mmHg. Weight stable at 58.5 kg.",
    assessment: "Hypertension responding well to monotherapy. Lipids borderline on the last panel.",
    plan: "Continue Telmisartan 40mg. Add evening walk. Repeat lipid profile at three months. No change to dose.",
    forChild: false, labs: false, review: true,
  },
  {
    daysAgo: 40, doctor: 5, slot: "11:20:00", video: false, icd: 5,
    subjective: "Night-time cough and chest tightness for ten days, worse after dust exposure at home. Known mild seasonal asthma.",
    objective: "RR 18/min. SpO2 97% on room air. Scattered expiratory wheeze bilaterally. Peak flow 82% of predicted.",
    assessment: "Mild persistent asthma with a dust-mite trigger; currently in exacerbation.",
    plan: "Budesonide + Formoterol inhaler twice daily for six weeks with spacer technique demonstrated. Montelukast at night. Mattress covers and weekly hot-wash of bedding. Return if peak flow drops below 70%.",
    forChild: false, labs: false, review: false,
  },
  {
    daysAgo: 19, doctor: 1, slot: "09:20:00", video: false, icd: 2,
    subjective: "Aarav (6) has had fever up to 101F for two days with a runny nose and sore throat. Eating less, playful between fevers.",
    objective: "Temp 100.8F. Throat congested, no exudate. Chest clear. Tympanic membranes normal. No rash. Hydration adequate.",
    assessment: "Acute viral upper respiratory infection. No features of bacterial infection.",
    plan: "Paracetamol syrup 250mg/5ml as needed for fever. Steam inhalation, extra fluids. Return in 48 hours if fever persists or feeding drops.",
    forChild: true, labs: false, review: true,
  },
  {
    daysAgo: 6, doctor: 0, slot: "12:20:00", video: false, icd: 0,
    subjective: "Quarterly cardiac review. Adherent to medication, walking most days. No chest pain or breathlessness.",
    objective: "BP 126/80 mmHg. Pulse 72/min. ECG: normal sinus rhythm, no ST-T changes. Weight 58.0 kg.",
    assessment: "Hypertension well controlled on current therapy. Vitamin D low on the last panel.",
    plan: "Continue Telmisartan 40mg. Vitamin D supplementation started. Repeat HbA1c and lipid profile today. Review in three months.",
    forChild: false, labs: true, review: true,
  },
];

for (const h of DEMO_HISTORY) {
  aptCounter++;
  const doctor = DOCTORS[h.doctor];
  const diag = ICD_DIAGNOSES[h.icd];
  const dateStr = weekdayBefore(h.daysAgo);
  const endSlot = getEndSlot(h.slot);
  const fee = h.video ? doctor.videoFee : doctor.clinicFee;
  const aptId = `60000000-0000-0000-0000-${pad12(aptCounter)}`;
  const aptNumber = `APT-2026-${aptCounter.toString().padStart(5, "0")}`;
  const consultId = `80000000-0000-0000-0000-${pad12(aptCounter)}`;
  const rxId = `90000000-0000-0000-0000-${pad12(aptCounter)}`;
  const rxNum = `RX-2026-${aptCounter.toString().padStart(5, "0")}`;
  const invId = `70000000-0000-0000-0000-${pad12(aptCounter)}`;
  const invNum = `INV-2026-${aptCounter.toString().padStart(5, "0")}`;

  out(
    `INSERT INTO appointments (id, appointment_number, patient_id, for_family_member_id, doctor_id, clinic_id, appointment_type, scheduled_date, start_time, end_time, status, token_number, queue_status, fee_amount, is_paid, payment_method) VALUES (${esc(aptId)}, ${esc(aptNumber)}, ${esc(DEMO_PATIENT_ID)}, ${esc(h.forChild ? AARAV_ID : null)}, ${esc(doctor.id)}, ${esc(CLINIC_ID)}, ${esc(h.video ? "video" : "in_clinic")}, ${esc(dateStr)}, ${esc(h.slot)}, ${esc(endSlot)}, 'completed', 9, 'done', ${fee}, TRUE, 'card');`
  );
  emitInvoice({
    invId, invNum, patientId: DEMO_PATIENT_ID, aptId, amount: fee,
    status: "paid", method: "card",
    paidAt: esc(dateStr + " " + h.slot), createdAt: esc(dateStr + " " + h.slot),
    label: `${h.video ? "Video consultation" : "OPD consultation"} — ${doctor.fullName}`,
    itemType: h.video ? "video_fee" : "consultation_fee",
  });
  out(
    `INSERT INTO consultations (id, appointment_id, doctor_id, patient_id, started_at, completed_at, subjective, objective, assessment, plan, follow_up_date) VALUES (${esc(consultId)}, ${esc(aptId)}, ${esc(doctor.id)}, ${esc(DEMO_PATIENT_ID)}, ${esc(dateStr + " " + h.slot)}, ${esc(dateStr + " " + endSlot)}, ${esc(h.subjective)}, ${esc(h.objective)}, ${esc(h.assessment)}, ${esc(h.plan)}, ${esc(weekdayBefore(h.daysAgo - 28))});`
  );
  out(
    `INSERT INTO diagnoses (consultation_id, icd10_code, condition_name, is_primary) VALUES (${esc(consultId)}, ${esc(diag.code)}, ${esc(diag.name)}, TRUE);`
  );
  out(
    `INSERT INTO prescriptions (id, prescription_number, consultation_id, patient_id, doctor_id, diagnosis_summary, signed_at, is_immutable, digital_signature) VALUES (${esc(rxId)}, ${esc(rxNum)}, ${esc(consultId)}, ${esc(DEMO_PATIENT_ID)}, ${esc(doctor.id)}, ${esc(diag.name)}, ${esc(dateStr + " " + endSlot)}, TRUE, ${esc("SIG-CC-" + doctor.id.slice(0, 8))});`
  );
  for (const m of diag.meds) {
    out(
      `INSERT INTO prescription_items (prescription_id, medicine_name, generic_name, dosage_form, strength, frequency, timing, duration_days, instructions) VALUES (${esc(rxId)}, ${esc(m.name)}, ${esc(m.name)}, ${esc(m.form)}, ${esc(m.dose)}, ${esc(m.freq)}, ${esc(m.timing)}, ${h.forChild ? 5 : 30}, 'Take as prescribed with warm water.');`
    );
  }
  out(
    `INSERT INTO chart_access_logs (patient_id, accessed_by_user_id, access_type, resource_id, accessed_at) VALUES (${esc(DEMO_PATIENT_ID)}, ${esc(doctor.id)}, 'issue_prescription', ${esc(rxId)}, ${esc(dateStr + " " + endSlot)});`
  );

  COMPLETED_VISITS.push({
    n: aptCounter, aptId, consultId, patientId: DEMO_PATIENT_ID, doctorId: doctor.id,
    doctorName: doctor.fullName, dateStr, slot: h.slot, endSlot, isVideo: h.video, diag,
    demoLabs: h.labs, demoReview: h.review,
  });
  if (h.video) {
    VIDEO_VISITS.push({ aptId, dateStr, slot: h.slot, endSlot, ended: true });
  }
}
out(``);

// Today's live OPD queue, then the next 14 days of bookings
const todayStr = new Date().toISOString().slice(0, 10);
out(`-- Today's Active Clinic Queue & Upcoming Appointments`);

// Today's appointments for Dr. Rajesh Varma (including demo patient Ananya)
const TODAY_APPOINTMENTS = [
  { slot: "09:00:00", end: "09:20:00", patient: DEMO_PATIENT_ID, status: "completed", token: 1, qStatus: "done" },
  { slot: "09:20:00", end: "09:40:00", patient: PATIENT_IDS[2], status: "completed", token: 2, qStatus: "done" },
  { slot: "09:40:00", end: "10:00:00", patient: PATIENT_IDS[3], status: "in_consult", token: 3, qStatus: "with_doctor" },
  { slot: "10:00:00", end: "10:20:00", patient: PATIENT_IDS[4], status: "checked_in", token: 4, qStatus: "waiting" },
  { slot: "10:20:00", end: "10:40:00", patient: PATIENT_IDS[5], status: "checked_in", token: 5, qStatus: "waiting" },
  { slot: "10:40:00", end: "11:00:00", patient: PATIENT_IDS[6], status: "booked", token: null, qStatus: "waiting" },
  { slot: "11:00:00", end: "11:20:00", patient: PATIENT_IDS[7], status: "booked", token: null, qStatus: "waiting" },
  { slot: "11:20:00", end: "11:40:00", patient: PATIENT_IDS[8], status: "booked", token: null, qStatus: "waiting" },
  { slot: "16:00:00", end: "16:20:00", patient: PATIENT_IDS[9], status: "booked", token: null, qStatus: "waiting" },
  { slot: "16:20:00", end: "16:40:00", patient: PATIENT_IDS[10], status: "booked", token: null, qStatus: "waiting" },
];

for (const ta of TODAY_APPOINTMENTS) {
  aptCounter++;
  const aptId = `60000000-0000-0000-0000-${aptCounter.toString().padStart(12, "0")}`;
  const aptNumber = `APT-2026-${aptCounter.toString().padStart(5, "0")}`;
  const doctor = DOCTORS[0]; // Dr. Rajesh Varma
  // Today's desk: the patients already seen have paid, the ones still waiting settle on the way out.
  const collected = ta.status === "completed" || ta.status === "in_consult";

  out(
    `INSERT INTO appointments (id, appointment_number, patient_id, doctor_id, clinic_id, appointment_type, scheduled_date, start_time, end_time, status, token_number, queue_status, fee_amount, is_paid) VALUES (${esc(aptId)}, ${esc(aptNumber)}, ${esc(ta.patient)}, ${esc(doctor.id)}, ${esc(CLINIC_ID)}, 'in_clinic', ${esc(todayStr)}, ${esc(ta.slot)}, ${esc(ta.end)}, ${esc(ta.status)}, ${ta.token || "NULL"}, ${esc(ta.qStatus)}, ${doctor.clinicFee}, ${esc(collected)});`
  );

  const invId = `70000000-0000-0000-0000-${pad12(aptCounter)}`;
  const invNum = `INV-2026-${aptCounter.toString().padStart(5, "0")}`;
  emitInvoice({
    invId,
    invNum,
    patientId: ta.patient,
    aptId,
    amount: doctor.clinicFee,
    status: collected ? "paid" : "pending",
    method: collected ? "upi" : null,
    paidAt: collected ? "NOW()" : "NULL",
    createdAt: "NOW()",
    label: `OPD consultation — ${doctor.fullName}`,
    itemType: "consultation_fee",
  });

  if (ta.status === "in_consult" || ta.status === "completed") {
    const consultId = `80000000-0000-0000-0000-${aptCounter.toString().padStart(12, "0")}`;
    out(
      `INSERT INTO consultations (id, appointment_id, doctor_id, patient_id, started_at, subjective, objective, assessment, plan) VALUES (${esc(consultId)}, ${esc(aptId)}, ${esc(doctor.id)}, ${esc(ta.patient)}, NOW(), 'Routine quarterly blood pressure and cardiac review.', 'BP 128/82 mmHg, HR 74 bpm. Heart sounds S1 S2 normal.', 'Hypertension stage 1 - well controlled.', 'Continue low sodium diet and regular morning walk.');`
    );
    out(
      `INSERT INTO diagnoses (consultation_id, icd10_code, condition_name, is_primary) VALUES (${esc(consultId)}, 'I10', 'Essential (primary) hypertension', TRUE);`
    );
    TODAY_VISITS.push({ n: aptCounter, aptId, consultId, patientId: ta.patient, doctorId: doctor.id });
  }
}

// Planned physician absences the rostering screen shows. No appointment is written against a
// doctor on a day they are away, so the calendar and the bookings agree.
function dateInDays(days) {
  const d = new Date();
  d.setDate(d.getDate() + days);
  return d.toISOString().slice(0, 10);
}

const SCHEDULE_OVERRIDES = [
  { doctor: DOCTORS[1], day: 2, isLeave: true, reason: "Paediatric immunisation camp — Whitefield outreach" },
  { doctor: DOCTORS[4], day: 5, isLeave: true, reason: "Annual leave" },
  { doctor: DOCTORS[7], day: 6, isLeave: true, reason: "IAP conference, Hyderabad (speaker)" },
  { doctor: DOCTORS[2], day: 9, isLeave: false, start: "11:00:00", end: "15:00:00", reason: "Theatre list in the morning; OPD shifted to the afternoon" },
  { doctor: DOCTORS[10], day: 12, isLeave: true, reason: "Medical council licence renewal" },
];

const LEAVE_DAYS = new Set(
  SCHEDULE_OVERRIDES.filter((o) => o.isLeave).map((o) => `${o.doctor.id}|${dateInDays(o.day)}`)
);

// Generate remaining upcoming appointments up to +14 days
for (let day = 1; day <= 14; day++) {
  const d = new Date();
  d.setDate(d.getDate() + day);
  const dateStr = d.toISOString().slice(0, 10);
  if (d.getDay() === 0) continue;

  for (let s = 0; s < 12; s++) {
    if (aptCounter >= 900) break;

    const doctor = DOCTORS[s % DOCTORS.length];
    if (LEAVE_DAYS.has(`${doctor.id}|${dateStr}`)) continue;

    aptCounter++;

    const aptId = `60000000-0000-0000-0000-${pad12(aptCounter)}`;
    const aptNumber = `APT-2026-${aptCounter.toString().padStart(5, "0")}`;
    const patientId = PATIENT_IDS[(s * 7 + day) % PATIENT_IDS.length];
    const slot = SLOTS[s];
    const endSlot = getEndSlot(slot);
    const isVideo = s % 3 === 0;
    const fee = isVideo ? doctor.videoFee : doctor.clinicFee;

    // A video visit is paid online when it is booked; an OPD visit is collected at the desk, so
    // it stays on the cashier's pending list until the patient arrives.
    out(
      `INSERT INTO appointments (id, appointment_number, patient_id, doctor_id, clinic_id, appointment_type, scheduled_date, start_time, end_time, status, queue_status, fee_amount, is_paid) VALUES (${esc(aptId)}, ${esc(aptNumber)}, ${esc(patientId)}, ${esc(doctor.id)}, ${esc(CLINIC_ID)}, ${esc(isVideo ? "video" : "in_clinic")}, ${esc(dateStr)}, ${esc(slot)}, ${esc(endSlot)}, 'booked', 'waiting', ${fee}, ${esc(isVideo)});`
    );

    const invId = `70000000-0000-0000-0000-${pad12(aptCounter)}`;
    const invNum = `INV-2026-${aptCounter.toString().padStart(5, "0")}`;
    emitInvoice({
      invId,
      invNum,
      patientId,
      aptId,
      amount: fee,
      status: isVideo ? "paid" : "pending",
      method: isVideo ? "card" : null,
      paidAt: isVideo ? "NOW()" : "NULL",
      createdAt: "NOW()",
      label: `${isVideo ? "Video consultation" : "OPD consultation"} — ${doctor.fullName}`,
      itemType: isVideo ? "video_fee" : "consultation_fee",
    });

    if (isVideo) {
      VIDEO_VISITS.push({ aptId, dateStr, slot, endSlot, ended: false });
    }
  }
}

out(``);
out(`-- 7. Doctor leave and altered OPD hours`);
for (const o of SCHEDULE_OVERRIDES) {
  out(
    `INSERT INTO schedule_overrides (doctor_id, date, is_leave, custom_start_time, custom_end_time, reason) VALUES (${esc(o.doctor.id)}, ${esc(dateInDays(o.day))}, ${esc(o.isLeave)}, ${esc(o.start || null)}, ${esc(o.end || null)}, ${esc(o.reason)});`
  );
}

out(``);
out(`-- 8. Vitals recorded at the desk before each consultation`);

// Deterministic but clinically plausible: a hypertensive patient reads high, everyone drifts a
// little around their own baseline.
function vitalsFor(n) {
  const hypertensive = n % 4 === 0;
  const diabetic = n % 7 === 0;
  return {
    systolic: (hypertensive ? 138 : 116) + (n % 9),
    diastolic: (hypertensive ? 88 : 74) + (n % 6),
    heartRate: 68 + (n % 17),
    temperature: (97.8 + ((n % 9) * 0.2)).toFixed(1),
    spo2: 96 + (n % 4),
    respiratory: 14 + (n % 5),
    glucose: diabetic ? 148 + (n % 42) : 88 + (n % 22),
  };
}

for (const v of COMPLETED_VISITS) {
  const vit = vitalsFor(v.n);
  out(
    `INSERT INTO vitals_records (patient_id, appointment_id, recorded_by, recorded_at, bp_systolic, bp_diastolic, heart_rate, temperature_f, spo2_percent, respiratory_rate, blood_glucose_mg_dl, notes) VALUES (${esc(v.patientId)}, ${esc(v.aptId)}, ${esc(RECEPTION_ID)}, ${esc(v.dateStr + " " + v.slot)}, ${vit.systolic}, ${vit.diastolic}, ${vit.heartRate}, ${vit.temperature}, ${vit.spo2}, ${vit.respiratory}, ${vit.glucose}, 'Recorded at front desk during check-in.');`
  );
}

// Ananya also logs her own readings between visits, which is what the patient app charts.
for (let w = 12; w >= 1; w--) {
  const vit = vitalsFor(w * 3);
  out(
    `INSERT INTO vitals_records (patient_id, recorded_by, recorded_at, bp_systolic, bp_diastolic, heart_rate, temperature_f, spo2_percent, respiratory_rate, notes) VALUES (${esc(DEMO_PATIENT_ID)}, ${esc(DEMO_PATIENT_ID)}, ${esc(dateInDays(-w * 7) + " 07:30:00")}, ${112 + (w % 8)}, ${72 + (w % 7)}, ${66 + (w % 12)}, ${(97.9 + ((w % 5) * 0.2)).toFixed(1)}, ${97 + (w % 3)}, ${14 + (w % 4)}, 'Home reading logged by patient.');`
  );
}
out(``);

out(`-- 9. Diagnostic lab orders, results and their own invoices`);

let labCounter = 0;
const LAB_IN_FLIGHT = ["ordered", "sample_collected", "processing"];

function emitLabOrder({ visit, status, createdAt, completedAt, testCount }) {
  labCounter++;
  const orderId = `b0000000-0000-0000-0000-${pad12(labCounter)}`;
  const orderNum = `LAB-2026-${labCounter.toString().padStart(5, "0")}`;
  out(
    `INSERT INTO lab_orders (id, order_number, consultation_id, patient_id, doctor_id, status, created_at, completed_at) VALUES (${esc(orderId)}, ${esc(orderNum)}, ${esc(visit.consultId)}, ${esc(visit.patientId)}, ${esc(visit.doctorId)}, ${esc(status)}, ${createdAt}, ${completedAt});`
  );

  let fee = 0;
  for (let k = 0; k < testCount; k++) {
    const idx = (labCounter * 3 + k) % LAB_TESTS.length;
    const test = LAB_TESTS[idx];
    const profile = LAB_RESULTS[test.code];
    const [value, flag] = profile.values[(labCounter + k) % profile.values.length];
    fee += test.fee;

    if (status === "completed") {
      out(
        `INSERT INTO lab_order_items (lab_order_id, test_id, result_value, reference_range, unit, flag, technician_notes) VALUES (${esc(orderId)}, ${esc(LAB_TEST_IDS[idx])}, ${esc(value)}, ${esc(profile.range)}, ${esc(profile.unit)}, ${esc(flag)}, ${esc(flag === "normal" ? "Within reference range." : "Flagged for physician review.")});`
      );
    } else {
      out(
        `INSERT INTO lab_order_items (lab_order_id, test_id, reference_range, unit, flag) VALUES (${esc(orderId)}, ${esc(LAB_TEST_IDS[idx])}, ${esc(profile.range)}, ${esc(profile.unit)}, 'normal');`
      );
    }
  }

  // Diagnostics are billed on their own receipt, separate from the consultation fee.
  if (status === "completed") {
    const invId = `71000000-0000-0000-0000-${pad12(labCounter)}`;
    const invNum = `INV-LAB-${labCounter.toString().padStart(5, "0")}`;
    emitInvoice({
      invId,
      invNum,
      patientId: visit.patientId,
      aptId: visit.aptId,
      amount: fee,
      status: "paid",
      method: "card",
      paidAt: completedAt,
      createdAt,
      label: `Diagnostic investigations (${testCount} test${testCount > 1 ? "s" : ""}) — ${orderNum}`,
      itemType: "lab_test",
    });
  }

  out(
    `INSERT INTO chart_access_logs (patient_id, accessed_by_user_id, access_type, resource_id, accessed_at) VALUES (${esc(visit.patientId)}, ${esc(visit.doctorId)}, 'order_labs', ${esc(orderId)}, ${createdAt});`
  );
}

const RECENT_CUTOFF = dateInDays(-4);
for (const visit of COMPLETED_VISITS) {
  if (visit.n % 4 !== 0 && !visit.demoLabs) continue;
  const inFlight = visit.dateStr >= RECENT_CUTOFF;
  const status = inFlight ? LAB_IN_FLIGHT[visit.n % LAB_IN_FLIGHT.length] : "completed";
  emitLabOrder({
    visit,
    status,
    createdAt: esc(visit.dateStr + " " + visit.endSlot),
    completedAt: status === "completed" ? esc(visit.dateStr + " 18:30:00") : "NULL",
    testCount: (visit.n % 3) + 1,
  });
}

// Today's clinic: samples just taken, so the lab bench has live work on screen.
for (const visit of TODAY_VISITS) {
  emitLabOrder({
    visit,
    status: LAB_IN_FLIGHT[visit.n % LAB_IN_FLIGHT.length],
    createdAt: "NOW()",
    completedAt: "NULL",
    testCount: 2,
  });
}
out(``);

out(`-- 10. Cancellation refunds (>24h notice: full refund under the clinic policy)`);
let refundCounter = 0;
for (const cv of CANCELLED_VISITS) {
  refundCounter++;
  out(
    `INSERT INTO refunds (refund_number, invoice_id, appointment_id, amount, cancellation_fee, reason, refund_status, refund_method, processed_at) VALUES (${esc("REF-2026-" + refundCounter.toString().padStart(5, "0"))}, ${esc(cv.invId)}, ${esc(cv.aptId)}, ${cv.fee}, 0, 'Patient cancelled more than 24 hours before the appointment.', 'processed', 'original_source', ${esc(cv.dateStr + " 10:15:00")});`
  );
}
out(``);

out(`-- 11. Patient reviews (recent feedback; doctor_profiles.rating_avg is the lifetime average)`);
const REVIEW_TEXT = [
  { rating: 5, text: "Dr. explained my reports line by line and never rushed the consultation. Token system meant almost no waiting." },
  { rating: 5, text: "Very thorough examination and the prescription was on my phone before I left the building." },
  { rating: 4, text: "Good consultation. The clinic was running about fifteen minutes late, but the front desk kept us informed." },
  { rating: 5, text: "Video consult worked flawlessly and saved me a trip across the city. Follow-up was scheduled on the call." },
  { rating: 4, text: "Clear advice on diet and medication. Would have liked a printed diet chart as well." },
  { rating: 5, text: "Second opinion that actually changed my treatment. Grateful for the time taken over my history." },
  { rating: 3, text: "The consultation itself was fine but the lab report took longer than the promised turnaround." },
  { rating: 5, text: "Paediatric visit for my son; the doctor was patient and gentle and explained everything to us." },
];

let reviewCounter = 0;
for (const v of COMPLETED_VISITS) {
  if (v.n % 3 !== 0 && !v.demoReview) continue;
  const r = REVIEW_TEXT[v.n % REVIEW_TEXT.length];
  reviewCounter++;
  out(
    `INSERT INTO patient_reviews (patient_id, doctor_id, appointment_id, rating, feedback, is_anonymous, created_at) VALUES (${esc(v.patientId)}, ${esc(v.doctorId)}, ${esc(v.aptId)}, ${r.rating}, ${esc(r.text)}, ${esc(reviewCounter % 11 === 0)}, ${esc(v.dateStr + " 20:00:00")});`
  );
}
out(``);

out(`-- 12. Telehealth video sessions`);
for (const vv of VIDEO_VISITS) {
  const token = `tele-${vv.aptId.slice(-12)}`;
  if (vv.ended) {
    out(
      `INSERT INTO telehealth_sessions (appointment_id, room_token, doctor_joined_at, patient_joined_at, ended_at, status, call_duration_seconds, connection_quality, created_at) VALUES (${esc(vv.aptId)}, ${esc(token)}, ${esc(vv.dateStr + " " + vv.slot)}, ${esc(vv.dateStr + " " + vv.slot)}, ${esc(vv.dateStr + " " + vv.endSlot)}, 'ended', ${600 + (token.length % 7) * 60}, ${esc(["excellent", "good", "good", "fair"][token.length % 4])}, ${esc(vv.dateStr + " " + vv.slot)});`
    );
  } else {
    out(
      `INSERT INTO telehealth_sessions (appointment_id, room_token, status, connection_quality, created_at) VALUES (${esc(vv.aptId)}, ${esc(token)}, 'waiting', 'good', NOW());`
    );
  }
}
out(``);

out(`-- 13. Notifications for the demo accounts`);
const NOTIFICATIONS = [
  { user: DEMO_PATIENT_ID, title: "Your token is next", message: "Token 3 is with the doctor. Please wait outside OPD Room 101.", type: "token_called", read: false, link: "/appointments", ago: 0 },
  { user: DEMO_PATIENT_ID, title: "Prescription ready", message: "Dr. Rajesh Varma has signed your prescription. Download the PDF from your records.", type: "prescription_ready", read: false, link: "/prescriptions", ago: 0 },
  { user: DEMO_PATIENT_ID, title: "Lab results are in", message: "Your Lipid Profile Comprehensive report is ready to view.", type: "lab_results_ready", read: false, link: "/lab-reports", ago: 1 },
  { user: DEMO_PATIENT_ID, title: "Payment received", message: "We have received Rs. 900 towards invoice for your consultation today.", type: "payment_received", read: true, link: "/invoices", ago: 0 },
  { user: DEMO_PATIENT_ID, title: "Appointment confirmed", message: "Aarav's paediatric review with Dr. Meera Nambiar is confirmed.", type: "appointment_confirmed", read: true, link: "/appointments", ago: 4 },
  { user: DOCTORS[0].id, title: "Patient checked in", message: "Token 4 has checked in and is waiting for you in OPD Room 101.", type: "token_called", read: false, link: "/queue", ago: 0 },
  { user: DOCTORS[0].id, title: "Video visit waiting", message: "A patient has joined the telehealth waiting room.", type: "consultation_started", read: false, link: "/queue", ago: 0 },
  { user: DOCTORS[0].id, title: "Critical lab value", message: "HbA1c 9.2% flagged critical for a patient in today's list.", type: "lab_results_ready", read: false, link: "/patients", ago: 0 },
  { user: DOCTORS[0].id, title: "New review", message: "You received a 5-star review after yesterday's consultation.", type: "appointment_confirmed", read: true, link: "/reviews", ago: 1 },
  { user: STAFF[0].id, title: "Refund processed", message: "A cancellation refund was returned to the original payment method.", type: "appointment_cancelled", read: false, link: "/refunds", ago: 0 },
  { user: STAFF[0].id, title: "Doctor on leave", message: "Dr. Meera Nambiar is away for the immunisation camp; two slots need reassigning.", type: "appointment_cancelled", read: false, link: "/doctors", ago: 0 },
  { user: STAFF[0].id, title: "Collections summary", message: "Yesterday's counter collection has been reconciled.", type: "payment_received", read: true, link: "/billing", ago: 1 },
];

for (const n of NOTIFICATIONS) {
  out(
    `INSERT INTO notifications (user_id, title, message, type, is_read, link, created_at) VALUES (${esc(n.user)}, ${esc(n.title)}, ${esc(n.message)}, ${esc(n.type)}, ${esc(n.read)}, ${esc(n.link)}, ${n.ago === 0 ? "NOW()" : esc(dateInDays(-n.ago) + " 09:00:00")});`
  );
}

out(``);
out(`-- End of CareClinic Seed Data`);
console.log(lines.join("\n"));
