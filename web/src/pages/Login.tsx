import React, { useState, useEffect, useRef } from "react";
import { BookOpen, Mail, ArrowRight, ArrowLeft, ShieldCheck, Loader2, AlertCircle, CheckCircle, Zap } from "lucide-react";
import { motion, AnimatePresence } from "motion/react";
import { sendVerificationCode, verifyCode } from "@/src/lib/api";

const STORAGE_KEY = "nice_invest_session";

interface LoginProps {
  onBack: () => void;
  onLoginSuccess: (email: string) => void;
}

function saveGuestSession() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify({
    session_token: "__guest__",
    email: "guest@niceinvest.dev",
  }));
}

export default function Login({ onBack, onLoginSuccess }: LoginProps) {
  // Step: "email" | "code"
  const [step, setStep] = useState<"email" | "code">("email");
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [sending, setSending] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [error, setError] = useState("");
  const [countdown, setCountdown] = useState(0);
  const [devCode, setDevCode] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Countdown timer for resend
  useEffect(() => {
    if (countdown <= 0) return;
    const timer = setTimeout(() => setCountdown(countdown - 1), 1000);
    return () => clearTimeout(timer);
  }, [countdown]);

  // Auto-focus input on step change
  useEffect(() => {
    inputRef.current?.focus();
  }, [step]);

  const handleSendCode = async () => {
    const trimmed = email.trim().toLowerCase();
    if (!trimmed || !trimmed.includes("@")) {
      setError("请输入有效的邮箱地址");
      return;
    }
    setError("");
    setSending(true);
    try {
      const result = await sendVerificationCode(trimmed);
      setDevCode(result.dev_code || null);
      setStep("code");
      setCountdown(60);
    } catch (e: any) {
      setError(e.message || "发送失败，请稍后重试");
    } finally {
      setSending(false);
    }
  };

  const handleVerify = async () => {
    const trimmed = code.trim();
    if (trimmed.length !== 6 || !/^\d{6}$/.test(trimmed)) {
      setError("请输入6位数字验证码");
      return;
    }
    setError("");
    setVerifying(true);
    try {
      const result = await verifyCode(email.trim().toLowerCase(), trimmed);
      // Store session
      localStorage.setItem(STORAGE_KEY, JSON.stringify({
        session_token: result.session_token,
        email: result.email,
      }));
      onLoginSuccess(result.email);
    } catch (e: any) {
      setError(e.message || "验证失败，请检查验证码是否正确");
    } finally {
      setVerifying(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      if (step === "email") handleSendCode();
      else handleVerify();
    }
  };

  return (
    <div className="flex flex-col items-center justify-center h-screen w-full bg-[#fffcf2] font-sans relative overflow-hidden">
      {/* 装饰光晕 */}
      <div className="absolute top-[-120px] left-[-120px] w-[400px] h-[400px] bg-[#ccc5b9]/10 rounded-full blur-[150px] pointer-events-none" />
      <div className="absolute bottom-[-120px] right-[-120px] w-[400px] h-[400px] bg-[#403d39]/5 rounded-full blur-[150px] pointer-events-none" />

      {/* Back button */}
      <button
        onClick={onBack}
        className="absolute top-8 left-8 flex items-center gap-2 text-[14px] text-[#403d39]/60 hover:text-[#252422] transition-colors z-10"
      >
        <ArrowLeft className="w-4 h-4" />
        返回首页
      </button>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="relative z-10 w-full max-w-[420px] mx-auto px-6"
      >
        {/* Brand */}
        <div className="text-center mb-10">
          <div className="flex items-center justify-center gap-2.5 mb-3">
            <BookOpen className="w-6 h-6 text-[#403d39]" />
            <span className="text-[26px] font-serif font-bold italic tracking-wide text-[#252422]">
              Nice Invest
            </span>
          </div>
          <p className="text-[14px] text-[#403d39]/50 font-serif">
            邮箱验证登录
          </p>
        </div>

        {/* 跳过登录 — 游客模式 */}
        <button
          onClick={() => { saveGuestSession(); onLoginSuccess("guest@niceinvest.dev"); }}
          className="w-full max-w-[420px] mx-auto mb-6 h-[46px] bg-transparent border border-[#ccc5b9]/60 text-[#403d39] rounded-lg text-[14px] font-medium hover:bg-[#fffcf2] hover:border-[#403d39] transition-colors flex items-center justify-center gap-2"
        >
          <Zap className="w-4 h-4" />
          跳过登录，直接体验
        </button>

        {/* 分隔线 */}
        <div className="w-full max-w-[420px] mx-auto mb-6 flex items-center gap-4">
          <div className="flex-1 h-px bg-[#ccc5b9]/40" />
          <span className="text-[12px] text-[#ccc5b9] font-serif">或</span>
          <div className="flex-1 h-px bg-[#ccc5b9]/40" />
        </div>

        {/* Card */}
        <div className="bg-white rounded-2xl border border-[#ccc5b9]/40 shadow-[0_4px_32px_rgba(37,36,34,0.06)] p-8">
          <AnimatePresence mode="wait">
            {step === "email" ? (
              <motion.div
                key="email"
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 10 }}
                transition={{ duration: 0.2 }}
              >
                <div className="flex items-center gap-3 mb-6">
                  <div className="w-10 h-10 bg-[#fffcf2] border border-[#ccc5b9]/40 rounded-xl flex items-center justify-center">
                    <Mail className="w-5 h-5 text-[#403d39]" />
                  </div>
                  <div>
                    <h3 className="text-[16px] font-bold text-[#252422]">输入邮箱</h3>
                    <p className="text-[12px] text-[#403d39]/50">我们将发送6位验证码到您的邮箱</p>
                  </div>
                </div>

                <input
                  ref={inputRef}
                  type="email"
                  placeholder="your@email.com"
                  value={email}
                  onChange={(e) => { setEmail(e.target.value); setError(""); }}
                  onKeyDown={handleKeyDown}
                  className="w-full h-[46px] px-4 bg-[#fffcf2] border border-[#ccc5b9] rounded-lg text-[15px] text-[#252422] placeholder-[#ccc5b9] focus:outline-none focus:ring-1 focus:ring-[#403d39] focus:border-[#403d39] transition-all mb-4"
                />

                {error && (
                  <div className="flex items-center gap-2 mb-4 text-[13px] text-red-500">
                    <AlertCircle className="w-4 h-4 shrink-0" />
                    {error}
                  </div>
                )}

                <button
                  onClick={handleSendCode}
                  disabled={sending}
                  className="w-full h-[46px] bg-[#252422] text-white rounded-lg text-[14px] font-medium hover:bg-[#403d39] transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
                >
                  {sending ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <ArrowRight className="w-4 h-4" />
                  )}
                  发送验证码
                </button>
              </motion.div>
            ) : (
              <motion.div
                key="code"
                initial={{ opacity: 0, x: 10 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -10 }}
                transition={{ duration: 0.2 }}
              >
                <div className="flex items-center gap-3 mb-6">
                  <div className="w-10 h-10 bg-[#fffcf2] border border-[#ccc5b9]/40 rounded-xl flex items-center justify-center">
                    <ShieldCheck className="w-5 h-5 text-[#403d39]" />
                  </div>
                  <div>
                    <h3 className="text-[16px] font-bold text-[#252422]">输入验证码</h3>
                    <p className="text-[12px] text-[#403d39]/50">
                      已发送至 <span className="text-[#403d39] font-medium">{email}</span>
                    </p>
                  </div>
                </div>

                <input
                  ref={inputRef}
                  type="text"
                  inputMode="numeric"
                  maxLength={6}
                  placeholder="000000"
                  value={code}
                  onChange={(e) => { setCode(e.target.value.replace(/\D/g, "").slice(0, 6)); setError(""); }}
                  onKeyDown={handleKeyDown}
                  className="w-full h-[56px] px-4 bg-[#fffcf2] border border-[#ccc5b9] rounded-lg text-[28px] text-[#252422] placeholder-[#ccc5b9] tracking-[10px] text-center font-mono focus:outline-none focus:ring-1 focus:ring-[#403d39] focus:border-[#403d39] transition-all mb-4"
                />

                {/* Dev code fallback */}
                {devCode && (
                  <div className="mb-3 p-2 bg-[#fffcf2] border border-[#ccc5b9]/30 rounded-lg text-center">
                    <p className="text-[11px] text-[#403d39]/40">开发模式 — 验证码：</p>
                    <p className="text-[16px] font-mono font-bold text-[#252422] tracking-[4px]">{devCode}</p>
                  </div>
                )}

                {error && (
                  <div className="flex items-center gap-2 mb-4 text-[13px] text-red-500">
                    <AlertCircle className="w-4 h-4 shrink-0" />
                    {error}
                  </div>
                )}

                <button
                  onClick={handleVerify}
                  disabled={verifying || code.length !== 6}
                  className="w-full h-[46px] bg-[#252422] text-white rounded-lg text-[14px] font-medium hover:bg-[#403d39] transition-colors flex items-center justify-center gap-2 disabled:opacity-50 mb-3"
                >
                  {verifying ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <CheckCircle className="w-4 h-4" />
                  )}
                  验证并登录
                </button>

                <div className="flex items-center justify-between">
                  <button
                    onClick={() => { setStep("email"); setError(""); setDevCode(null); }}
                    className="text-[13px] text-[#403d39]/60 hover:text-[#252422] transition-colors"
                  >
                    更换邮箱
                  </button>
                  <button
                    onClick={handleSendCode}
                    disabled={countdown > 0 || sending}
                    className="text-[13px] text-[#403d39]/60 hover:text-[#252422] transition-colors disabled:text-[#ccc5b9]"
                  >
                    {countdown > 0 ? `${countdown}秒后重发` : "重新发送"}
                  </button>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        <p className="text-center text-[12px] text-[#403d39]/30 mt-6 font-serif">
          登录即表示同意 Nice Invest 的服务条款
        </p>
      </motion.div>
    </div>
  );
}
