import { useState, useEffect } from "react";
import type { Settings } from "../types";

interface Props {
  settings: Settings | null;
  onUpdate: (settings: Partial<Settings>) => Promise<void>;
}

export default function SettingsPanel({ settings, onUpdate }: Props) {
  const [dailyHours, setDailyHours] = useState("4");
  const [horizonDays, setHorizonDays] = useState("30");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (settings) {
      setDailyHours(String(settings.default_daily_hours));
      setHorizonDays(String(settings.horizon_days));
    }
  }, [settings]);

  const handleSave = async () => {
    setSaving(true);
    try {
      await onUpdate({ default_daily_hours: Number(dailyHours), horizon_days: Number(horizonDays) });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="card">
      <h2>基本設定</h2>
      <div className="row">
        <label>
          1日の既定作業可能時間 (h)
          <input type="number" min="0.5" step="0.5" value={dailyHours} onChange={(e) => setDailyHours(e.target.value)} />
        </label>
        <label>
          スケジュール対象期間 (日)
          <input type="number" min="1" max="180" value={horizonDays} onChange={(e) => setHorizonDays(e.target.value)} />
        </label>
        <button onClick={handleSave} disabled={saving}>
          {saving ? "保存中..." : "保存"}
        </button>
      </div>
    </div>
  );
}
