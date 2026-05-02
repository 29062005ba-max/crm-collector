"use client";
import { useEffect, useRef, useState } from "react";
import { apiClient } from "@/lib/api-client";
import { Phone, PhoneOff, X } from "lucide-react";

export default function ZadarmaWidget() {
  const [open, setOpen] = useState(false);
  const [phone, setPhone] = useState("");
  const [status, setStatus] = useState<"idle"|"calling"|"connected">("idle");
  const [duration, setDuration] = useState(0);
  const [ready, setReady] = useState(false);
  const [widgetKey, setWidgetKey] = useState("");
  const [widgetSip, setWidgetSip] = useState("");
  const timerRef = useRef<any>(null);
  const initialized = useRef(false);
  const hiddenRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (initialized.current) return;
    initialized.current = true;
    initZadarma();
  }, []);

  // Listen for call status from Zadarma widget
  useEffect(() => {
    const handler = (e: MessageEvent) => {
      const d = e.data;
      if (!d) return;
      const s = typeof d === "string" ? d : JSON.stringify(d);
      if (s.includes("call_start") || s.includes("answered")) {
        setStatus("connected");
        timerRef.current = setInterval(() => setDuration(x => x + 1), 1000);
      }
      if (s.includes("call_end") || s.includes("hangup") || s.includes("bye")) {
        setStatus("idle");
        clearInterval(timerRef.current);
        setDuration(0);
      }
    };
    window.addEventListener("message", handler);
    return () => window.removeEventListener("message", handler);
  }, []);

  const initZadarma = async () => {
    try {
      const { data } = await apiClient.get("/zadarma/webrtc_key");
      if (!data.key) return;
      setWidgetKey(data.key);
      setWidgetSip(data.sip);

      const loadScript = (src: string) =>
        new Promise<void>((resolve) => {
          if (document.querySelector(`script[src="${src}"]`)) { resolve(); return; }
          const s = document.createElement("script");
          s.src = src; s.onload = () => resolve(); s.onerror = () => resolve();
          document.head.appendChild(s);
        });

      await loadScript("https://my.zadarma.com/webphoneWebRTCWidget/v9/js/loader-phone-lib.js?sub_v=1");
      await loadScript("https://my.zadarma.com/webphoneWebRTCWidget/v9/js/loader-phone-fn.js?sub_v=1");
      await new Promise(r => setTimeout(r, 1000));

      // Init Zadarma widget hidden in DOM
      if (typeof (window as any).zadarmaWidgetFn === "function") {
        (window as any).zadarmaWidgetFn(
          data.key, data.sip, "rounded", "ru", false,
          { right: "-500px", bottom: "0px" }
        );
      }

      setReady(true);
    } catch (e) {
      console.error("Zadarma init:", e);
    }
  };

  const startCall = () => {
    if (!phone || !ready) return;

    // Find Zadarma widget input and click call
    const inputs = document.querySelectorAll('input');
    let zadInput: HTMLInputElement | null = null;
    inputs.forEach(inp => {
      if (inp.placeholder?.includes('phone') || inp.type === 'tel' ||
          inp.closest('[id*="webphone"]') || inp.closest('[class*="zadarma"]')) {
        if (inp !== document.querySelector('.crm-phone-input')) {
          zadInput = inp;
        }
      }
    });

    if (zadInput) {
      const nativeInput = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value');
      nativeInput?.set?.call(zadInput, phone);
      (zadInput as HTMLInputElement).dispatchEvent(new Event('input', { bubbles: true }));
      (zadInput as HTMLInputElement).dispatchEvent(new Event('change', { bubbles: true }));

      setTimeout(() => {
        // Find call button
        const btns = document.querySelectorAll('button, [role="button"]');
        btns.forEach((btn: any) => {
          if (btn.closest('[id*="webphone"]') || btn.closest('[class*="zadarma"]')) {
            if (!btn.closest('.crm-phone-panel')) {
              btn.click();
            }
          }
        });
      }, 300);
    }

    // Also try window.zadarmaCall if available
    const w = window as any;
    if (w.zadarmaWidgetCall) w.zadarmaWidgetCall(phone);
    else if (w.webphoneCall) w.webphoneCall(phone);
    else if (w.zadarmaCall) w.zadarmaCall(phone);

    setStatus("calling");
    // Optimistic timer start after 5s if no event received
    setTimeout(() => {
      setStatus(s => s === "calling" ? "connected" : s);
      if (!timerRef.current) {
        timerRef.current = setInterval(() => setDuration(x => x + 1), 1000);
      }
    }, 5000);
  };

  const endCall = () => {
    const w = window as any;
    if (w.zadarmaWidgetHangup) w.zadarmaWidgetHangup();
    else if (w.webphoneHangup) w.webphoneHangup();

    // Click hangup button in hidden widget
    document.querySelectorAll('button').forEach((btn: any) => {
      if (btn.closest('[id*="webphone"]') || btn.closest('[class*="zadarma"]')) {
        if (!btn.closest('.crm-phone-panel')) btn.click();
      }
    });

    setStatus("idle");
    clearInterval(timerRef.current);
    setDuration(0);
  };

  const fmt = (s: number) =>
    `${String(Math.floor(s/60)).padStart(2,"0")}:${String(s%60).padStart(2,"0")}`;

  const keypad = [["1","2","3"],["4","5","6"],["7","8","9"],["*","0","#"]];

  return (
    <>
      {/* Hidden Zadarma widget container */}
      <div ref={hiddenRef} style={{position:"fixed", right:"-500px", bottom:"0", zIndex:1}} />

      {/* Our button */}
      <button
        onClick={() => setOpen(o => !o)}
        className={`fixed bottom-4 right-4 z-[9999] w-14 h-14 rounded-full shadow-xl flex items-center justify-center transition-all ${
          status === "connected" ? "bg-green-500 ring-4 ring-green-300" :
          status === "calling" ? "bg-yellow-500 ring-4 ring-yellow-300 animate-pulse" :
          "bg-green-600 hover:bg-green-700"
        }`}
      >
        <Phone size={22} className="text-white" />
        {status !== "idle" && (
          <span className="absolute -top-1 -right-1 bg-red-500 text-white text-[10px] rounded-full w-5 h-5 flex items-center justify-center font-mono">
            {String(Math.floor(duration/60)).padStart(2,"0")}:{String(duration%60).padStart(2,"0")}
          </span>
        )}
      </button>

      {/* Panel */}
      {open && (
        <div className="crm-phone-panel fixed bottom-20 right-4 z-[9999] w-72 rounded-2xl bg-white shadow-2xl border border-gray-100 overflow-hidden">
          <div className={`px-4 py-3 flex items-center justify-between text-white ${
            status === "connected" ? "bg-green-500" :
            status === "calling" ? "bg-yellow-500" : "bg-gray-800"
          }`}>
            <div className="flex items-center gap-2">
              <Phone size={15} />
              <span className="font-medium text-sm">
                {status === "connected" ? `Разговор ${fmt(duration)}` :
                 status === "calling" ? "Соединение..." : "Телефон"}
              </span>
            </div>
            <button onClick={() => setOpen(false)}><X size={15} /></button>
          </div>

          <div className="p-4 space-y-3">
            <div className="flex items-center bg-gray-50 rounded-xl px-3 py-2 border border-gray-200">
              <input
                className="crm-phone-input flex-1 bg-transparent text-xl font-mono outline-none"
                type="tel"
                value={phone}
                onChange={e => setPhone(e.target.value)}
                placeholder="+7..."
              />
              {phone && <button onClick={() => setPhone(p => p.slice(0,-1))} className="text-gray-400 text-lg">⌫</button>}
            </div>

            <div className="grid grid-cols-3 gap-1.5">
              {keypad.flat().map(k => (
                <button key={k} onClick={() => setPhone(p => p + k)}
                  className="h-12 rounded-xl bg-gray-100 hover:bg-gray-200 active:bg-gray-300 text-lg font-semibold transition-colors">
                  {k}
                </button>
              ))}
            </div>

            {status !== "connected" ? (
              <button onClick={startCall} disabled={!phone || !ready}
                className="w-full h-12 rounded-xl bg-green-500 hover:bg-green-600 disabled:opacity-40 text-white font-semibold flex items-center justify-center gap-2">
                <Phone size={18} />
                {status === "calling" ? "Соединение..." : "Позвонить"}
              </button>
            ) : (
              <button onClick={endCall}
                className="w-full h-12 rounded-xl bg-red-500 hover:bg-red-600 text-white font-semibold flex items-center justify-center gap-2">
                <PhoneOff size={18} />
                Завершить {fmt(duration)}
              </button>
            )}

            <p className="text-center text-xs text-gray-400">
              {ready ? `SIP: ${widgetSip}` : "⏳ Подключение..."}
            </p>
          </div>
        </div>
      )}
    </>
  );
}
