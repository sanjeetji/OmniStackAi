/** Scheduling and appointment lifecycle service for CareClinic. */

import { query, withTransaction } from "../db.ts";
import {
  BadRequestError,
  ConflictError,
  NotFoundError,
  ForbiddenError,
} from "../lib/errors.ts";
import { assertValidTransition, type AppointmentStatus } from "../lib/appointment-state.ts";
import { calculateCancellationRefund } from "../lib/money.ts";
import { generateSlotsForShift, type TimeSlot } from "../lib/slot-generator.ts";
import { broadcastEvent } from "../routes/stream.ts";
import { nextDocumentNumber } from "../lib/document-number.ts";

export interface BookAppointmentInput {
  patientId: string;
  doctorId: string;
  clinicId?: string;
  forFamilyMemberId?: string;
  appointmentType: "in_clinic" | "video";
  scheduledDate: string; // YYYY-MM-DD
  startTime: string;     // HH:MM:SS
  notes?: string;
  paymentMethod?: string;
}

export class SchedulingService {
  /** Calculate all available and booked slots for a doctor on a given date. */
  static async getDoctorAvailableSlots(
    doctorId: string,
    dateString: string // YYYY-MM-DD
  ): Promise<TimeSlot[]> {
    const targetDate = new Date(dateString);
    const dayOfWeek = targetDate.getDay(); // 0=Sunday, 6=Saturday

    // 1. Check leave overrides
    const overrideRes = await query(
      `SELECT is_leave, custom_start_time, custom_end_time
       FROM schedule_overrides
       WHERE doctor_id = $1 AND date = $2`,
      [doctorId, dateString]
    );

    if (overrideRes.rows.length > 0 && overrideRes.rows[0].is_leave) {
      return []; // Doctor on leave
    }

    // 2. Fetch standard availability for this day of week
    const availRes = await query(
      `SELECT start_time, end_time, slot_duration_mins
       FROM doctor_availability
       WHERE doctor_id = $1 AND day_of_week = $2 AND is_available = TRUE`,
      [doctorId, dayOfWeek]
    );

    if (availRes.rows.length === 0) {
      return [];
    }

    // 3. Fetch existing active bookings for this doctor on this date
    const bookedRes = await query(
      `SELECT start_time
       FROM appointments
       WHERE doctor_id = $1 AND scheduled_date = $2 AND status NOT IN ('cancelled')`,
      [doctorId, dateString]
    );

    const bookedSet = new Set<string>(
      bookedRes.rows.map((r: { start_time: string }) => r.start_time.slice(0, 8))
    );

    const shift = availRes.rows[0];
    const shiftStartTime = overrideRes.rows[0]?.custom_start_time || shift.start_time;
    const shiftEndTime = overrideRes.rows[0]?.custom_end_time || shift.end_time;

    return generateSlotsForShift(
      {
        startTime: shiftStartTime.slice(0, 8),
        endTime: shiftEndTime.slice(0, 8),
        slotDurationMins: shift.slot_duration_mins || 20,
      },
      bookedSet
    );
  }

  /** Book an appointment with zero-double-booking guarantee. */
  static async bookAppointment(input: BookAppointmentInput) {
    return withTransaction(async (client) => {
      // 1. Verify doctor exists and fetch fee
      const docRes = await client.query(
        `SELECT u.full_name, dp.clinic_id, dp.consultation_fee_inr, dp.video_fee_inr
         FROM users u
         JOIN doctor_profiles dp ON dp.doctor_id = u.id
         WHERE u.id = $1 AND u.role = 'doctor'`,
        [input.doctorId]
      );

      if (docRes.rows.length === 0) {
        throw new NotFoundError("Doctor profile not found");
      }

      const doc = docRes.rows[0];
      const clinicId = input.clinicId || doc.clinic_id;
      const fee =
        input.appointmentType === "video" ? doc.video_fee_inr : doc.consultation_fee_inr;

      // Calculate 20 minute end time
      const [h, m] = input.startTime.split(":").map(Number);
      const startMins = h * 60 + m;
      const endMins = startMins + 20;
      const endHour = Math.floor(endMins / 60)
        .toString()
        .padStart(2, "0");
      const endMin = (endMins % 60).toString().padStart(2, "0");
      const endTime = `${endHour}:${endMin}:00`;

      // 2. Next appointment number in this year's series
      const aptNumber = await nextDocumentNumber(client, "appointments");

      // 3. Insert appointment (protected by uq_doctor_slot)
      let aptRow;
      try {
        const insertRes = await client.query(
          `INSERT INTO appointments (
            appointment_number, patient_id, for_family_member_id, doctor_id, clinic_id,
            appointment_type, scheduled_date, start_time, end_time, status,
            fee_amount, is_paid, payment_method, notes
          ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, 'booked', $10, FALSE, $11, $12)
          RETURNING *`,
          [
            aptNumber,
            input.patientId,
            input.forFamilyMemberId || null,
            input.doctorId,
            clinicId,
            input.appointmentType,
            input.scheduledDate,
            input.startTime,
            endTime,
            fee,
            input.paymentMethod || null,
            input.notes || null,
          ]
        );
        aptRow = insertRes.rows[0];
      } catch (err: any) {
        if (err.code === "23505") {
          // Unique violation on uq_doctor_slot
          throw new ConflictError(
            `Doctor slot on ${input.scheduledDate} at ${input.startTime} was just booked by another patient. Please choose an adjacent time.`
          );
        }
        throw err;
      }

      // 4. Create initial pending invoice
      const invNumber = await nextDocumentNumber(client, "invoices");

      const invRes = await client.query(
        `INSERT INTO invoices (
          invoice_number, patient_id, appointment_id, total_amount, discount_amount, net_payable,
          payment_status, payment_method
        ) VALUES ($1, $2, $3, $4, 0, $4, 'pending', $5)
        RETURNING *`,
        [invNumber, input.patientId, aptRow.id, fee, input.paymentMethod || null]
      );

      await client.query(
        `INSERT INTO invoice_items (invoice_id, description, item_type, quantity, unit_price, amount)
         VALUES ($1, $2, $3, 1, $4, $4)`,
        [
          invRes.rows[0].id,
          `${input.appointmentType === "video" ? "Telehealth Video Consultation" : "In-Clinic Consultation"} with ${doc.full_name}`,
          input.appointmentType === "video" ? "video_fee" : "consultation_fee",
          fee,
        ]
      );

      // 5. If video visit, create telehealth session room
      if (input.appointmentType === "video") {
        const roomToken = `room_cc_${aptRow.id.replace(/-/g, "").slice(0, 16)}`;
        await client.query(
          `INSERT INTO telehealth_sessions (appointment_id, room_token, status)
           VALUES ($1, $2, 'waiting')`,
          [aptRow.id, roomToken]
        );
      }

      // 6. Notify patient
      await client.query(
        `INSERT INTO notifications (user_id, title, message, type, link)
         VALUES ($1, $2, $3, 'appointment_booked', $4)`,
        [
          input.patientId,
          "Appointment Scheduled",
          `Your appointment with ${doc.full_name} is confirmed for ${input.scheduledDate} at ${input.startTime}.`,
          `/appointments/${aptRow.id}`,
        ]
      );

      broadcastEvent("appointment_booked", {
        appointmentId: aptRow.id,
        doctorId: input.doctorId,
        patientId: input.patientId,
        scheduledDate: input.scheduledDate,
        startTime: input.startTime,
      });

      return {
        ...aptRow,
        invoice: invRes.rows[0],
      };
    });
  }

  /** Check in patient on arrival, allocate sequential queue token, and alert doctor. */
  static async checkIn(appointmentId: string, receptionistId?: string) {
    return withTransaction(async (client) => {
      const aptRes = await client.query(
        `SELECT a.*, u.full_name as doctor_name
         FROM appointments a
         JOIN users u ON u.id = a.doctor_id
         WHERE a.id = $1`,
        [appointmentId]
      );

      if (aptRes.rows.length === 0) {
        throw new NotFoundError("Appointment not found");
      }

      const apt = aptRes.rows[0];
      assertValidTransition(apt.status as AppointmentStatus, "checked_in");

      // Calculate next token number for this doctor and date
      const maxTokenRes = await client.query(
        `SELECT COALESCE(MAX(token_number), 0) + 1 as next_token
         FROM appointments
         WHERE doctor_id = $1 AND scheduled_date = $2`,
        [apt.doctor_id, apt.scheduled_date]
      );

      const nextToken = parseInt(maxTokenRes.rows[0].next_token, 10);

      const updatedRes = await client.query(
        `UPDATE appointments
         SET status = 'checked_in', token_number = $1, queue_status = 'waiting', updated_at = NOW()
         WHERE id = $2
         RETURNING *`,
        [nextToken, appointmentId]
      );

      // Notify doctor
      await client.query(
        `INSERT INTO notifications (user_id, title, message, type, link)
         VALUES ($1, $2, $3, 'token_called', $4)`,
        [
          apt.doctor_id,
          `Patient Checked In: Token #${nextToken}`,
          `Patient has arrived for their ${apt.start_time} visit.`,
          `/queue`,
        ]
      );

      broadcastEvent("queue_updated", {
        appointmentId,
        doctorId: apt.doctor_id,
        tokenNumber: nextToken,
        status: "checked_in",
        queueStatus: "waiting",
      });

      return updatedRes.rows[0];
    });
  }

  /** Cancel an appointment and apply refund policy rules. */
  static async cancelAppointment(
    appointmentId: string,
    cancelledBy: string,
    reason: string
  ) {
    return withTransaction(async (client) => {
      const aptRes = await client.query(
        `SELECT a.*, inv.id as invoice_id, inv.payment_status
         FROM appointments a
         LEFT JOIN invoices inv ON inv.appointment_id = a.id
         WHERE a.id = $1`,
        [appointmentId]
      );

      if (aptRes.rows.length === 0) {
        throw new NotFoundError("Appointment not found");
      }

      const apt = aptRes.rows[0];
      assertValidTransition(apt.status as AppointmentStatus, "cancelled");

      const refundPolicy = calculateCancellationRefund(
        apt.fee_amount,
        apt.scheduled_date.toISOString().slice(0, 10),
        apt.start_time
      );

      // Update appointment
      const updatedApt = await client.query(
        `UPDATE appointments
         SET status = 'cancelled', queue_status = 'cancelled',
             cancellation_reason = $1, cancelled_by = $2, cancelled_at = NOW(), updated_at = NOW()
         WHERE id = $3
         RETURNING *`,
        [reason, cancelledBy, appointmentId]
      );

      // Handle refund record if paid
      if (apt.is_paid && apt.invoice_id && refundPolicy.refundAmount > 0) {
        const refNumber = await nextDocumentNumber(client, "refunds");

        await client.query(
          `INSERT INTO refunds (
            refund_number, invoice_id, appointment_id, amount, cancellation_fee, reason
          ) VALUES ($1, $2, $3, $4, $5, $6)`,
          [
            refNumber,
            apt.invoice_id,
            appointmentId,
            refundPolicy.refundAmount,
            refundPolicy.cancellationFee,
            `Cancellation refund (${refundPolicy.reasonExplanation})`,
          ]
        );

        await client.query(
          `UPDATE invoices
           SET payment_status = $1
           WHERE id = $2`,
          [
            refundPolicy.refundPercentage === 100 ? "refunded" : "partially_refunded",
            apt.invoice_id,
          ]
        );
      }

      broadcastEvent("appointment_cancelled", {
        appointmentId,
        doctorId: apt.doctor_id,
        patientId: apt.patient_id,
        refundAmount: refundPolicy.refundAmount,
      });

      return {
        appointment: updatedApt.rows[0],
        refund: refundPolicy,
      };
    });
  }
}
