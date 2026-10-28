import React from "react";
import { Calendar, Sparkles } from "lucide-react";

export interface DateShortcut {
  date: string;
  label: string;
  isSevere?: boolean;
}

export const DEFAULT_SHORTCUTS: DateShortcut[] = [
  { date: "2024-11-18", label: "Nov 18 (Peak: 589.7)", isSevere: true },
  { date: "2024-11-13", label: "Nov 13 (Severe: 409.3)", isSevere: true },
  { date: "2024-11-04", label: "Nov 04 (Smog: 230.7)", isSevere: false },
  { date: "2024-10-15", label: "Oct 15 (Harvest: 98.4)", isSevere: false }
];

interface CalendarDateSelectorProps {
  value: string;
  onChange: (date: string) => void;
  minDate?: string;
  maxDate?: string;
  label?: string;
  helperText?: string;
  shortcuts?: DateShortcut[];
  disabled?: boolean;
}

export default function CalendarDateSelector({
  value,
  onChange,
  minDate = "2018-01-01",
  maxDate = "2025-06-02",
  label = "Select Date",
  helperText,
  shortcuts = DEFAULT_SHORTCUTS,
  disabled = false
}: CalendarDateSelectorProps) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "0.4rem" }}>
      <div style={{ display: "flex", alignItems: "center", gap: "0.6rem", flexWrap: "wrap" }}>
        {/* Calendar Picker Box */}
        <div
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "0.5rem",
            background: "rgba(15, 23, 42, 0.8)",
            border: "1px solid rgba(6, 182, 212, 0.4)",
            borderRadius: "8px",
            padding: "0.35rem 0.65rem",
            boxShadow: "0 2px 8px rgba(0,0,0,0.2)"
          }}
        >
          <Calendar size={16} color="var(--accent-cyan)" />
          <span style={{ fontSize: "0.8rem", color: "var(--text-secondary)", fontWeight: 500 }}>
            {label}:
          </span>
          <input
            type="date"
            value={value}
            min={minDate}
            max={maxDate}
            disabled={disabled}
            onChange={(e) => {
              if (e.target.value) {
                onChange(e.target.value);
              }
            }}
            style={{
              background: "transparent",
              border: "none",
              color: "#f8fafc",
              fontSize: "0.85rem",
              fontWeight: 600,
              fontFamily: "inherit",
              outline: "none",
              cursor: "pointer",
              colorScheme: "dark"
            }}
          />
        </div>

        {/* Quick demonstration shortcuts */}
        <div style={{ display: "flex", alignItems: "center", gap: "0.35rem", flexWrap: "wrap" }}>
          <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", display: "flex", alignItems: "center", gap: "2px" }}>
            <Sparkles size={12} color="var(--accent-amber)" /> Shortcuts:
          </span>
          {shortcuts.map((sc) => {
            const isSelected = value === sc.date;
            return (
              <button
                key={sc.date}
                type="button"
                onClick={() => onChange(sc.date)}
                disabled={disabled}
                style={{
                  background: isSelected ? "rgba(6, 182, 212, 0.25)" : "rgba(255, 255, 255, 0.05)",
                  border: isSelected ? "1px solid var(--accent-cyan)" : "1px solid rgba(255, 255, 255, 0.1)",
                  color: isSelected ? "var(--accent-cyan)" : "var(--text-secondary)",
                  borderRadius: "5px",
                  padding: "0.2rem 0.5rem",
                  fontSize: "0.74rem",
                  fontWeight: isSelected ? 600 : 400,
                  cursor: "pointer",
                  transition: "all 0.15s ease"
                }}
                title={`Quick select ${sc.date}`}
              >
                {sc.label}
              </button>
            );
          })}
        </div>
      </div>

      {helperText && (
        <div style={{ fontSize: "0.74rem", color: "var(--text-muted)", paddingLeft: "2px" }}>
          {helperText}
        </div>
      )}
    </div>
  );
}
