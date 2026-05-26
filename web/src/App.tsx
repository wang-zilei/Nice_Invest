import React, { useState } from "react";
import Landing from "@/src/pages/Landing";
import Login from "@/src/pages/Login";
import Dashboard from "@/src/pages/Dashboard";
import Report from "@/src/pages/Report";
import { checkSession, clearSession } from "@/src/lib/api";
import type { ReportData, AgentTask } from "@/src/lib/api";

type Page = "landing" | "login" | "dashboard" | "report";

export interface AnalysisResult {
  analysisId: string;
  stockCode: string;
  stockName: string;
  verdict: string;
  summaryText: string;
  reportData: ReportData | null;
  agents: AgentTask[];
}

export default function App() {
  const [currentPage, setCurrentPage] = useState<Page>("landing");
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);

  const handleEnterApp = async () => {
    const raw = localStorage.getItem("nice_invest_session");
    if (!raw) {
      setCurrentPage("login");
      return;
    }

    try {
      const data = JSON.parse(raw);
      if (data.session_token) {
        const res = await checkSession(data.session_token);
        if (res.valid) {
          setCurrentPage("dashboard");
          return;
        }
      }

      clearSession();
    } catch {
      clearSession();
    }

    setCurrentPage("login");
  };

  const handleLoginSuccess = (_email: string) => {
    setCurrentPage("dashboard");
  };

  const handleLogout = () => {
    clearSession();
    setCurrentPage("landing");
  };

  const handleViewReport = (result: AnalysisResult) => {
    setAnalysisResult(result);
    setCurrentPage("report");
  };

  const handleBackToDashboard = () => {
    setCurrentPage("dashboard");
  };

  const handleBackToLandingFromLogin = () => {
    setCurrentPage("landing");
  };

  return (
    <div className="w-full h-screen">
      {currentPage === "landing" && <Landing onEnter={handleEnterApp} />}
      {currentPage === "login" && (
        <Login onBack={handleBackToLandingFromLogin} onLoginSuccess={handleLoginSuccess} />
      )}
      {currentPage === "dashboard" && (
        <Dashboard onViewReport={handleViewReport} onLogout={handleLogout} />
      )}
      {currentPage === "report" && (
        <Report
          result={analysisResult}
          onBack={handleBackToDashboard}
        />
      )}
    </div>
  );
}
