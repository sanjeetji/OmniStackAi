"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  Mic,
  MicOff,
  Video as VideoIcon,
  VideoOff,
  PhoneOff,
  MessageSquare,
  Activity,
  Send,
  ShieldCheck,
  Clock,
  Sparkles,
  Maximize2,
} from "lucide-react";
import { defaultApiClient } from "@careclinic/shared";

export default function TelehealthRoomPage() {
  const params = useParams();
  const router = useRouter();
  const appointmentId = (params?.appointmentId as string) || "apt-telehealth";

  const [micOn, setMicOn] = useState(true);
  const [videoOn, setVideoOn] = useState(true);
  const [callActive, setCallActive] = useState(true);
  const [activeTab, setActiveTab] = useState<"chat" | "vitals">("chat");
  const [messages, setMessages] = useState<
    { sender: "doctor" | "patient"; text: string; time: string }[]
  >([
    {
      sender: "doctor",
      text: "Hello Ananya, good morning. I can hear and see you clearly.",
      time: "10:21 AM",
    },
    {
      sender: "patient",
      text: "Good morning Dr. Rajesh. I have been having occasional chest tightness after climbing stairs.",
      time: "10:22 AM",
    },
    {
      sender: "doctor",
      text: "Understood. Let me review your vitals and ECG history while we talk.",
      time: "10:22 AM",
    },
  ]);
  const [chatInput, setChatInput] = useState("");
  const [secondsElapsed, setSecondsElapsed] = useState(245);

  useEffect(() => {
    // Notify server of patient joining room
    defaultApiClient.joinTelehealthSession(appointmentId).catch(() => {});

    const timer = setInterval(() => {
      setSecondsElapsed((prev) => prev + 1);
    }, 1000);

    return () => clearInterval(timer);
  }, [appointmentId]);

  const handleSendMessage = (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatInput.trim()) return;

    const newMsg = {
      sender: "patient" as const,
      text: chatInput.trim(),
      time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };
    setMessages((prev) => [...prev, newMsg]);
    setChatInput("");

    // Simulate doctor acknowledgement
    setTimeout(() => {
      setMessages((prev) => [
        ...prev,
        {
          sender: "doctor",
          text: "I am adding an updated prescription for your medication now. You will be able to download the signed Rx immediately after this call.",
          time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        },
      ]);
    }, 2500);
  };

  const formatTimer = (totalSecs: number) => {
    const mins = Math.floor(totalSecs / 60);
    const secs = totalSecs % 60;
    return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  };

  const handleEndCall = () => {
    setCallActive(false);
    setTimeout(() => {
      router.push(`/appointments/${appointmentId}`);
    }, 1200);
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      {/* Top Banner */}
      <div className="flex items-center justify-between bg-slate-900 text-white px-5 py-3 rounded-2xl mb-4 border border-slate-800">
        <div className="flex items-center gap-2 text-xs">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse"></span>
          <span className="font-bold">Encrypted Telehealth Consultation</span>
          <span className="text-slate-400 hidden sm:inline">• Room #CC-{appointmentId.slice(-6)}</span>
        </div>

        <div className="flex items-center gap-3 text-xs">
          <div className="flex items-center gap-1.5 bg-slate-800 px-3 py-1 rounded-xl text-teal-300 font-mono font-bold">
            <Clock className="w-3.5 h-3.5 text-teal-400" />
            <span>{formatTimer(secondsElapsed)}</span>
          </div>

          <div className="hidden sm:flex items-center gap-1 text-emerald-400 bg-emerald-950/70 px-2.5 py-1 rounded-xl text-[11px] font-semibold">
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>256-Bit WebRTC</span>
          </div>
        </div>
      </div>

      {/* Main Video & Consultation Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Video Feeds & Controls (2 Cols) */}
        <div className="lg:col-span-2 space-y-4">
          <div className="relative aspect-video bg-slate-950 rounded-3xl overflow-hidden border border-slate-800 shadow-2xl flex items-center justify-center">
            {/* Main Remote Video (Doctor) */}
            <div className="absolute inset-0 flex flex-col items-center justify-center p-8 text-center bg-gradient-to-b from-slate-900 to-slate-950">
              <div className="relative mb-4">
                <div className="w-28 h-28 rounded-full bg-teal-800/60 border-2 border-teal-500 flex items-center justify-center text-white text-3xl font-extrabold shadow-lg">
                  RV
                </div>
                <span className="absolute bottom-0 right-1 w-5 h-5 rounded-full bg-emerald-500 border-2 border-slate-950"></span>
              </div>
              <h2 className="text-xl font-bold text-white">Dr. Rajesh Varma, MD</h2>
              <p className="text-xs text-teal-300 mt-1">Senior Cardiologist • CareClinic Indiranagar</p>
              <div className="mt-3 flex items-center gap-1.5 bg-teal-950/80 border border-teal-800/80 px-3 py-1 rounded-full text-[11px] text-teal-300 font-medium">
                <Activity className="w-3.5 h-3.5 text-teal-400 animate-pulse" />
                <span>Audio Connected • HD 1080p Stream</span>
              </div>
            </div>

            {/* Local Patient PIP Camera */}
            <div className="absolute bottom-4 right-4 w-36 sm:w-48 aspect-video bg-slate-800/90 rounded-2xl border border-slate-700 shadow-xl overflow-hidden flex items-center justify-center">
              {videoOn ? (
                <div className="w-full h-full bg-teal-950 flex flex-col items-center justify-center p-2 text-center">
                  <div className="w-8 h-8 rounded-full bg-teal-700 text-white font-bold flex items-center justify-center text-xs mb-1">
                    AD
                  </div>
                  <span className="text-[10px] text-teal-200 font-medium">Ananya (You)</span>
                </div>
              ) : (
                <div className="text-[10px] text-slate-400 flex flex-col items-center gap-1">
                  <VideoOff className="w-4 h-4 text-slate-500" />
                  <span>Camera Paused</span>
                </div>
              )}
            </div>
          </div>

          {/* Bottom Floating Call Controls */}
          <div className="bg-white p-3.5 rounded-3xl border border-slate-200 shadow-md flex items-center justify-center gap-3">
            <button
              onClick={() => setMicOn(!micOn)}
              className={`p-3.5 rounded-2xl transition-colors cursor-pointer ${
                micOn
                  ? "bg-slate-100 hover:bg-slate-200 text-slate-700"
                  : "bg-rose-100 text-rose-700 hover:bg-rose-200"
              }`}
              title={micOn ? "Mute Microphone" : "Unmute Microphone"}
            >
              {micOn ? <Mic className="w-5 h-5" /> : <MicOff className="w-5 h-5" />}
            </button>

            <button
              onClick={() => setVideoOn(!videoOn)}
              className={`p-3.5 rounded-2xl transition-colors cursor-pointer ${
                videoOn
                  ? "bg-slate-100 hover:bg-slate-200 text-slate-700"
                  : "bg-rose-100 text-rose-700 hover:bg-rose-200"
              }`}
              title={videoOn ? "Turn Camera Off" : "Turn Camera On"}
            >
              {videoOn ? <VideoIcon className="w-5 h-5" /> : <VideoOff className="w-5 h-5" />}
            </button>

            <button
              onClick={handleEndCall}
              className="bg-rose-600 hover:bg-rose-700 text-white px-6 py-3 rounded-2xl font-bold text-xs sm:text-sm transition-all shadow-md flex items-center gap-2 cursor-pointer"
            >
              <PhoneOff className="w-4 h-4" />
              <span>Leave Consult</span>
            </button>
          </div>
        </div>

        {/* Right Column: In-Call Panel (Chat & Vitals) */}
        <div className="bg-white rounded-3xl border border-slate-200 shadow-xs flex flex-col h-[520px] overflow-hidden">
          {/* Tabs */}
          <div className="flex border-b border-slate-100 text-xs font-bold text-slate-600">
            <button
              onClick={() => setActiveTab("chat")}
              className={`flex-1 py-3.5 text-center flex items-center justify-center gap-1.5 transition-colors cursor-pointer ${
                activeTab === "chat"
                  ? "text-teal-700 border-b-2 border-teal-600 bg-teal-50/30"
                  : "hover:bg-slate-50"
              }`}
            >
              <MessageSquare className="w-3.5 h-3.5" />
              <span>Live In-Call Chat</span>
            </button>
            <button
              onClick={() => setActiveTab("vitals")}
              className={`flex-1 py-3.5 text-center flex items-center justify-center gap-1.5 transition-colors cursor-pointer ${
                activeTab === "vitals"
                  ? "text-teal-700 border-b-2 border-teal-600 bg-teal-50/30"
                  : "hover:bg-slate-50"
              }`}
            >
              <Activity className="w-3.5 h-3.5" />
              <span>Shared Vitals</span>
            </button>
          </div>

          {/* Tab Content */}
          {activeTab === "chat" ? (
            <div className="flex-1 flex flex-col justify-between p-4 overflow-hidden">
              <div className="space-y-3 overflow-y-auto flex-1 pr-1">
                {messages.map((m, idx) => (
                  <div
                    key={idx}
                    className={`flex flex-col ${
                      m.sender === "patient" ? "items-end" : "items-start"
                    }`}
                  >
                    <div
                      className={`max-w-[85%] rounded-2xl p-3 text-xs leading-relaxed ${
                        m.sender === "patient"
                          ? "bg-teal-600 text-white rounded-br-xs"
                          : "bg-slate-100 text-slate-800 rounded-bl-xs"
                      }`}
                    >
                      <p>{m.text}</p>
                    </div>
                    <span className="text-[10px] text-slate-400 mt-1 px-1">{m.time}</span>
                  </div>
                ))}
              </div>

              <form onSubmit={handleSendMessage} className="mt-3 flex gap-2">
                <input
                  type="text"
                  placeholder="Type a message to the physician..."
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  className="flex-1 text-xs px-3.5 py-2.5 border border-slate-200 rounded-xl focus:border-teal-500 focus:outline-hidden"
                />
                <button
                  type="submit"
                  className="bg-teal-600 hover:bg-teal-700 text-white p-2.5 rounded-xl cursor-pointer"
                >
                  <Send className="w-4 h-4" />
                </button>
              </form>
            </div>
          ) : (
            <div className="p-5 space-y-4 overflow-y-auto flex-1 text-xs">
              <div className="bg-teal-50/60 p-3.5 rounded-2xl border border-teal-100">
                <span className="text-[10px] uppercase font-bold text-teal-800 block">
                  Today's Recorded Biometrics
                </span>
                <p className="text-slate-500 text-[11px] mt-0.5">
                  Logged for Dr. Rajesh Varma's clinical evaluation.
                </p>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
                  <span className="text-slate-400 block text-[10px]">Blood Pressure</span>
                  <span className="text-base font-bold text-slate-900">120 / 80</span>
                  <span className="text-[10px] text-emerald-600 font-semibold block">Optimal</span>
                </div>

                <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
                  <span className="text-slate-400 block text-[10px]">Heart Rate</span>
                  <span className="text-base font-bold text-slate-900">72 BPM</span>
                  <span className="text-[10px] text-slate-500 block">Normal Sinus</span>
                </div>

                <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
                  <span className="text-slate-400 block text-[10px]">SpO2 Saturation</span>
                  <span className="text-base font-bold text-slate-900">98%</span>
                  <span className="text-[10px] text-emerald-600 font-semibold block">Room Air</span>
                </div>

                <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
                  <span className="text-slate-400 block text-[10px]">Fasting Sugar</span>
                  <span className="text-base font-bold text-slate-900">94 mg/dL</span>
                  <span className="text-[10px] text-emerald-600 font-semibold block">Controlled</span>
                </div>
              </div>

              <div className="border-t border-slate-100 pt-3">
                <span className="font-bold text-slate-800 block mb-1">Known Allergies</span>
                <span className="inline-block bg-rose-50 text-rose-700 px-2 py-0.5 rounded text-[11px] font-semibold border border-rose-100">
                  Penicillin (Moderate Rash)
                </span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
