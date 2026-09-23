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

for (const t of LAB_TESTS) {
  out(
    `INSERT INTO lab_test_catalog (code, name, category, standard_fee_inr, turnaround_hours, sample_type) VALUES (${esc(t.code)}, ${esc(t.name)}, ${esc(t.category)}, ${t.fee}, ${t.hours}, ${esc(t.sample)}) ON CONFLICT (code) DO NOTHING;`
  );
}
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

  const fn = FIRST_NAMES[(i - 1) % FIRST_NAMES.length];
  const ln = LAST_NAMES[Math.floor((i - 1) / FIRST_NAMES.length) % LAST_NAMES.length];
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

// 6. Appointments (900 Appointments over past 90 days and next 14 days)
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

// Generate 700 past appointments (-90 days to -1 day)
for (let dayOffset = 90; dayOffset >= 1; dayOffset--) {
  const d = new Date();
  d.setDate(d.getDate() - dayOffset);
  const dateStr = d.toISOString().slice(0, 10);
  const isWeekend = d.getDay() === 0;
  if (isWeekend) continue; // Clinic OPD closed on Sundays

  // 8 appointments per weekday across doctors
  for (let sIdx = 0; sIdx < 8; sIdx++) {
    aptCounter++;
    if (aptCounter > 700) break;

    const aptId = `60000000-0000-0000-0000-${aptCounter.toString().padStart(12, "0")}`;
    const aptNumber = `APT-2026-${aptCounter.toString().padStart(5, "0")}`;
    const doctor = DOCTORS[aptCounter % DOCTORS.length];
    const patientId = PATIENT_IDS[aptCounter % PATIENT_IDS.length];
    const slot = SLOTS[sIdx * 3]; // 09:00, 10:00, 11:00, 12:00, 16:00, 17:00, 18:00, 19:00
    const [h, m] = slot.split(":").map(Number);
    const endSlot = `${h.toString().padStart(2, "0")}:${(m + 20).toString().padStart(2, "0")}:00`;
    const isVideo = aptCounter % 4 === 0;
    const fee = isVideo ? doctor.videoFee : doctor.clinicFee;

    // Mostly completed, 5% cancelled, 5% no_show
    let status = "completed";
    if (aptCounter % 20 === 0) status = "cancelled";
    else if (aptCounter % 25 === 0) status = "no_show";

    out(
      `INSERT INTO appointments (id, appointment_number, patient_id, doctor_id, clinic_id, appointment_type, scheduled_date, start_time, end_time, status, token_number, queue_status, fee_amount, is_paid, payment_method) VALUES (${esc(aptId)}, ${esc(aptNumber)}, ${esc(patientId)}, ${esc(doctor.id)}, ${esc(CLINIC_ID)}, ${esc(isVideo ? "video" : "in_clinic")}, ${esc(dateStr)}, ${esc(slot)}, ${esc(endSlot)}, ${esc(status)}, ${sIdx + 1}, ${esc(status === "completed" ? "done" : status)}, ${fee}, TRUE, 'upi');`
    );

    // Invoice
    const invId = `70000000-0000-0000-0000-${aptCounter.toString().padStart(12, "0")}`;
    const invNum = `INV-2026-${aptCounter.toString().padStart(5, "0")}`;
    out(
      `INSERT INTO invoices (id, invoice_number, patient_id, appointment_id, total_amount, net_payable, payment_status, payment_method, paid_at) VALUES (${esc(invId)}, ${esc(invNum)}, ${esc(patientId)}, ${esc(aptId)}, ${fee}, ${fee}, 'paid', 'upi', ${esc(dateStr + " 09:05:00")});`
    );

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
    }
  }
}

// Generate 200 today & upcoming appointments (0 to +14 days)
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

  out(
    `INSERT INTO appointments (id, appointment_number, patient_id, doctor_id, clinic_id, appointment_type, scheduled_date, start_time, end_time, status, token_number, queue_status, fee_amount, is_paid) VALUES (${esc(aptId)}, ${esc(aptNumber)}, ${esc(ta.patient)}, ${esc(doctor.id)}, ${esc(CLINIC_ID)}, 'in_clinic', ${esc(todayStr)}, ${esc(ta.slot)}, ${esc(ta.end)}, ${esc(ta.status)}, ${ta.token || "NULL"}, ${esc(ta.qStatus)}, ${doctor.clinicFee}, TRUE);`
  );

  const invId = `70000000-0000-0000-0000-${aptCounter.toString().padStart(12, "0")}`;
  const invNum = `INV-2026-${aptCounter.toString().padStart(5, "0")}`;
  out(
    `INSERT INTO invoices (id, invoice_number, patient_id, appointment_id, total_amount, net_payable, payment_status, payment_method, paid_at) VALUES (${esc(invId)}, ${esc(invNum)}, ${esc(ta.patient)}, ${esc(aptId)}, ${doctor.clinicFee}, ${doctor.clinicFee}, 'paid', 'upi', NOW());`
  );

  if (ta.status === "in_consult" || ta.status === "completed") {
    const consultId = `80000000-0000-0000-0000-${aptCounter.toString().padStart(12, "0")}`;
    out(
      `INSERT INTO consultations (id, appointment_id, doctor_id, patient_id, started_at, subjective, objective, assessment, plan) VALUES (${esc(consultId)}, ${esc(aptId)}, ${esc(doctor.id)}, ${esc(ta.patient)}, NOW(), 'Routine quarterly blood pressure and cardiac review.', 'BP 128/82 mmHg, HR 74 bpm. Heart sounds S1 S2 normal.', 'Hypertension stage 1 - well controlled.', 'Continue low sodium diet and regular morning walk.');`
    );
    out(
      `INSERT INTO diagnoses (consultation_id, icd10_code, condition_name, is_primary) VALUES (${esc(consultId)}, 'I10', 'Essential (primary) hypertension', TRUE);`
    );
  }
}

// Generate remaining upcoming appointments up to +14 days
for (let day = 1; day <= 14; day++) {
  const d = new Date();
  d.setDate(d.getDate() + day);
  const dateStr = d.toISOString().slice(0, 10);
  if (d.getDay() === 0) continue;

  for (let s = 0; s < 12; s++) {
    aptCounter++;
    if (aptCounter > 900) break;

    const aptId = `60000000-0000-0000-0000-${aptCounter.toString().padStart(12, "0")}`;
    const aptNumber = `APT-2026-${aptCounter.toString().padStart(5, "0")}`;
    const doctor = DOCTORS[s % DOCTORS.length];
    const patientId = PATIENT_IDS[(s * 7 + day) % PATIENT_IDS.length];
    const slot = SLOTS[s];
    const [h, m] = slot.split(":").map(Number);
    const endSlot = `${h.toString().padStart(2, "0")}:${(m + 20).toString().padStart(2, "0")}:00`;
    const isVideo = s % 3 === 0;

    out(
      `INSERT INTO appointments (id, appointment_number, patient_id, doctor_id, clinic_id, appointment_type, scheduled_date, start_time, end_time, status, queue_status, fee_amount, is_paid) VALUES (${esc(aptId)}, ${esc(aptNumber)}, ${esc(patientId)}, ${esc(doctor.id)}, ${esc(CLINIC_ID)}, ${esc(isVideo ? "video" : "in_clinic")}, ${esc(dateStr)}, ${esc(slot)}, ${esc(endSlot)}, 'booked', 'waiting', ${isVideo ? doctor.videoFee : doctor.clinicFee}, TRUE);`
    );

    const invId = `70000000-0000-0000-0000-${aptCounter.toString().padStart(12, "0")}`;
    const invNum = `INV-2026-${aptCounter.toString().padStart(5, "0")}`;
    out(
      `INSERT INTO invoices (id, invoice_number, patient_id, appointment_id, total_amount, net_payable, payment_status, payment_method) VALUES (${esc(invId)}, ${esc(invNum)}, ${esc(patientId)}, ${esc(aptId)}, ${doctor.clinicFee}, ${doctor.clinicFee}, 'paid', 'upi');`
    );
  }
}

out(``);
out(`-- End of CareClinic Seed Data`);
console.log(lines.join("\n"));
