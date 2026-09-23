/** Telehealth video session management and mock WebRTC broker. */

import { query, withTransaction } from "../db.ts";
import { NotFoundError, BadRequestError } from "../lib/errors.ts";
import { broadcastEvent } from "../routes/stream.ts";

export class TelehealthService {
  /** Retrieve or initialize telehealth room for a video appointment. */
  static async getOrCreateRoom(appointmentId: string) {
    const existing = await query(
      `SELECT * FROM telehealth_sessions WHERE appointment_id = $1`,
      [appointmentId]
    );

    if (existing.rows.length > 0) {
      return existing.rows[0];
    }

    const roomToken = `room_cc_${appointmentId.replace(/-/g, "").slice(0, 16)}`;
    const res = await query(
      `INSERT INTO telehealth_sessions (appointment_id, room_token, status)
       VALUES ($1, $2, 'waiting')
       RETURNING *`,
      [appointmentId, roomToken]
    );

    return res.rows[0];
  }

  /** Participant joins video room. */
  static async joinRoom(appointmentId: string, role: "patient" | "doctor") {
    return withTransaction(async (client) => {
      const existing = await client.query(
        `SELECT * FROM telehealth_sessions WHERE appointment_id = $1`,
        [appointmentId]
      );

      if (existing.rows.length === 0) {
        throw new NotFoundError("Telehealth session not found for this appointment");
      }

      const session = existing.rows[0];
      const isDoctor = role === "doctor";
      const isPatient = role === "patient";

      const doctorJoinedAt = isDoctor ? new Date() : session.doctor_joined_at;
      const patientJoinedAt = isPatient ? new Date() : session.patient_joined_at;

      // Status becomes active once both have joined or at least one is in room
      const newStatus = doctorJoinedAt && patientJoinedAt ? "active" : "waiting";

      const updated = await client.query(
        `UPDATE telehealth_sessions
         SET doctor_joined_at = COALESCE(doctor_joined_at, $1),
             patient_joined_at = COALESCE(patient_joined_at, $2),
             status = $3
         WHERE id = $4
         RETURNING *`,
        [
          isDoctor ? doctorJoinedAt : null,
          isPatient ? patientJoinedAt : null,
          newStatus,
          session.id,
        ]
      );

      broadcastEvent("telehealth_participant_joined", {
        appointmentId,
        role,
        status: newStatus,
      });

      return updated.rows[0];
    });
  }

  /** End video call and compute duration. */
  static async endRoom(appointmentId: string) {
    return withTransaction(async (client) => {
      const existing = await client.query(
        `SELECT * FROM telehealth_sessions WHERE appointment_id = $1`,
        [appointmentId]
      );

      if (existing.rows.length === 0) {
        throw new NotFoundError("Telehealth session not found");
      }

      const session = existing.rows[0];
      const start = session.doctor_joined_at || session.created_at;
      const endedAt = new Date();
      const durationSecs = Math.max(
        0,
        Math.floor((endedAt.getTime() - new Date(start).getTime()) / 1000)
      );

      const updated = await client.query(
        `UPDATE telehealth_sessions
         SET ended_at = $1, status = 'ended', call_duration_seconds = $2
         WHERE id = $3
         RETURNING *`,
        [endedAt, durationSecs, session.id]
      );

      broadcastEvent("telehealth_call_ended", {
        appointmentId,
        durationSeconds: durationSecs,
      });

      return updated.rows[0];
    });
  }
}
