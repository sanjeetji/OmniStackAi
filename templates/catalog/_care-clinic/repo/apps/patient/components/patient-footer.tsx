import Link from "next/link";
import { HeartPulse, PhoneCall, ShieldCheck, Clock, MapPin } from "lucide-react";

export function PatientFooter() {
  return (
    <footer className="bg-slate-900 text-slate-400 text-sm mt-auto border-t border-slate-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-8">
          {/* Column 1: Hospital Info */}
          <div className="space-y-4">
            <div className="flex items-center gap-2 text-white font-bold text-lg">
              <div className="w-8 h-8 rounded-lg bg-teal-600 text-white flex items-center justify-center">
                <HeartPulse className="w-5 h-5 text-white" />
              </div>
              <span>CareClinic</span>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              NABH-accredited integrated healthcare facility offering multi-specialty clinical consultations, 
              preventive health diagnostics, and real-time telemedicine video visits.
            </p>
            <div className="flex items-center gap-2 text-xs text-emerald-400 bg-emerald-950/60 border border-emerald-800/80 px-2.5 py-1.5 rounded-lg w-fit">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              <span>NABH Certified & HIPAA Compliant</span>
            </div>
          </div>

          {/* Column 2: Emergency & Helplines */}
          <div className="space-y-3">
            <h4 className="text-white font-semibold text-sm">Emergency & Helplines</h4>
            <div className="space-y-2 text-xs">
              <div className="flex items-start gap-2">
                <PhoneCall className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                <div>
                  <div className="text-rose-300 font-semibold">24x7 Emergency Ambulance</div>
                  <div className="text-slate-300">108 / +91 80 4912 3000</div>
                </div>
              </div>
              <div className="flex items-start gap-2 pt-1">
                <Clock className="w-4 h-4 text-teal-400 shrink-0 mt-0.5" />
                <div>
                  <div className="text-slate-300 font-medium">OPD Consultation Hours</div>
                  <div className="text-slate-400">Mon - Sat: 8:00 AM - 8:00 PM</div>
                  <div className="text-slate-400">Sun: 9:00 AM - 2:00 PM</div>
                </div>
              </div>
            </div>
          </div>

          {/* Column 3: Quick Links */}
          <div className="space-y-3">
            <h4 className="text-white font-semibold text-sm">Patient Services</h4>
            <ul className="space-y-1.5 text-xs">
              <li>
                <Link href="/doctors" className="hover:text-teal-300 transition-colors">
                  Find Specialists & Book
                </Link>
              </li>
              <li>
                <Link href="/appointments" className="hover:text-teal-300 transition-colors">
                  Appointment Queue Status
                </Link>
              </li>
              <li>
                <Link href="/prescriptions" className="hover:text-teal-300 transition-colors">
                  Digital Prescriptions (Rx)
                </Link>
              </li>
              <li>
                <Link href="/lab-reports" className="hover:text-teal-300 transition-colors">
                  Diagnostic Lab Reports
                </Link>
              </li>
              <li>
                <Link href="/records" className="hover:text-teal-300 transition-colors">
                  Vitals & Longitudinal Records
                </Link>
              </li>
              <li>
                <Link href="/family" className="hover:text-teal-300 transition-colors">
                  Family Health Profiles
                </Link>
              </li>
            </ul>
          </div>

          {/* Column 4: Location */}
          <div className="space-y-3">
            <h4 className="text-white font-semibold text-sm">Indiranagar Center</h4>
            <div className="flex items-start gap-2 text-xs text-slate-400">
              <MapPin className="w-4 h-4 text-teal-400 shrink-0 mt-0.5" />
              <div>
                <p className="text-slate-300 font-medium">CareClinic Indiranagar</p>
                <p>#482, 100 Feet Road, 12th Main</p>
                <p>HAL 2nd Stage, Indiranagar</p>
                <p>Bengaluru, Karnataka 560038</p>
              </div>
            </div>
          </div>
        </div>

        <div className="border-t border-slate-800 pt-6 flex flex-col sm:flex-row items-center justify-between text-xs text-slate-500 gap-3">
          <p>© 2026 CareClinic Health Systems Pvt Ltd. All rights reserved.</p>
          <div className="flex gap-4">
            <span className="hover:text-slate-400 cursor-pointer">Patient Privacy Policy</span>
            <span>•</span>
            <span className="hover:text-slate-400 cursor-pointer">HIPAA Compliance</span>
            <span>•</span>
            <span className="hover:text-slate-400 cursor-pointer">Cancellation & Refunds</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
