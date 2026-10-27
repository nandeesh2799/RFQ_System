import React, { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { Gavel, PlusCircle, LayoutDashboard, ListFilter, UserCheck, Menu, X } from "lucide-react";
import { api, getStoredDemoUser, setStoredDemoUser } from "@/lib/api";
import type { User } from "@/types";

export const Navbar: React.FC = () => {
  const location = useLocation();
  const [users, setUsers] = useState<User[]>([]);
  const [currentUserEmail, setCurrentUserEmail] = useState(getStoredDemoUser());
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    api.getUsers().then(setUsers).catch(console.error);
    const handlePersonaChange = () => setCurrentUserEmail(getStoredDemoUser());
    window.addEventListener("persona_changed", handlePersonaChange);
    return () => window.removeEventListener("persona_changed", handlePersonaChange);
  }, []);

  // Close mobile menu on route change
  useEffect(() => {
    setMobileMenuOpen(false);
  }, [location.pathname]);

  const handleUserSelect = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const email = e.target.value;
    setCurrentUserEmail(email);
    setStoredDemoUser(email);
  };

  const navLinks = [
    { to: "/", label: "Dashboard", icon: LayoutDashboard },
    { to: "/auctions", label: "Auctions", icon: ListFilter },
    { to: "/rfqs/new", label: "Create RFQ", icon: PlusCircle },
  ];

  const activeUser = users.find((u) => u.email === currentUserEmail);

  return (
    <header className="border-b border-slate-200 bg-white sticky top-0 z-40 shadow-xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16 items-center gap-2">
          {/* Brand & Mobile Menu Toggle */}
          <div className="flex items-center space-x-2 sm:space-x-3 min-w-0 shrink">
            <button
              type="button"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-1.5 rounded-lg text-slate-500 hover:text-slate-900 hover:bg-slate-100 lg:hidden focus:outline-none"
              aria-label="Toggle navigation menu"
            >
              {mobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
            </button>
            <div className="h-9 w-9 sm:h-10 sm:w-10 rounded-lg bg-indigo-600 flex items-center justify-center text-white shadow-sm shrink-0">
              <Gavel className="h-4 w-4 sm:h-5 sm:w-5" />
            </div>
            <div className="min-w-0">
              <Link to="/" className="text-base sm:text-lg font-bold text-slate-900 tracking-tight flex items-center gap-1.5 whitespace-nowrap">
                <span>British Auction</span>
                <span className="text-xs px-1.5 py-0.5 rounded bg-indigo-50 text-indigo-700 font-semibold uppercase tracking-wider">RFQ</span>
              </Link>
              <p className="text-[11px] text-slate-500 hidden sm:block">Reverse Auction Engine</p>
            </div>
          </div>

          {/* Desktop Navigation Links */}
          <nav className="hidden lg:flex space-x-1 shrink-0">
            {navLinks.map((link) => {
              const Icon = link.icon;
              const isActive = location.pathname === link.to;
              return (
                <Link
                  key={link.to}
                  to={link.to}
                  className={`flex items-center space-x-2 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                    isActive
                      ? "bg-slate-100 text-indigo-700 font-semibold"
                      : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  <span>{link.label}</span>
                </Link>
              );
            })}
          </nav>

          {/* Demo Persona Switcher */}
          <div className="flex items-center space-x-2 bg-slate-50 border border-slate-200 rounded-lg px-2 sm:px-3 py-1 sm:py-1.5 shrink-0 max-w-[200px] sm:max-w-none">
            <UserCheck className="h-4 w-4 text-slate-500 shrink-0" />
            <div className="flex flex-col text-left min-w-0">
              <span className="text-[9px] sm:text-[10px] uppercase font-bold tracking-wider text-slate-400">Acting Persona</span>
              <select
                value={currentUserEmail}
                onChange={handleUserSelect}
                aria-label="Acting Persona Switcher"
                className="text-xs font-medium text-slate-800 bg-transparent border-0 p-0 focus:ring-0 cursor-pointer outline-none max-w-[110px] sm:max-w-[180px] md:max-w-none truncate"
              >
                {users.map((u) => (
                  <option key={u.email} value={u.email}>
                    {u.role === "BUYER" ? "👔 Buyer" : "🚚 Supplier"}: {u.company_name}
                  </option>
                ))}
              </select>
            </div>
            {activeUser && (
              <span className={`hidden sm:inline-flex text-[10px] px-2 py-0.5 rounded-full font-bold shrink-0 ${
                activeUser.role === "BUYER" ? "bg-amber-100 text-amber-800" : "bg-emerald-100 text-emerald-800"
              }`}>
                {activeUser.role}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Mobile Drawer / Dropdown */}
      {mobileMenuOpen && (
        <div className="lg:hidden border-t border-slate-200 bg-white px-4 pt-2 pb-3 space-y-1 shadow-md">
          {navLinks.map((link) => {
            const Icon = link.icon;
            const isActive = location.pathname === link.to;
            return (
              <Link
                key={link.to}
                to={link.to}
                onClick={() => setMobileMenuOpen(false)}
                className={`flex items-center space-x-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-indigo-50 text-indigo-700 font-semibold"
                    : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
                }`}
              >
                <Icon className="h-4 w-4 text-slate-500" />
                <span>{link.label}</span>
              </Link>
            );
          })}
        </div>
      )}
    </header>
  );
};
