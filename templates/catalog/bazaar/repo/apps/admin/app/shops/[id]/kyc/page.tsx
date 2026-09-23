"use client";

import { useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { AdminHeader } from "@/components/admin-header";
import {
  ShieldCheck,
  FileText,
  Building,
  Award,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  ArrowLeft,
  Stamp,
  ExternalLink,
} from "lucide-react";

export default function AdminKycApprovalPage() {
  const params = useParams();
  const shopId = (params?.id as string) || "shop-001";

  const [decision, setDecision] = useState<"verified" | "rejected" | "suspended" | null>("verified");
  const [operatorNote, setOperatorNote] = useState(
    "Verified against GI Registry of India (GI Application #39). All master artisan citations and bank IFSC records validated."
  );
  const [statusUpdated, setStatusUpdated] = useState(false);

  const kycData = {
    shopId,
    shopName: "Jaipur Blue Art Pottery",
    artisanName: "Kripal Singh Shekhawat",
    giTag: "GI Tag #39 (Jaipur Blue Pottery)",
    giCertificateNumber: "GI/IN/2006/0039",
    craftLineage: "Padma Shri Kripal Kumbh Heritage School",
    panNumber: "AAACK9281M",
    gstin: "08AAACK9281M1Z4",
    bankVerification: {
      accountHolder: "Jaipur Blue Art Pottery Atelier",
      bankName: "State Bank of India",
      ifscCode: "SBIN0004123",
      accountNumber: "•••• •••• 8291",
      pennyDropStatus: "Matched (100% confidence)",
    },
    documents: [
      {
        title: "Geographical Indication (GI) Authorized User Certificate",
        type: "PDF / Official Government Seal",
        fileSize: "2.4 MB",
        verificationDate: "Valid through 2031",
      },
      {
        title: "Development Commissioner (Handicrafts) Artisan Identity Card",
        type: "National Pehchan Card",
        fileSize: "1.1 MB",
        verificationDate: "Verified against Ministry of Textiles DB",
      },
      {
        title: "Cancelled Bank Cheque & IFSC Direct Settlement Mandate",
        type: "Financial Proof",
        fileSize: "850 KB",
        verificationDate: "Reconciled with SBI RTGS API",
      },
    ],
  };

  const handleDecisionSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setStatusUpdated(true);
    setTimeout(() => setStatusUpdated(false), 4000);
  };

  return (
    <div className="flex-1 flex flex-col">
      <AdminHeader
        title="KYC Verification & Approval"
        subtitle={`Audit Geographical Indication authentication and government credentials for ${kycData.shopName}.`}
        badge="Official Review"
      />

      <div className="p-6 space-y-6 flex-1 max-w-5xl">
        <Link
          href={`/shops/${shopId}`}
          className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-white transition"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          Back to Workshop Profile
        </Link>

        {/* Verification Status Banner */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <div className="text-base font-bold text-white flex items-center gap-2">
                {kycData.shopName}
                <span className="text-xs font-mono px-2 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/20">
                  {kycData.giTag}
                </span>
              </div>
              <p className="text-xs text-slate-400">
                Master Craftsman: {kycData.artisanName} • {kycData.craftLineage}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <span className="text-xs text-slate-400">KYC Status:</span>
            <span className="px-3 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-xs font-mono font-bold flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5" />
              AUTHENTICATED &amp; VERIFIED
            </span>
          </div>
        </div>

        {/* Submitted Documentation Inspection */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <FileText className="w-4 h-4 text-amber-400" />
            Submitted Statutory Documents &amp; GI Credentials
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {kycData.documents.map((doc, idx) => (
              <div
                key={idx}
                className="bg-slate-950 border border-slate-800 rounded-lg p-3.5 space-y-2 flex flex-col justify-between"
              >
                <div>
                  <div className="text-xs font-bold text-slate-100 mb-1">{doc.title}</div>
                  <div className="text-[11px] text-slate-400">{doc.type} ({doc.fileSize})</div>
                </div>
                <div className="pt-2 border-t border-slate-800 flex items-center justify-between text-[11px]">
                  <span className="text-emerald-400 flex items-center gap-1">
                    <CheckCircle2 className="w-3 h-3" /> Validated
                  </span>
                  <span className="text-slate-400 font-mono">Verified</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Legal & Banking Credentials */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-3">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <Award className="w-4 h-4 text-amber-400" />
              Tax &amp; Identity Credentials
            </h3>
            <div className="space-y-2 text-xs">
              <div className="flex justify-between py-1 border-b border-slate-800">
                <span className="text-slate-400">GI Certificate:</span>
                <span className="font-mono text-white">{kycData.giCertificateNumber}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-800">
                <span className="text-slate-400">PAN Number:</span>
                <span className="font-mono text-white">{kycData.panNumber}</span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-slate-400">GSTIN Registration:</span>
                <span className="font-mono text-white">{kycData.gstin}</span>
              </div>
            </div>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-3">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <Building className="w-4 h-4 text-emerald-400" />
              Banking &amp; Settlement Validation
            </h3>
            <div className="space-y-2 text-xs">
              <div className="flex justify-between py-1 border-b border-slate-800">
                <span className="text-slate-400">Account Beneficiary:</span>
                <span className="text-white">{kycData.bankVerification.accountHolder}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-800">
                <span className="text-slate-400">Bank &amp; Branch:</span>
                <span className="text-white">{kycData.bankVerification.bankName}</span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-slate-400">Automated Penny-Drop:</span>
                <span className="text-emerald-400 font-mono font-semibold">
                  {kycData.bankVerification.pennyDropStatus}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Operator Decision Console */}
        <form onSubmit={handleDecisionSubmit} className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <Stamp className="w-4 h-4 text-amber-400" />
              Administrative Verification Decision
            </h3>
            <span className="text-xs text-slate-400">Immutable Audit Record</span>
          </div>

          <div className="space-y-2 text-xs">
            <label className="block text-slate-300 font-medium">
              Operator Approval Note &amp; Compliance Notes
            </label>
            <textarea
              rows={3}
              value={operatorNote}
              onChange={(e) => setOperatorNote(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 text-white placeholder-slate-400 focus:outline-none focus:border-amber-500"
            />
          </div>

          <div className="flex flex-wrap items-center gap-3 pt-2">
            <button
              type="submit"
              onClick={() => setDecision("verified")}
              className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs transition flex items-center gap-1.5 cursor-pointer"
            >
              <CheckCircle2 className="w-4 h-4" />
              Approve &amp; Confirm GI Accreditation
            </button>

            <button
              type="submit"
              onClick={() => setDecision("suspended")}
              className="px-4 py-2 rounded-lg bg-rose-600/20 hover:bg-rose-600/30 border border-rose-500/30 text-rose-300 text-xs font-semibold transition flex items-center gap-1.5 cursor-pointer"
            >
              <XCircle className="w-4 h-4" />
              Suspend Workshop
            </button>
          </div>

          {statusUpdated && (
            <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4" />
              Operator decision confirmed and committed to audit trail with timestamp.
            </div>
          )}
        </form>
      </div>
    </div>
  );
}
