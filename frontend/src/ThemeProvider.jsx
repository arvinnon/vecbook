import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { themes } from "./theme";

const ThemeCtx = createContext(null);

export function ThemeProvider({ children }) {
  const [mode, setMode] = useState(() => localStorage.getItem("vecbook_theme") || "light");

  useEffect(() => {
    localStorage.setItem("vecbook_theme", mode);
    // optional: set body background for pages with minimal wrappers
    document.body.style.background = themes[mode].bg;
    document.body.style.color = themes[mode].text;
  }, [mode]);

  const value = useMemo(() => {
    const t = themes[mode] || themes.light;
    return {
      mode: t.name,
      t,
      toggle: () => setMode((m) => (m === "light" ? "dark" : "light")),
      setMode,
    };
  }, [mode]);

  return <ThemeCtx.Provider value={value}>{children}</ThemeCtx.Provider>;
}

export function useTheme() {
  const ctx = useContext(ThemeCtx);
  if (!ctx) throw new Error("useTheme must be used inside ThemeProvider");
  return ctx;
}
