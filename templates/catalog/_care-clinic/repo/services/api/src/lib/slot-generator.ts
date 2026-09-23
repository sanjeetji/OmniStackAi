/** Slot generator computing 20-minute consultation windows from availability rules. */

export interface TimeSlot {
  startTime: string; // "HH:MM:SS"
  endTime: string;   // "HH:MM:SS"
  isAvailable: boolean;
}

export interface DoctorShift {
  startTime: string; // "HH:MM:SS"
  endTime: string;   // "HH:MM:SS"
  slotDurationMins: number;
}

function timeStringToMinutes(time: string): number {
  const [h, m] = time.split(":").map((v) => parseInt(v, 10));
  return h * 60 + m;
}

function minutesToTimeString(minutes: number): string {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  const hStr = h.toString().padStart(2, "0");
  const mStr = m.toString().padStart(2, "0");
  return `${hStr}:${mStr}:00`;
}

export function generateSlotsForShift(
  shift: DoctorShift,
  bookedStartTimes: Set<string>
): TimeSlot[] {
  const startMins = timeStringToMinutes(shift.startTime);
  const endMins = timeStringToMinutes(shift.endTime);
  const duration = shift.slotDurationMins || 20;

  const slots: TimeSlot[] = [];

  for (let current = startMins; current + duration <= endMins; current += duration) {
    const slotStart = minutesToTimeString(current);
    const slotEnd = minutesToTimeString(current + duration);

    slots.push({
      startTime: slotStart,
      endTime: slotEnd,
      isAvailable: !bookedStartTimes.has(slotStart),
    });
  }

  return slots;
}
