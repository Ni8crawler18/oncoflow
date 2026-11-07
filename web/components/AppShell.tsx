"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import Sidebar from "./Sidebar";
import { isAuthed } from "@/lib/auth";

// Guards the authenticated app area (redirects to /login when not authed) and
// renders the full-page sidebar + content layout.
export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [ready, setReady] = useState(false);

  const isLogin = pathname === "/login";

  useEffect(() => {
    if (isLogin) {
      setReady(true);
      return;
    }
    if (!isAuthed()) {
      router.replace("/login");
    } else {
      setReady(true);
    }
  }, [pathname, isLogin, router]);

  if (isLogin) return <>{children}</>;
  if (!ready) return <div className="min-h-screen bg-canvas" />;

  return (
    <div className="flex h-screen overflow-hidden bg-white">
      <Sidebar />
      <main className="flex-1 overflow-y-auto bg-canvas">
        <div className="mx-auto max-w-[1500px] px-6 pb-12 pt-8 md:px-10">
          {children}
        </div>
      </main>
    </div>
  );
}
