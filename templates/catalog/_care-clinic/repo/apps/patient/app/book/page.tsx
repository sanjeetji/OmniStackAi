"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function BookIndexRedirect() {
  const router = useRouter();

  useEffect(() => {
    // Default to doctor directory or first physician
    router.replace("/doctors");
  }, [router]);

  return (
    <div className="max-w-md mx-auto p-12 text-center text-xs text-slate-400">
      Redirecting to Doctor Directory...
    </div>
  );
}
