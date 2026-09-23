/** Clinical care domain service: chart audit, SOAP documentation, diagnoses, and immutable prescriptions. */

import { query, withTransaction } from "../db.ts";
import {
  BadRequestError,
  NotFoundError,
  ForbiddenError,
  UnprocessableError,
} from "../lib/errors.ts";
import { assertValidTransition, type AppointmentStatus } from "../lib/appointment-state.ts";
import { broadcastEvent } from "../routes/stream.ts";

export interface SoapInput {
  subjective?: string;
  objective?: string;
  assessment?: string;
  plan?: string;
  followUpDate?: string;
  diagnoses?: Array<{
    icd10Code: string;
    conditionName: string;
    isPrimary?: boolean;
    notes?: string;
  }>;
}

export interface PrescriptionItemInput {
  medicineName: string;
  genericName?: string;
  dosageForm: "tablet" | "capsule" | "syrup" | "injection" | "inhaler" | "drops" | "ointment";
  strength: string;
  frequency: string;
  timing: "after_food" | "before_food" | "with_food" | "empty_stomach" | "as_needed";
  durationDays: number;
  instructions?: string;
}

export class ClinicalService {
  /** Log access to patient medical chart for HIPAA / healthcare audit compliance. */
  static async logChartAccess(
    patientId: string,
    accessedByUserId: string,
    accessType: "view_chart" | "view_soap" | "view_prescription" | "edit_soap" | "issue_prescription" | "view_labs" | "order_labs",
    resourceId?: string,
    ip = "127.0.0.1",
    userAgent?: string
  ) {
    await query(
      `INSERT INTO chart_access_logs (
        patient_id, accessed_by_user_id, access_type, resource_id, ip_address, user_agent
      ) VALUES ($1, $2, $3, $4, $5, $6)`,
      [patientId, accessedByUserId, accessType, resourceId || null, ip, userAgent || null]
    );
  }

  /** Retrieve complete longitudinal medical chart with mandatory access logging. */
  static async getPatientChart(patientId: string, accessedByUserId: string, ip = "127.0.0.1") {
    // 1. Log access first
    await this.logChartAccess(patientId, accessedByUserId, "view_chart", patientId, ip);

    // 2. Fetch patient demographics
    const userRes = await query(
      `SELECT u.id, u.full_name, u.email, u.phone, p.dob, p.gender, p.blood_group,
              p.height_cm, p.weight_kg, p.emergency_contact, p.emergency_phone
       FROM users u
       LEFT JOIN patient_profiles p ON p.patient_id = u.id
       WHERE u.id = $1`,
      [patientId]
    );

    if (userRes.rows.length === 0) {
      throw new NotFoundError("Patient record not found");
    }

    // 3. Medical history
    const historyRes = await query(
      `SELECT allergies, chronic_conditions, current_medications, past_surgeries, family_history, lifestyle_notes
       FROM medical_histories
       WHERE patient_id = $1`,
      [patientId]
    );

    // 4. Vitals records (latest 10)
    const vitalsRes = await query(
      `SELECT * FROM vitals_records
       WHERE patient_id = $1
       ORDER BY recorded_at DESC LIMIT 10`,
      [patientId]
    );

    // 5. Past consultations & diagnoses
    const consultsRes = await query(
      `SELECT c.*, a.appointment_number, a.scheduled_date, u.full_name as doctor_name
       FROM consultations c
       JOIN appointments a ON a.id = c.appointment_id
       JOIN users u ON u.id = c.doctor_id
       WHERE c.patient_id = $1
       ORDER BY c.created_at DESC`,
      [patientId]
    );

    // 6. Past prescriptions
    const rxRes = await query(
      `SELECT p.*, u.full_name as doctor_name
       FROM prescriptions p
       JOIN users u ON u.id = p.doctor_id
       WHERE p.patient_id = $1
       ORDER BY p.created_at DESC`,
      [patientId]
    );

    // 7. Lab orders & items
    const labRes = await query(
      `SELECT l.*, u.full_name as doctor_name
       FROM lab_orders l
       JOIN users u ON u.id = l.doctor_id
       WHERE l.patient_id = $1
       ORDER BY l.created_at DESC`,
      [patientId]
    );

    return {
      profile: userRes.rows[0],
      medicalHistory: historyRes.rows[0] || {
        allergies: [],
        chronic_conditions: [],
        current_medications: [],
        past_surgeries: [],
      },
      vitals: vitalsRes.rows,
      consultations: consultsRes.rows,
      prescriptions: rxRes.rows,
      labOrders: labRes.rows,
    };
  }

  /** Start a consultation session for a checked-in appointment. */
  static async startConsultation(appointmentId: string, doctorId: string) {
    return withTransaction(async (client) => {
      const aptRes = await client.query(
        `SELECT * FROM appointments WHERE id = $1`,
        [appointmentId]
      );

      if (aptRes.rows.length === 0) {
        throw new NotFoundError("Appointment not found");
      }

      const apt = aptRes.rows[0];
      if (apt.doctor_id !== doctorId) {
        throw new ForbiddenError("Only assigned physician can conduct consultation");
      }

      assertValidTransition(apt.status as AppointmentStatus, "in_consult");

      // Update appointment status
      await client.query(
        `UPDATE appointments
         SET status = 'in_consult', queue_status = 'with_doctor', updated_at = NOW()
         WHERE id = $1`,
        [appointmentId]
      );

      // Create consultation record if not existing
      const consultRes = await client.query(
        `INSERT INTO consultations (appointment_id, doctor_id, patient_id)
         VALUES ($1, $2, $3)
         ON CONFLICT (appointment_id) DO UPDATE SET doctor_id = EXCLUDED.doctor_id
         RETURNING *`,
        [appointmentId, doctorId, apt.patient_id]
      );

      broadcastEvent("consultation_started", {
        appointmentId,
        doctorId,
        patientId: apt.patient_id,
        consultationId: consultRes.rows[0].id,
      });

      return consultRes.rows[0];
    });
  }

  /** Record or update SOAP clinical notes and ICD-10 diagnostic codes. */
  static async saveSoapNotes(
    consultationId: string,
    doctorId: string,
    soap: SoapInput,
    ip = "127.0.0.1"
  ) {
    return withTransaction(async (client) => {
      const cRes = await client.query(
        `SELECT * FROM consultations WHERE id = $1`,
        [consultationId]
      );

      if (cRes.rows.length === 0) {
        throw new NotFoundError("Consultation not found");
      }

      const consult = cRes.rows[0];
      if (consult.doctor_id !== doctorId) {
        throw new ForbiddenError("Only consulting physician can record SOAP clinical notes");
      }

      // Check if consultation is already finalized/completed
      if (consult.completed_at) {
        throw new BadRequestError("Cannot edit SOAP notes of a completed and finalized consultation");
      }

      // 1. Update SOAP fields
      const updatedConsult = await client.query(
        `UPDATE consultations
         SET subjective = COALESCE($1, subjective),
             objective = COALESCE($2, objective),
             assessment = COALESCE($3, assessment),
             plan = COALESCE($4, plan),
             follow_up_date = COALESCE($5, follow_up_date)
         WHERE id = $6
         RETURNING *`,
        [
          soap.subjective ?? null,
          soap.objective ?? null,
          soap.assessment ?? null,
          soap.plan ?? null,
          soap.followUpDate ?? null,
          consultationId,
        ]
      );

      // 2. Upsert diagnoses if provided
      if (soap.diagnoses && soap.diagnoses.length > 0) {
        await client.query(`DELETE FROM diagnoses WHERE consultation_id = $1`, [consultationId]);

        for (const diag of soap.diagnoses) {
          await client.query(
            `INSERT INTO diagnoses (consultation_id, icd10_code, condition_name, is_primary, notes)
             VALUES ($1, $2, $3, $4, $5)`,
            [
              consultationId,
              diag.icd10Code,
              diag.conditionName,
              diag.isPrimary || false,
              diag.notes || null,
            ]
          );
        }
      }

      await this.logChartAccess(
        consult.patient_id,
        doctorId,
        "edit_soap",
        consultationId,
        ip
      );

      return updatedConsult.rows[0];
    });
  }

  /** Issue and digitally sign an immutable prescription. */
  static async issuePrescription(
    consultationId: string,
    doctorId: string,
    diagnosisSummary: string,
    items: PrescriptionItemInput[],
    ip = "127.0.0.1"
  ) {
    if (!items || items.length === 0) {
      throw new BadRequestError("Prescription must contain at least one medication item");
    }

    return withTransaction(async (client) => {
      const cRes = await client.query(
        `SELECT c.*, u.full_name as doctor_name, u.email as doctor_email,
                dp.license_number
         FROM consultations c
         JOIN users u ON u.id = c.doctor_id
         JOIN doctor_profiles dp ON dp.doctor_id = u.id
         WHERE c.id = $1`,
        [consultationId]
      );

      if (cRes.rows.length === 0) {
        throw new NotFoundError("Consultation not found");
      }

      const consult = cRes.rows[0];
      if (consult.doctor_id !== doctorId) {
        throw new ForbiddenError("Only consulting physician can issue prescription");
      }

      // Check if prescription already exists and is immutable
      const existingRxRes = await client.query(
        `SELECT * FROM prescriptions WHERE consultation_id = $1`,
        [consultationId]
      );

      if (existingRxRes.rows.length > 0 && existingRxRes.rows[0].is_immutable) {
        throw new BadRequestError(
          "Prescription for this consultation has already been digitally signed and is immutable."
        );
      }

      // Generate sequential prescription number
      const rxCountRes = await client.query(`SELECT COUNT(*) as total FROM prescriptions`);
      const rxSeq = parseInt(rxCountRes.rows[0].total, 10) + 1;
      const rxNumber = `RX-2026-${rxSeq.toString().padStart(5, "0")}`;

      const digitalSig = `SIG-CARECLINIC-${doctorId.slice(0, 8)}-${Date.now()}`;

      // Insert or update prescription record
      let rxRow;
      if (existingRxRes.rows.length === 0) {
        const insertRx = await client.query(
          `INSERT INTO prescriptions (
            prescription_number, consultation_id, patient_id, doctor_id,
            diagnosis_summary, signed_at, is_immutable, digital_signature
          ) VALUES ($1, $2, $3, $4, $5, NOW(), TRUE, $6)
          RETURNING *`,
          [
            rxNumber,
            consultationId,
            consult.patient_id,
            doctorId,
            diagnosisSummary,
            digitalSig,
          ]
        );
        rxRow = insertRx.rows[0];
      } else {
        const updateRx = await client.query(
          `UPDATE prescriptions
           SET diagnosis_summary = $1, signed_at = NOW(), is_immutable = TRUE, digital_signature = $2
           WHERE id = $3
           RETURNING *`,
          [diagnosisSummary, digitalSig, existingRxRes.rows[0].id]
        );
        rxRow = updateRx.rows[0];
      }

      // Insert prescription items
      await client.query(`DELETE FROM prescription_items WHERE prescription_id = $1`, [rxRow.id]);

      const insertedItems = [];
      for (const item of items) {
        const itemRes = await client.query(
          `INSERT INTO prescription_items (
            prescription_id, medicine_name, generic_name, dosage_form,
            strength, frequency, timing, duration_days, instructions
          ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
          RETURNING *`,
          [
            rxRow.id,
            item.medicineName,
            item.genericName || null,
            item.dosageForm,
            item.strength,
            item.frequency,
            item.timing,
            item.durationDays,
            item.instructions || null,
          ]
        );
        insertedItems.push(itemRes.rows[0]);
      }

      // Notify patient
      await client.query(
        `INSERT INTO notifications (user_id, title, message, type, link)
         VALUES ($1, $2, $3, 'prescription_ready', $4)`,
        [
          consult.patient_id,
          "New Prescription Issued",
          `Dr. ${consult.doctor_name} has issued your e-prescription #${rxNumber}.`,
          `/prescriptions/${rxRow.id}`,
        ]
      );

      await this.logChartAccess(
        consult.patient_id,
        doctorId,
        "issue_prescription",
        rxRow.id,
        ip
      );

      broadcastEvent("prescription_issued", {
        prescriptionId: rxRow.id,
        prescriptionNumber: rxNumber,
        patientId: consult.patient_id,
        doctorId,
      });

      return {
        ...rxRow,
        items: insertedItems,
      };
    });
  }

  /** Complete and finalize a clinical consultation. */
  static async completeConsultation(consultationId: string, doctorId: string) {
    return withTransaction(async (client) => {
      const cRes = await client.query(
        `SELECT c.*, a.id as apt_id, a.status as apt_status
         FROM consultations c
         JOIN appointments a ON a.id = c.appointment_id
         WHERE c.id = $1`,
        [consultationId]
      );

      if (cRes.rows.length === 0) {
        throw new NotFoundError("Consultation not found");
      }

      const consult = cRes.rows[0];
      if (consult.doctor_id !== doctorId) {
        throw new ForbiddenError("Only consulting physician can finalize visit");
      }

      assertValidTransition(consult.apt_status as AppointmentStatus, "completed");

      // Finalize consultation
      await client.query(
        `UPDATE consultations
         SET completed_at = NOW()
         WHERE id = $1`,
        [consultationId]
      );

      // Finalize appointment
      await client.query(
        `UPDATE appointments
         SET status = 'completed', queue_status = 'done', updated_at = NOW()
         WHERE id = $1`,
        [consult.apt_id]
      );

      broadcastEvent("consultation_completed", {
        consultationId,
        appointmentId: consult.apt_id,
        doctorId,
        patientId: consult.patient_id,
      });

      return { success: true, completedAt: new Date().toISOString() };
    });
  }
}
