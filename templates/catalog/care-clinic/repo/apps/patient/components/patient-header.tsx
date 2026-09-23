"use client";

import Link from "next/navigation";
import NextLink from "next/link";
import { useState, useEffect } from "react";
import {
  HeartPulse,
  Calendar,
  User,
  FileText,
  FlaskConical,
  Activity,
  Users,
  Receipt,
  Search,
  Menu,
  X,
  Bell,
} from "lucide-react";

export function PatientHeader() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [user, setUser] = useState<{ full_name?: string; email?: string } | null>(null);

  useEffect(() => {
    try {
      const u = localStorage.getItem("careclinic_user");
      if (u) setUser(JSON.parse(u));
    } catch {
      // ignore
    }
  }, []);

  const navLinks = [
    { href: "/doctors", label: "Find Doctors", icon: Search },
    { href: "/appointments", label: "Appointments", icon: Calendar },
    { href: "/prescriptions", label: "Prescriptions", icon: FileText },
    { href: "/lab-reports", label: "Lab Reports", icon: FlaskConical },
    { href: "/records", label: "Health Records", icon: Activity },
    { href: "/family", label: "Family", icon: Users },
    { href: "/invoices", label: "Invoices", icon: Receipt },
  ];

  return (
    <header className="sticky top-0 z-40 bg-white/95 backdrop-blur-md border-b border-slate-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <NextLink href="/" className="flex items-center gap-2.5 text-teal-800 font-bold text-xl tracking-tight">
            <div className="w-10 h-10 rounded-xl bg-teal-600 text-white flex items-center justify-center shadow-sm">
              <HeartPulse className="w-6 h-6 text-white" />
            </div>
            <div>
              <span className="text-slate-900 font-extrabold text-lg sm:text-xl">Care</span>
              <span className="text-teal-600 font-extrabold text-lg sm:text-xl">Clinic</span>
              <span className="block text-[10px] uppercase font-semibold tracking-wider text-teal-700/80 -mt-1">
                Healthcare & Telehealth
              </span>
            </div>
          </NextLink>

          {/* Desktop Navigation */}
          <nav className="hidden lg:flex items-center gap-1 xl:gap-2">
            {navLinks.map((link) => {
              const Icon = link.icon;
              return (
                <NextLink
                  key={link.href}
                  href={link.href}
                  className="px-3 py-2 rounded-lg text-sm font-medium text-slate-600 hover:text-teal-700 hover:bg-teal-50/70 transition-colors flex items-center gap-1.5"
                >
                  <Icon className="w-4 h-4 text-slate-400 group-hover:text-teal-600" />
                  {link.label}
                </NextLink>
              );
            })}
          </nav>

          {/* Right Action Buttons */}
          <div className="hidden sm:flex items-center gap-3">
            <NextLink
              href="/appointments"
              className="p-2 rounded-full text-slate-500 hover:text-teal-600 hover:bg-slate-100 transition-colors relative"
              title="Notifications"
            >
              <Bell className="w-5 h-5" />
              <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-teal-600"></span>
            </NextLink>

            <NextLink
              href="/doctors"
              className="bg-teal-600 hover:bg-teal-700 text-white font-semibold text-sm px-4 py-2 rounded-xl transition-all shadow-sm hover:shadow flex items-center gap-1.5"
            >
              <Calendar className="w-4 h-4 text-teal-100" />
              Book Visit
            </NextLink>

            {user ? (
              <NextLink
                href="/records"
                className="flex items-center gap-2 pl-2 border-l border-slate-200"
              >
                <div className="w-8 h-8 rounded-full bg-teal-100 text-teal-800 font-bold flex items-center justify-center text-xs">
                  {user.full_name ? user.full_name.charAt(0) : "A"}
                </div>
                <div className="text-left hidden md:block">
                  <div className="text-xs font-semibold text-slate-800 leading-tight">
                    {user.full_name || "Ananya"}
                  </div>
                  <div className="text-[10px] text-teal-600 font-medium">Patient Portal</div>
                </div>
              </NextLink>
            ) : (
              <NextLink
                href="/login"
                className="border border-slate-300 hover:border-teal-500 text-slate-700 hover:text-teal-700 text-sm font-medium px-3.5 py-1.5 rounded-xl transition-colors flex items-center gap-1.5"
              >
                <User className="w-4 h-4 text-slate-400" />
                Sign In
              </NextLink>
            )}
          </div>

          {/* Mobile hamburger toggle */}
          <div className="flex lg:hidden items-center gap-2">
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 rounded-lg text-slate-600 hover:bg-slate-100"
              aria-label="Toggle Navigation Menu"
            >
              {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Menu Dropdown */}
      {mobileMenuOpen && (
        <div className="lg:hidden border-b border-slate-200 bg-white px-4 pt-2 pb-6 space-y-1">
          {navLinks.map((link) => {
            const Icon = link.icon;
            return (
              <NextLink
                key={link.href}
                href={link.href}
                onClick={() => setMobileMenuOpen(false)}
                className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-base font-medium text-slate-700 hover:bg-teal-50 hover:text-teal-700"
              >
                <Icon className="w-5 h-5 text-teal-600" />
                {link.label}
              </NextLink>
            );
          })}
          <div className="pt-4 border-t border-slate-200 flex flex-col gap-2">
            <NextLink
              href="/doctors"
              onClick={() => setMobileMenuOpen(false)}
              className="w-full text-center bg-teal-600 text-white font-medium py-2.5 rounded-xl text-sm"
            >
              Book an Appointment
            </NextLink>
            {!user && (
              <NextLink
                href="/login"
                onClick={() => setMobileMenuOpen(false)}
                className="w-full text-center border border-slate-300 text-slate-700 font-medium py-2 rounded-xl text-sm"
              >
                Patient Sign In
              </NextLink>
            )}
          </div>
        </div>
      )}
    </header>
  );
}
