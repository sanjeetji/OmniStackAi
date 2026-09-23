/**
 * Universal typed API Client for CareClinic.
 */

import type {
  User,
  Clinic,
  DoctorProfile,
  DoctorShift,
  PatientProfile,
  FamilyMember,
  Appointment,
  AvailableSlot,
  MedicalHistory,
  VitalsRecord,
  Prescription,
  LabOrder,
  LabOrderItem,
  LabTest,
  Invoice,
  TelehealthSession,
  PatientReview,
  AuthResponse,
  AdminDashboard,
  AdminAppointmentRow,
  AdminAppointmentDetail,
  AdminDoctorRow,
  AdminInvoiceRow,
  AdminInvoiceDetail,
  AdminLabOrderRow,
  AdminLabOrderDetail,
  ChartAccessLogRow,
  ClinicReports,
  ClinicSettings,
  DoctorRoster,
  QueueDisplayEntry,
  QueueEntry,
  RefundRow,
  RoomRow,
  ScheduleOverride,
} from "./types";

export interface ApiClientOptions {
  baseUrl?: string;
  token?: string;
}

export class CareClinicApiClient {
  private baseUrl: string;
  private token: string | null = null;
  private role: string = "patient";

  constructor(options: ApiClientOptions = {}) {
    this.baseUrl =
      options.baseUrl ||
      (typeof process !== "undefined" && process.env?.NEXT_PUBLIC_API_URL) ||
      (typeof window !== "undefined" && window.location.origin.includes("3000")
        ? "http://127.0.0.1:4000"
        : "") ||
      "http://127.0.0.1:4000";

    if (options.token) {
      this.token = options.token;
    } else if (typeof window !== "undefined") {
      // Browser fallback to stored session
      this.token =
        window.localStorage.getItem("careclinic_token") ||
        window.sessionStorage.getItem("careclinic_token") ||
        null;
    }
  }

  public setToken(token: string | null, role: string = "patient"): void {
    this.token = token;
    this.role = role;
    if (typeof window !== "undefined") {
      if (token) {
        window.localStorage.setItem("careclinic_token", token);
        window.localStorage.setItem(`careclinic_${role}_token`, token);
      } else {
        window.localStorage.removeItem("careclinic_token");
        window.localStorage.removeItem(`careclinic_${role}_token`);
      }
    }
  }

  public getToken(): string | null {
    if (!this.token && typeof window !== "undefined") {
      this.token =
        window.localStorage.getItem("careclinic_token") ||
        window.localStorage.getItem(`careclinic_${this.role}_token`) ||
        null;
    }
    return this.token;
  }

  public setSession(token: string, user: Partial<User>): void {
    this.setToken(token, user.role || "patient");
    if (typeof window !== "undefined") {
      window.localStorage.setItem("careclinic_user", JSON.stringify(user));
    }
  }

  public clearSession(): void {
    this.setToken(null, this.role);
    if (typeof window !== "undefined") {
      window.localStorage.removeItem("careclinic_user");
    }
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const headers = new Headers(options.headers || {});

    headers.set("Content-Type", "application/json");

    const token = this.getToken();
    if (token) {
      headers.set("Authorization", `Bearer ${token}`);
    }

    const res = await fetch(url, {
      ...options,
      headers,
    });

    if (!res.ok) {
      let errMessage = `HTTP ${res.status}: ${res.statusText}`;
      try {
        const errorJson = await res.json();
        errMessage = errorJson.error || errorJson.message || errMessage;
      } catch {
        // use default error message
      }
      throw new Error(errMessage);
    }

    return res.json() as Promise<T>;
  }

  // --- Public & Auth ---
  public async health(): Promise<{ status: string; service: string; version: string }> {
    return this.request<{ status: string; service: string; version: string }>("/health");
  }

  /**
   * `role` is the kind of account the app expects: "patient", "doctor" or "admin" (which also
   * admits a receptionist). The API answers 403 when the account is of another kind, so a patient
   * cannot sign in to the clinic console.
   */
  public async login(email: string, password: string, role?: string): Promise<AuthResponse> {
    const res = await this.request<AuthResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password, role }),
    });
    this.setToken(res.token, res.user.role);
    if (typeof window !== "undefined") {
      window.localStorage.setItem("careclinic_user", JSON.stringify(res.user));
    }
    return res;
  }

  public async register(data: {
    email: string;
    password: string;
    fullName: string;
    phone?: string;
    bloodGroup?: string;
    gender?: string;
    dob?: string;
  }): Promise<AuthResponse> {
    const res = await this.request<AuthResponse>("/auth/register", {
      method: "POST",
      body: JSON.stringify(data),
    });
    this.setToken(res.token, "patient");
    if (typeof window !== "undefined") {
      window.localStorage.setItem("careclinic_user", JSON.stringify(res.user));
    }
    return res;
  }

  public async getClinics(): Promise<{ clinics: Clinic[] }> {
    return this.request<{ clinics: Clinic[] }>("/api/public/clinics");
  }

  public async getSpecialties(): Promise<{ specialties: { specialty: string; doctor_count: number }[] }> {
    return this.request<{ specialties: { specialty: string; doctor_count: number }[] }>("/api/public/specialties");
  }

  public async getDoctors(params: {
    q?: string;
    specialty?: string;
    clinicId?: string;
  } = {}): Promise<{ doctors: DoctorProfile[] }> {
    const query = new URLSearchParams();
    if (params.q) query.set("q", params.q);
    if (params.specialty) query.set("specialty", params.specialty);
    if (params.clinicId) query.set("clinicId", params.clinicId);
    const qs = query.toString();
    return this.request<{ doctors: DoctorProfile[] }>(`/api/public/doctors${qs ? `?${qs}` : ""}`);
  }

  public async getDoctor(id: string): Promise<{
    doctor: DoctorProfile;
    availability: DoctorShift[];
    reviews: PatientReview[];
  }> {
    return this.request<{
      doctor: DoctorProfile;
      availability: DoctorShift[];
      reviews: PatientReview[];
    }>(`/api/public/doctors/${id}`);
  }

  public async getLabTests(): Promise<{ tests: LabTest[] }> {
    return this.request<{ tests: LabTest[] }>("/api/public/lab-tests");
  }

  // --- Patient Portal ---
  public async getPatientMe(): Promise<{ patient: User & PatientProfile; familyMembers: FamilyMember[] }> {
    return this.request<{ patient: User & PatientProfile; familyMembers: FamilyMember[] }>("/api/patient/me");
  }

  public async updatePatientMe(data: Partial<User & PatientProfile>): Promise<{ success: boolean }> {
    return this.request<{ success: boolean }>("/api/patient/me", {
      method: "PUT",
      body: JSON.stringify(data),
    });
  }

  public async getDoctorSlots(
    doctorId: string,
    date: string
  ): Promise<{ doctorId: string; date: string; slots: AvailableSlot[] }> {
    return this.request<{ doctorId: string; date: string; slots: AvailableSlot[] }>(
      `/api/patient/doctors/${doctorId}/slots?date=${encodeURIComponent(date)}`
    );
  }

  public async bookAppointment(data: {
    doctorId: string;
    clinicId?: string;
    forFamilyMemberId?: string;
    appointmentType: "in_clinic" | "video";
    scheduledDate: string;
    startTime: string;
    notes?: string;
    paymentMethod?: string;
  }): Promise<{ appointment: Appointment }> {
    return this.request<{ appointment: Appointment }>("/api/patient/book", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  public async getAppointments(
    filter?: "upcoming" | "past"
  ): Promise<{ appointments: Appointment[] }> {
    const qs = filter ? `?filter=${filter}` : "";
    return this.request<{ appointments: Appointment[] }>(`/api/patient/appointments${qs}`);
  }

  public async getAppointment(id: string): Promise<{ appointment: Appointment }> {
    return this.request<{ appointment: Appointment }>(`/api/patient/appointments/${id}`);
  }

  public async cancelAppointment(
    id: string,
    reason?: string
  ): Promise<{
    appointment: Appointment;
    cancellation: {
      refundPercent: number;
      refundAmountInr: number;
      deductionInr: number;
      policyNote: string;
    };
  }> {
    return this.request<{
      appointment: Appointment;
      cancellation: {
        refundPercent: number;
        refundAmountInr: number;
        deductionInr: number;
        policyNote: string;
      };
    }>(`/api/patient/appointments/${id}/cancel`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    });
  }

  public async getPrescriptions(): Promise<{ prescriptions: Prescription[] }> {
    return this.request<{ prescriptions: Prescription[] }>("/api/patient/prescriptions");
  }

  public async getPrescription(id: string): Promise<{ prescription: Prescription; items: any[] }> {
    return this.request<{ prescription: Prescription; items: any[] }>(`/api/patient/prescriptions/${id}`);
  }

  public async getLabReports(): Promise<{ orders: LabOrder[]; items: LabOrderItem[] }> {
    return this.request<{ orders: LabOrder[]; items: LabOrderItem[] }>("/api/patient/labs");
  }

  public async getMedicalRecords(): Promise<{ medicalHistory: MedicalHistory; vitals: VitalsRecord[] }> {
    return this.request<{ medicalHistory: MedicalHistory; vitals: VitalsRecord[] }>("/api/patient/records");
  }

  public async logVitals(data: {
    bpSystolic?: number;
    bpDiastolic?: number;
    heartRate?: number;
    temperatureF?: number;
    spo2Percent?: number;
    bloodGlucoseMgDl?: number;
    notes?: string;
  }): Promise<{ vitals: VitalsRecord }> {
    return this.request<{ vitals: VitalsRecord }>("/api/patient/records/vitals", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  public async getFamilyMembers(): Promise<{ familyMembers: FamilyMember[] }> {
    return this.request<{ familyMembers: FamilyMember[] }>("/api/patient/family");
  }

  public async addFamilyMember(data: {
    fullName: string;
    relationship: string;
    dob?: string;
    gender?: string;
    bloodGroup?: string;
  }): Promise<{ member: FamilyMember }> {
    return this.request<{ member: FamilyMember }>("/api/patient/family", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  public async getInvoices(): Promise<{ invoices: Invoice[] }> {
    return this.request<{ invoices: Invoice[] }>("/api/patient/invoices");
  }

  public async payInvoice(
    id: string,
    paymentMethod: string = "upi",
    transactionRef?: string
  ): Promise<{ invoice: Invoice }> {
    return this.request<{ invoice: Invoice }>(`/api/patient/invoices/${id}/pay`, {
      method: "POST",
      body: JSON.stringify({ paymentMethod, transactionRef }),
    });
  }

  public async getTelehealthSession(appointmentId: string): Promise<{ session: TelehealthSession }> {
    return this.request<{ session: TelehealthSession }>(`/api/patient/telehealth/${appointmentId}`);
  }

  public async joinTelehealthSession(appointmentId: string): Promise<{ session: TelehealthSession }> {
    return this.request<{ session: TelehealthSession }>(`/api/patient/telehealth/${appointmentId}/join`, {
      method: "POST",
    });
  }

  public async submitReview(data: {
    doctorId: string;
    appointmentId?: string;
    rating: number;
    feedback: string;
    isAnonymous?: boolean;
  }): Promise<{ review: PatientReview }> {
    return this.request<{ review: PatientReview }>("/api/patient/reviews", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  // --- Doctor Workstation ---
  public async getDoctorDashboard(): Promise<{
    metrics: {
      today_total: number;
      pending_count: number;
      waiting_count: number;
      in_consult_count: number;
      completed_count: number;
      video_count: number;
      today_earnings: number;
    };
    activeConsultation?: any;
  }> {
    return this.request("/api/doctor/dashboard");
  }

  public async getDoctorQueue(date?: string): Promise<{ queue: any[] }> {
    const qs = date ? `?date=${encodeURIComponent(date)}` : "";
    return this.request(`/api/doctor/queue${qs}`);
  }

  public async getDoctorPatients(q?: string): Promise<{ patients: any[] }> {
    const qs = q ? `?q=${encodeURIComponent(q)}` : "";
    return this.request(`/api/doctor/patients${qs}`);
  }

  public async getPatientChart(patientId: string): Promise<any> {
    return this.request(`/api/doctor/patients/${patientId}/chart`);
  }

  public async startConsultation(appointmentId: string): Promise<{ consultation: any }> {
    return this.request(`/api/doctor/consult/${appointmentId}/start`, {
      method: "POST",
    });
  }

  public async saveSoapNotes(appointmentId: string, data: any): Promise<{ consultation: any }> {
    return this.request(`/api/doctor/consult/${appointmentId}/soap`, {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  public async issuePrescription(
    appointmentId: string,
    data: { diagnosisSummary: string; items: any[] }
  ): Promise<{ prescription: any }> {
    return this.request(`/api/doctor/consult/${appointmentId}/prescribe`, {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  public async orderLabs(
    appointmentId: string,
    testCodes: string[]
  ): Promise<{ order: any; tests: any[] }> {
    return this.request(`/api/doctor/consult/${appointmentId}/labs`, {
      method: "POST",
      body: JSON.stringify({ testCodes }),
    });
  }

  public async completeConsultation(appointmentId: string): Promise<any> {
    return this.request(`/api/doctor/consult/${appointmentId}/complete`, {
      method: "POST",
    });
  }

  public async getDoctorSchedule(): Promise<{ shifts: any[]; overrides: any[] }> {
    return this.request("/api/doctor/schedule");
  }

  public async updateDoctorSchedule(shifts: any[]): Promise<{ success: boolean; count: number }> {
    return this.request("/api/doctor/schedule", {
      method: "PUT",
      body: JSON.stringify({ shifts }),
    });
  }

  public async getDoctorReviews(): Promise<{ reviews: any[] }> {
    return this.request("/api/doctor/reviews");
  }

  public async getDoctorTelehealth(appointmentId: string): Promise<{ session: any }> {
    return this.request(`/api/doctor/telehealth/${appointmentId}`);
  }

  public async joinDoctorTelehealth(appointmentId: string): Promise<{ session: any }> {
    return this.request(`/api/doctor/telehealth/${appointmentId}/join`, {
      method: "POST",
    });
  }

  public async endDoctorTelehealth(appointmentId: string): Promise<{ session: any }> {
    return this.request(`/api/doctor/telehealth/${appointmentId}/end`, {
      method: "POST",
    });
  }

  // --- Clinic Operations Console ---
  public async getAdminDashboard(): Promise<AdminDashboard> {
    return this.request<AdminDashboard>("/api/admin/dashboard");
  }

  public async getFrontDesk(): Promise<{ queue: QueueEntry[] }> {
    return this.request<{ queue: QueueEntry[] }>("/api/admin/front-desk");
  }

  public async getQueueDisplay(): Promise<{ activeQueue: QueueDisplayEntry[] }> {
    return this.request<{ activeQueue: QueueDisplayEntry[] }>("/api/admin/queue-display");
  }

  public async checkInPatient(appointmentId: string): Promise<{ appointment: Appointment }> {
    return this.request<{ appointment: Appointment }>("/api/admin/check-in", {
      method: "POST",
      body: JSON.stringify({ appointmentId }),
    });
  }

  public async callToken(appointmentId: string): Promise<{ appointment: Appointment }> {
    return this.request<{ appointment: Appointment }>(`/api/admin/queue/${appointmentId}/call`, {
      method: "POST",
    });
  }

  public async bookWalkIn(input: {
    patientName: string;
    phone?: string;
    doctorId: string;
    notes?: string;
    paymentMethod?: string;
  }): Promise<{ patient: User; appointment: Appointment }> {
    return this.request<{ patient: User; appointment: Appointment }>("/api/admin/walk-in", {
      method: "POST",
      body: JSON.stringify(input),
    });
  }

  public async getAdminAppointments(
    params: { q?: string; status?: string; doctorId?: string; date?: string } = {}
  ): Promise<{ appointments: AdminAppointmentRow[] }> {
    const search = new URLSearchParams();
    for (const [key, value] of Object.entries(params)) {
      if (value) search.set(key, value);
    }
    const qs = search.toString();
    return this.request<{ appointments: AdminAppointmentRow[] }>(
      `/api/admin/appointments${qs ? `?${qs}` : ""}`
    );
  }

  public async getAdminAppointment(id: string): Promise<{ appointment: AdminAppointmentDetail }> {
    return this.request<{ appointment: AdminAppointmentDetail }>(`/api/admin/appointments/${id}`);
  }

  public async cancelAppointmentAtDesk(
    id: string,
    reason: string
  ): Promise<{ appointment: Appointment; refund: { refundAmount: number; refundPercentage: number; reasonExplanation: string } }> {
    return this.request(`/api/admin/appointments/${id}/cancel`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    });
  }

  public async getAdminDoctors(): Promise<{ doctors: AdminDoctorRow[] }> {
    return this.request<{ doctors: AdminDoctorRow[] }>("/api/admin/doctors");
  }

  public async assignRoom(doctorId: string, roomNumber: string): Promise<{ success: boolean; roomNumber: string }> {
    return this.request<{ success: boolean; roomNumber: string }>(`/api/admin/doctors/${doctorId}/room`, {
      method: "PUT",
      body: JSON.stringify({ roomNumber }),
    });
  }

  public async getRooms(): Promise<{ rooms: RoomRow[] }> {
    return this.request<{ rooms: RoomRow[] }>("/api/admin/rooms");
  }

  public async getDoctorRoster(doctorId: string): Promise<DoctorRoster> {
    return this.request<DoctorRoster>(`/api/admin/doctors/${doctorId}/schedule`);
  }

  public async addScheduleOverride(
    doctorId: string,
    input: { date: string; isLeave: boolean; customStartTime?: string; customEndTime?: string; reason?: string }
  ): Promise<{ override: ScheduleOverride }> {
    return this.request<{ override: ScheduleOverride }>(`/api/admin/doctors/${doctorId}/schedule-override`, {
      method: "POST",
      body: JSON.stringify(input),
    });
  }

  public async getAdminInvoices(
    params: { status?: string; q?: string } = {}
  ): Promise<{ invoices: AdminInvoiceRow[] }> {
    const search = new URLSearchParams();
    if (params.status) search.set("status", params.status);
    if (params.q) search.set("q", params.q);
    const qs = search.toString();
    return this.request<{ invoices: AdminInvoiceRow[] }>(`/api/admin/billing${qs ? `?${qs}` : ""}`);
  }

  public async getAdminInvoice(id: string): Promise<AdminInvoiceDetail> {
    return this.request<AdminInvoiceDetail>(`/api/admin/invoices/${id}`);
  }

  public async collectPayment(
    invoiceId: string,
    paymentMethod: "card" | "upi" | "cash" | "insurance" | "netbanking"
  ): Promise<{ invoice: Invoice }> {
    return this.request<{ invoice: Invoice }>(`/api/admin/invoices/${invoiceId}/collect`, {
      method: "POST",
      body: JSON.stringify({ paymentMethod }),
    });
  }

  public async getRefunds(): Promise<{ refunds: RefundRow[] }> {
    return this.request<{ refunds: RefundRow[] }>("/api/admin/refunds");
  }

  public async getAdminLabOrders(status?: string): Promise<{ orders: AdminLabOrderRow[] }> {
    return this.request<{ orders: AdminLabOrderRow[] }>(
      `/api/admin/labs${status ? `?status=${encodeURIComponent(status)}` : ""}`
    );
  }

  public async getAdminLabOrder(id: string): Promise<AdminLabOrderDetail> {
    return this.request<AdminLabOrderDetail>(`/api/admin/labs/${id}`);
  }

  public async setLabOrderStatus(id: string, status: string): Promise<{ order: LabOrder }> {
    return this.request<{ order: LabOrder }>(`/api/admin/labs/${id}/status`, {
      method: "PUT",
      body: JSON.stringify({ status }),
    });
  }

  public async uploadLabResults(
    id: string,
    items: { itemId: string; resultValue: string; flag?: string; technicianNotes?: string }[]
  ): Promise<{ order: LabOrder }> {
    return this.request<{ order: LabOrder }>(`/api/admin/labs/${id}/results`, {
      method: "POST",
      body: JSON.stringify({ items }),
    });
  }

  public async getAuditLogs(q?: string): Promise<{ auditLogs: ChartAccessLogRow[] }> {
    return this.request<{ auditLogs: ChartAccessLogRow[] }>(
      `/api/admin/audit-logs${q ? `?q=${encodeURIComponent(q)}` : ""}`
    );
  }

  public async getClinicSettings(): Promise<ClinicSettings> {
    return this.request<ClinicSettings>("/api/admin/settings");
  }

  public async getClinicReports(days = 30): Promise<ClinicReports> {
    return this.request<ClinicReports>(`/api/admin/reports?days=${days}`);
  }
}

export const defaultApiClient = new CareClinicApiClient();
