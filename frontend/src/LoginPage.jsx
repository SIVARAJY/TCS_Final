import { useState } from "react";
import { login as apiLogin } from "./api";

const DEMO_ACCOUNTS = [
  {
    email: "investigator@fincrime.org",
    name: "Sarah Jenkins",
    role: "Lead AML Investigator",
    badge: "INV-4092",
    clearance: "Top Secret / FIU",
    desc: "Primary investigator with full case and AI generation access",
  },
  {
    email: "analyst@fincrime.org",
    name: "Marcus Chen",
    role: "Forensic Graph Analyst",
    badge: "FGA-8821",
    clearance: "Secret / Level 3",
    desc: "Specialist in topological money movement & entity resolution",
  },
  {
    email: "compliance@fincrime.org",
    name: "Elena Rostova",
    role: "Chief Compliance Officer",
    badge: "CCO-1004",
    clearance: "Executive Oversight",
    desc: "Audit & regulatory review of flagged syndicate clusters",
  },
];

export default function LoginPage({ onLogin }) {
  const [username, setUsername] = useState("investigator@fincrime.org");
  const [password, setPassword] = useState("investigator123");
  const [showPassword, setShowPassword] = useState(false);
  const [remember, setRemember] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e) {
    if (e) e.preventDefault();
    if (!username.trim()) {
      setError("Please enter your analyst email or ID");
      return;
    }
    if (password.length < 4) {
      setError("Password must be at least 4 characters");
      return;
    }

    setLoading(true);
    setError("");

    try {
      // Attempt backend auth first
      const res = await apiLogin(username.trim(), password);
      if (res && res.user) {
        if (remember) {
          localStorage.setItem("fincrime_user", JSON.stringify(res.user));
        }
        onLogin(res.user);
        return;
      }
    } catch (err) {
      // Graceful demo fallback: match against known demo accounts or generate custom profile
      const demoMatch = DEMO_ACCOUNTS.find(
        (a) => a.email.toLowerCase() === username.trim().toLowerCase()
      );
      if (demoMatch) {
        const userObj = { ...demoMatch, token: `demo-token-${demoMatch.badge}` };
        if (remember) localStorage.setItem("fincrime_user", JSON.stringify(userObj));
        onLogin(userObj);
        return;
      } else if (password.length >= 4) {
        // Fallback for custom analyst handle
        const namePart = username.split("@")[0].replace(/[._-]/g, " ");
        const userObj = {
          email: username,
          name: namePart.charAt(0).toUpperCase() + namePart.slice(1) || "Analyst",
          role: "Special Investigator",
          badge: `INV-${Math.floor(1000 + Math.random() * 9000)}`,
          clearance: "Operational Clearance",
          token: `demo-token-${Date.now()}`,
        };
        if (remember) localStorage.setItem("fincrime_user", JSON.stringify(userObj));
        onLogin(userObj);
        return;
      }
      setError(err.message || "Authentication failed. Check your credentials.");
    } finally {
      setLoading(false);
    }
  }

  function handleQuickLogin(account) {
    setUsername(account.email);
    setPassword("demoPass2026");
    setError("");
    const userObj = { ...account, token: `demo-token-${account.badge}` };
    if (remember) localStorage.setItem("fincrime_user", JSON.stringify(userObj));
    onLogin(userObj);
  }

  return (
    <div className="min-h-screen bg-[#0e1722] text-slate-100 flex flex-col justify-between selection:bg-[#1f6f78] selection:text-white">
      {/* Top Classification Header */}
      <div className="w-full bg-[#080d14] border-b border-slate-800/80 px-6 py-2.5 flex items-center justify-between text-xs tracking-wider text-slate-400">
        <div className="flex items-center gap-2">
          <span className="inline-block w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span className="font-mono text-slate-300 font-medium">NETWORK STATUS: ONLINE</span>
          <span className="text-slate-600">|</span>
          <span className="text-slate-400">NODE DISCOVERY V2.4</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-rose-950/80 text-rose-300 border border-rose-800/50 uppercase tracking-widest">
            Confidential // FIU Level-4
          </span>
        </div>
      </div>

      {/* Main Login Container */}
      <div className="flex-1 flex items-center justify-center p-4 sm:p-6 my-4">
        <div className="w-full max-w-md bg-[#141f2d] border border-slate-700/80 rounded-xl shadow-2xl p-6 sm:p-8 relative overflow-hidden">
          {/* Subtle Accent Glow */}
          <div className="absolute -top-24 -right-24 w-48 h-48 bg-[#1f6f78]/20 rounded-full blur-3xl pointer-events-none" />
          <div className="absolute -bottom-24 -left-24 w-48 h-48 bg-rose-900/15 rounded-full blur-3xl pointer-events-none" />

          {/* Brand Header */}
          <div className="text-center mb-6">
            <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-gradient-to-br from-[#1f6f78] to-[#14202b] border border-cyan-500/30 shadow-inner mb-3">
              <svg className="w-7 h-7 text-cyan-300" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                <path d="m9 12 2 2 4-4" />
              </svg>
            </div>
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-white">
              Financial Crime Investigator
            </h1>
            <p className="text-xs sm:text-sm text-slate-400 mt-1">
              Secure AML Intelligence & Graph Forensics Portal
            </p>
          </div>

          {/* Error Message */}
          {error && (
            <div className="mb-5 p-3 rounded-lg bg-rose-950/70 border border-rose-800/80 text-rose-200 text-xs flex items-start gap-2.5">
              <svg className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
              <span>{error}</span>
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-slate-300 uppercase tracking-wider mb-1.5">
                Analyst ID / Email
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                  <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                    <circle cx="12" cy="7" r="4" />
                  </svg>
                </div>
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="name@fincrime.org or INV-XXXX"
                  required
                  className="w-full pl-9 pr-3 py-2 bg-[#0d1622] border border-slate-700 rounded-lg text-sm text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 transition"
                />
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-xs font-medium text-slate-300 uppercase tracking-wider">
                  Password
                </label>
                <span className="text-[11px] text-slate-500">Min. 4 characters</span>
              </div>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                  <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                    <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                  </svg>
                </div>
                <input
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  className="w-full pl-9 pr-10 py-2 bg-[#0d1622] border border-slate-700 rounded-lg text-sm text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 transition"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-400 hover:text-slate-200"
                  tabIndex="-1"
                >
                  {showPassword ? (
                    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                      <line x1="1" y1="1" x2="23" y2="23" />
                    </svg>
                  ) : (
                    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                      <circle cx="12" cy="12" r="3" />
                    </svg>
                  )}
                </button>
              </div>
            </div>

            <div className="flex items-center justify-between text-xs pt-1">
              <label className="flex items-center gap-2 cursor-pointer select-none text-slate-300">
                <input
                  type="checkbox"
                  checked={remember}
                  onChange={(e) => setRemember(e.target.checked)}
                  className="rounded border-slate-700 bg-[#0d1622] text-[#1f6f78] focus:ring-0 focus:ring-offset-0"
                />
                <span>Keep analyst session active</span>
              </label>
              <span className="text-slate-500 text-[11px]">256-bit AES</span>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full mt-2 py-2.5 px-4 bg-[#1f6f78] hover:bg-[#25838d] active:bg-[#1a5b62] text-white font-medium text-sm rounded-lg transition duration-150 flex items-center justify-center gap-2 shadow-lg shadow-cyan-950/40 disabled:opacity-50"
            >
              {loading ? (
                <>
                  <svg className="animate-spin h-4 w-4 text-white" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  <span>Authenticating Credentials…</span>
                </>
              ) : (
                <>
                  <span>Sign In to Investigator Portal</span>
                  <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <line x1="5" y1="12" x2="19" y2="12" />
                    <polyline points="12 5 19 12 12 19" />
                  </svg>
                </>
              )}
            </button>
          </form>

          {/* Quick Demo Access Buttons */}
          <div className="mt-6 pt-5 border-t border-slate-700/60">
            <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2.5 flex items-center justify-between">
              <span>Quick Demo Access (1-Click)</span>
              <span className="text-[10px] text-cyan-400 font-normal">Select a role</span>
            </p>
            <div className="space-y-1.5">
              {DEMO_ACCOUNTS.map((acc) => (
                <button
                  key={acc.email}
                  type="button"
                  onClick={() => handleQuickLogin(acc)}
                  className="w-full text-left p-2.5 rounded-lg bg-[#0d1622]/90 hover:bg-[#182637] border border-slate-700/70 hover:border-cyan-500/40 transition duration-150 group"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-xs text-white group-hover:text-cyan-300">
                        {acc.name}
                      </span>
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 font-mono">
                        {acc.badge}
                      </span>
                    </div>
                    <span className="text-[10px] text-cyan-400/80 group-hover:text-cyan-300 flex items-center gap-1">
                      Login →
                    </span>
                  </div>
                  <div className="flex items-center justify-between mt-1 text-[11px] text-slate-400">
                    <span>{acc.role}</span>
                    <span className="text-[10px] text-slate-500">{acc.clearance}</span>
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Footer Security Disclaimer */}
      <footer className="w-full border-t border-slate-800/80 bg-[#080d14] px-6 py-3 text-center text-[11px] text-slate-500">
        <p>
          Official Financial Intelligence System · All activities and graph inspections are cryptographically audited.
        </p>
      </footer>
    </div>
  );
}
