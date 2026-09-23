"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  Video,
  Mic,
  MicOff,
  VideoOff,
  PhoneOff,
  Share2,
  FileText,
  Activity,
  MessageSquare,
  ShieldCheck,
  AlertTriangle,
  Send,
  Plus,
  Save,
  CheckCircle2,
  Clock,
  ExternalLink,
  ChevronRight,
} from "lucide-react";
import { defaultApiClient } from "@careclinic/shared";

export default function DoctorTelehealthPage() {
  const params = useParams();
  const router = useRouter();
  const appointmentId = (params?.appointmentId as string) || "apt-101";

  // Audio / Video states
  const [micMuted, setMicMuted] = useState(false);
  const [videoOff, setVideoOff] = useState(false);
  const [screenSharing, setScreenSharing] = useState(false);
  const [callDuration, setCallDuration] = useState(14 * 60 + 24); // 14m 24s

  // Side drawer tab: "soap" | "chart" | "prescription" | "chat"
  const [activeTab, setActiveTab] = useState<"soap" | "chart" | "prescription" | "chat">("soap");

  // In-call chat
  const [chatMessages, setChatMessages] = useState<{ sender: string; text: string; time: string }[]>([
    {
      sender: "System",
      text: "Encrypted WebRTC peer connection established (AES-256-GCM).",
      time: "10:02 AM",
    },
    {
      sender: "Ananya Deshmukh",
      text: "Hello Dr. Varma, I can hear and see you clearly.",
      time: "10:03 AM",
    },
  ]);
  const [newMsg, setNewMsg] = useState("");

  // In-call SOAP quick-notes
  const [soapNotes, setSoapNotes] = useState({
    subjective: "Patient reports feeling well. Occasional lightheadedness upon standing up fast in morning.",
    objective: "Home BP monitor reading reported today: 118/76 mmHg, Pulse 70 bpm.",
    assessment: "Well-controlled Essential Hypertension on Telmisartan 40mg daily.",
    plan: "Continue Telmisartan 40mg. Advise slow postural changes. Review routine electrolyte profile in 3 months.",
  });
  const [notesSaved, setNotesSaved] = useState(false);

  // Quick Prescription in-call
  const [meds, setMeds] = useState([
    { name: "Telmisartan 40mg Tablet", frequency: "1-0-0", duration: "30 days", instructions: "After breakfast" },
  ]);
  const [newMedName, setNewMedName] = useState("");

  // Timer tick
  useEffect(() => {
    const timer = setInterval(() => {
      setCallDuration((prev) => prev + 1);
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const formatTimer = (totalSeconds: number) => {
    const mins = Math.floor(totalSeconds / 60);
    const secs = totalSeconds % 60;
    return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  };

  const handleSendMessage = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newMsg.trim()) return;
    setChatMessages((prev) => [
      ...prev,
      {
        sender: "Dr. Rajesh Varma",
        text: newMsg,
        time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      },
    ]);
    setNewMsg("");
  };

  const handleSaveNotes = () => {
    setNotesSaved(true);
    setTimeout(() => setNotesSaved(false), 2500);
  };

  const handleAddMed = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newMedName.trim()) return;
    setMeds([
      ...meds,
      { name: newMedName, frequency: "1-0-1", duration: "15 days", instructions: "After meals" },
    ]);
    setNewMedName("");
  };

  const handleEndCall = () => {
    if (confirm("End consultation and proceed to final prescription verification?")) {
      router.push(`/consult/${appointmentId}/prescription`);
    }
  };

  return (
    <div className="space-y-4">
      {/* Top Telehealth Bar */}
      <div className="bg-slate-900 text-white px-5 py-3 rounded-2xl flex flex-wrap items-center justify-between gap-4 border border-slate-800 shadow-lg">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-teal-600 text-white flex items-center justify-center font-bold">
            <Video className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-sm">Telehealth Station</span>
              <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                Connected
              </span>
            </div>
            <span className="text-xs text-slate-400 block">
              Patient: Ananya Deshmukh (32 yrs • F) • Token #TEL-042
            </span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 bg-slate-800 px-3 py-1.5 rounded-lg border border-slate-700 text-xs">
            <Clock className="w-3.5 h-3.5 text-emerald-400" />
            <span className="font-mono font-bold text-emerald-400">
              {formatTimer(callDuration)}
            </span>
          </div>

          <div className="hidden sm:flex items-center gap-1.5 text-xs text-slate-400">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            <span>HIPAA Encrypted</span>
          </div>
        </div>
      </div>

      {/* Main Console Split */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Left Column: Video Room View (7 cols) */}
        <div className="lg:col-span-7 flex flex-col space-y-3">
          {/* Patient Main Video Screen */}
          <div className="relative aspect-video bg-slate-950 rounded-2xl overflow-hidden border border-slate-800 shadow-md flex items-center justify-center">
            {/* Simulated Live Video Graphic */}
            <div className="absolute inset-0 bg-linear-to-b from-slate-900/60 via-slate-950 to-slate-900 flex flex-col items-center justify-center">
              <div className="relative">
                <div className="w-24 h-24 rounded-full bg-teal-800/80 border-4 border-teal-500/40 text-teal-100 font-bold text-3xl flex items-center justify-center shadow-2xl">
                  AD
                </div>
                <div className="absolute -bottom-1 -right-1 w-6 h-6 rounded-full bg-emerald-500 border-2 border-slate-950 flex items-center justify-center">
                  <span className="w-2 h-2 rounded-full bg-white animate-ping"></span>
                </div>
              </div>
              <span className="font-bold text-white text-base mt-3">
                Ananya Deshmukh
              </span>
              <span className="text-xs text-teal-400 font-mono">
                1080p HD • 42ms • Packet Loss: 0.0%
              </span>
            </div>

            {/* Top Left Patient Status Overlay */}
            <div className="absolute top-4 left-4 flex items-center gap-2">
              <span className="px-2.5 py-1 rounded-md bg-slate-900/80 backdrop-blur-xs text-[11px] font-semibold text-slate-200 border border-white/10">
                Remote Stream
              </span>
            </div>

            {/* Self-Camera PIP in Bottom Right */}
            <div className="absolute bottom-4 right-4 w-36 h-24 bg-slate-800 rounded-xl overflow-hidden border-2 border-emerald-500/80 shadow-2xl flex flex-col items-center justify-center z-10">
              {videoOff ? (
                <div className="text-center">
                  <VideoOff className="w-5 h-5 text-red-400 mx-auto" />
                  <span className="text-[10px] text-slate-400 block mt-1">Camera Off</span>
                </div>
              ) : (
                <div className="w-full h-full bg-linear-to-br from-emerald-950 to-slate-900 flex flex-col items-center justify-center">
                  <div className="w-8 h-8 rounded-full bg-emerald-700 text-white font-bold text-xs flex items-center justify-center">
                    RV
                  </div>
                  <span className="text-[10px] text-emerald-300 font-bold mt-1">
                    Dr. Rajesh Varma
                  </span>
                </div>
              )}
            </div>
          </div>

          {/* Call Controls Bar */}
          <div className="bg-white p-3 rounded-xl border border-slate-200 shadow-xs flex items-center justify-between">
            <div className="flex items-center gap-2">
              <button
                onClick={() => setMicMuted(!micMuted)}
                className={`p-3 rounded-xl transition-colors ${
                  micMuted
                    ? "bg-red-50 text-red-600 border border-red-200"
                    : "bg-slate-100 hover:bg-slate-200 text-slate-700"
                }`}
                title={micMuted ? "Unmute Microphone" : "Mute Microphone"}
              >
                {micMuted ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
              </button>

              <button
                onClick={() => setVideoOff(!videoOff)}
                className={`p-3 rounded-xl transition-colors ${
                  videoOff
                    ? "bg-red-50 text-red-600 border border-red-200"
                    : "bg-slate-100 hover:bg-slate-200 text-slate-700"
                }`}
                title={videoOff ? "Enable Camera" : "Disable Camera"}
              >
                {videoOff ? <VideoOff className="w-5 h-5" /> : <Video className="w-5 h-5" />}
              </button>

              <button
                onClick={() => setScreenSharing(!screenSharing)}
                className={`p-3 rounded-xl transition-colors ${
                  screenSharing
                    ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                    : "bg-slate-100 hover:bg-slate-200 text-slate-700"
                }`}
                title="Share Screen"
              >
                <Share2 className="w-5 h-5" />
              </button>
            </div>

            <button
              onClick={handleEndCall}
              className="px-5 py-2.5 bg-red-600 hover:bg-red-700 text-white font-bold text-xs rounded-xl inline-flex items-center gap-2 shadow-xs transition-colors"
            >
              <PhoneOff className="w-4 h-4" />
              <span>Complete Consultation</span>
            </button>
          </div>
        </div>

        {/* Right Column: Concurrent Clinical Workstation Drawer (5 cols) */}
        <div className="lg:col-span-5 bg-white rounded-2xl border border-slate-200 shadow-xs flex flex-col overflow-hidden min-h-[520px]">
          {/* Tabs Header */}
          <div className="p-2 border-b border-slate-200 bg-slate-50 grid grid-cols-4 gap-1">
            <button
              onClick={() => setActiveTab("soap")}
              className={`py-2 text-xs font-bold rounded-lg transition-colors flex items-center justify-center gap-1.5 ${
                activeTab === "soap"
                  ? "bg-white text-slate-900 shadow-xs border border-slate-200"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              <FileText className="w-3.5 h-3.5 text-emerald-600" />
              <span>SOAP</span>
            </button>

            <button
              onClick={() => setActiveTab("chart")}
              className={`py-2 text-xs font-bold rounded-lg transition-colors flex items-center justify-center gap-1.5 ${
                activeTab === "chart"
                  ? "bg-white text-slate-900 shadow-xs border border-slate-200"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              <Activity className="w-3.5 h-3.5 text-blue-600" />
              <span>Chart</span>
            </button>

            <button
              onClick={() => setActiveTab("prescription")}
              className={`py-2 text-xs font-bold rounded-lg transition-colors flex items-center justify-center gap-1.5 ${
                activeTab === "prescription"
                  ? "bg-white text-slate-900 shadow-xs border border-slate-200"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              <Plus className="w-3.5 h-3.5 text-teal-600" />
              <span>Rx ({meds.length})</span>
            </button>

            <button
              onClick={() => setActiveTab("chat")}
              className={`py-2 text-xs font-bold rounded-lg transition-colors flex items-center justify-center gap-1.5 ${
                activeTab === "chat"
                  ? "bg-white text-slate-900 shadow-xs border border-slate-200"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              <MessageSquare className="w-3.5 h-3.5 text-indigo-600" />
              <span>Chat</span>
            </button>
          </div>

          {/* Drawer Body Content */}
          <div className="flex-1 p-4 overflow-y-auto">
            {/* Tab 1: SOAP */}
            {activeTab === "soap" && (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
                    In-Call SOAP Note
                  </span>
                  <button
                    onClick={handleSaveNotes}
                    className="text-xs text-emerald-700 hover:text-emerald-800 font-bold inline-flex items-center gap-1"
                  >
                    <Save className="w-3.5 h-3.5" />
                    <span>{notesSaved ? "Saved" : "Save Note"}</span>
                  </button>
                </div>

                {notesSaved && (
                  <div className="p-2 rounded-lg bg-emerald-50 text-emerald-800 text-[11px] font-semibold flex items-center gap-1.5">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                    <span>Clinical note auto-saved to encounter draft.</span>
                  </div>
                )}

                <div>
                  <label className="text-[11px] font-bold text-slate-700 block mb-1">
                    Subjective (Symptoms)
                  </label>
                  <textarea
                    rows={2}
                    value={soapNotes.subjective}
                    onChange={(e) => setSoapNotes({ ...soapNotes, subjective: e.target.value })}
                    className="w-full text-xs p-2 border border-slate-300 rounded-lg text-slate-900"
                  />
                </div>

                <div>
                  <label className="text-[11px] font-bold text-slate-700 block mb-1">
                    Objective (Vitals & Findings)
                  </label>
                  <textarea
                    rows={2}
                    value={soapNotes.objective}
                    onChange={(e) => setSoapNotes({ ...soapNotes, objective: e.target.value })}
                    className="w-full text-xs p-2 border border-slate-300 rounded-lg text-slate-900"
                  />
                </div>

                <div>
                  <label className="text-[11px] font-bold text-slate-700 block mb-1">
                    Assessment (Clinical Impression / ICD-10)
                  </label>
                  <textarea
                    rows={2}
                    value={soapNotes.assessment}
                    onChange={(e) => setSoapNotes({ ...soapNotes, assessment: e.target.value })}
                    className="w-full text-xs p-2 border border-slate-300 rounded-lg text-slate-900 font-medium"
                  />
                </div>

                <div>
                  <label className="text-[11px] font-bold text-slate-700 block mb-1">
                    Plan & Directives
                  </label>
                  <textarea
                    rows={2}
                    value={soapNotes.plan}
                    onChange={(e) => setSoapNotes({ ...soapNotes, plan: e.target.value })}
                    className="w-full text-xs p-2 border border-slate-300 rounded-lg text-slate-900"
                  />
                </div>
              </div>
            )}

            {/* Tab 2: Patient Chart Snapshot */}
            {activeTab === "chart" && (
              <div className="space-y-4">
                <div className="p-3 bg-red-50 border border-red-200 rounded-xl">
                  <div className="flex items-center gap-1.5 text-xs font-bold text-red-800 mb-1">
                    <AlertTriangle className="w-3.5 h-3.5" />
                    <span>Known Drug Allergies</span>
                  </div>
                  <span className="text-xs text-red-700 font-semibold block">
                    Penicillin (Moderate Exanthema / Rash)
                  </span>
                </div>

                <div className="space-y-2">
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-400 block">
                    Vitals Baseline
                  </span>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-200">
                      <span className="text-slate-400 block text-[10px]">Blood Pressure</span>
                      <span className="font-bold text-slate-900 text-sm">118/76 mmHg</span>
                      <span className="text-[10px] text-emerald-600 font-semibold">Normal</span>
                    </div>
                    <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-200">
                      <span className="text-slate-400 block text-[10px]">Heart Rate</span>
                      <span className="font-bold text-slate-900 text-sm">70 bpm</span>
                      <span className="text-[10px] text-slate-500">Regular sinus</span>
                    </div>
                  </div>
                </div>

                <div className="space-y-2">
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-400 block">
                    Chronic Conditions
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    <span className="px-2.5 py-1 bg-slate-100 rounded-md text-xs font-medium text-slate-700">
                      Stage 1 Essential Hypertension (2024)
                    </span>
                  </div>
                </div>

                <div className="pt-2">
                  <Link
                    href={`/patients/pat-1`}
                    target="_blank"
                    className="w-full py-2 border border-slate-200 hover:bg-slate-50 rounded-lg text-xs font-bold text-slate-700 inline-flex items-center justify-center gap-1.5 transition-colors"
                  >
                    <span>Open Full Longitudinal Chart</span>
                    <ExternalLink className="w-3.5 h-3.5 text-slate-400" />
                  </Link>
                </div>
              </div>
            )}

            {/* Tab 3: Quick Prescription builder */}
            {activeTab === "prescription" && (
              <div className="space-y-3">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-400 block">
                  Prescribed Medications
                </span>

                <div className="space-y-2">
                  {meds.map((m, idx) => (
                    <div
                      key={idx}
                      className="p-3 bg-slate-50 rounded-xl border border-slate-200 text-xs space-y-1"
                    >
                      <div className="flex items-center justify-between font-bold text-slate-900">
                        <span>{m.name}</span>
                        <span className="font-mono text-emerald-700">{m.frequency}</span>
                      </div>
                      <div className="flex items-center justify-between text-slate-500 text-[11px]">
                        <span>{m.instructions}</span>
                        <span>{m.duration}</span>
                      </div>
                    </div>
                  ))}
                </div>

                <form onSubmit={handleAddMed} className="pt-2 border-t border-slate-100 space-y-2">
                  <input
                    type="text"
                    placeholder="Add medication (e.g. Amlodipine 5mg)"
                    value={newMedName}
                    onChange={(e) => setNewMedName(e.target.value)}
                    className="w-full text-xs p-2 border border-slate-300 rounded-lg text-slate-900"
                  />
                  <button
                    type="submit"
                    className="w-full py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-bold"
                  >
                    + Add to In-Call Rx
                  </button>
                </form>
              </div>
            )}

            {/* Tab 4: In-call Chat */}
            {activeTab === "chat" && (
              <div className="flex flex-col h-full space-y-3">
                <div className="flex-1 space-y-2 overflow-y-auto max-h-[300px]">
                  {chatMessages.map((msg, i) => (
                    <div
                      key={i}
                      className={`p-2.5 rounded-xl text-xs space-y-0.5 ${
                        msg.sender === "Dr. Rajesh Varma"
                          ? "bg-emerald-50 text-emerald-950 ml-6 border border-emerald-100"
                          : msg.sender === "System"
                          ? "bg-slate-100 text-slate-600 text-center text-[10px]"
                          : "bg-slate-100 text-slate-900 mr-6"
                      }`}
                    >
                      {msg.sender !== "System" && (
                        <div className="flex items-center justify-between text-[10px] text-slate-500 font-semibold">
                          <span>{msg.sender}</span>
                          <span>{msg.time}</span>
                        </div>
                      )}
                      <p>{msg.text}</p>
                    </div>
                  ))}
                </div>

                <form onSubmit={handleSendMessage} className="flex gap-2 pt-2 border-t border-slate-100">
                  <input
                    type="text"
                    placeholder="Send message to patient..."
                    value={newMsg}
                    onChange={(e) => setNewMsg(e.target.value)}
                    className="flex-1 text-xs px-3 py-2 border border-slate-300 rounded-lg text-slate-900"
                  />
                  <button
                    type="submit"
                    className="p-2 bg-slate-900 text-white rounded-lg hover:bg-slate-800"
                  >
                    <Send className="w-4 h-4" />
                  </button>
                </form>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
