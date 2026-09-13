import { useCallback, useEffect, useState } from "react";
import { api } from "./api";

/** Loads and refreshes the aggregate progress summary (completion, streak, phase mastery). */
export function useProgress() {
  const [summary, setSummary] = useState(null);

  const refresh = useCallback(() => {
    api("/progress/summary").then(setSummary);
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const setMastery = useCallback(
    async (conceptId, masteryLevel) => {
      await api("/progress/mastery", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ concept_id: conceptId, mastery_level: masteryLevel }),
      });
      refresh();
    },
    [refresh]
  );

  return { summary, refresh, setMastery };
}
