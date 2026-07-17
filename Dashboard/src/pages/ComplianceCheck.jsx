import { useEffect, useRef, useState } from "react";
import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import ComplianceResultCard from "../components/ComplianceResultCard";
import EmptyState from "../components/EmptyState";
import { runComplianceCheck, getLastComplianceCheck } from "../api/client";
import { useToast } from "../components/Toast";

export default function ComplianceCheck() {
  const [results, setResults] = useState([]);
  const [ranAt, setRanAt] = useState(null);
  const [loading, setLoading] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);
  const boxRef = useRef(null);
  const toast = useToast();

  // Load whatever was last saved, on mount — survives navigation AND refresh
  useEffect(() => {
    getLastComplianceCheck()
      .then((res) => {
        setResults(res.data.results || []);
        setRanAt(res.data.ran_at || null);
      })
      .catch(() => {})
      .finally(() => setInitialLoading(false));
  }, []);

  useGSAP(
    () => {
      if (loading) boxRef.current?.classList.add("radar-sweep");
      else boxRef.current?.classList.remove("radar-sweep");
    },
    { dependencies: [loading] }
  );

  const handleRun = async () => {
    setLoading(true);
    try {
      const res = await runComplianceCheck();
      setResults(res.data.results || []);
      setRanAt(res.data.ran_at || null);
    } catch (err) {
      toast?.show("Compliance check failed — check the backend.", "error");
    } finally {
      setLoading(false);
    }
  };

  const deviationCount = results.filter((r) => r.status === "Deviation").length;
  const hasRun = ranAt !== null;

  const formattedTime = ranAt
    ? new Date(ranAt).toLocaleString(undefined, {
        dateStyle: "medium",
        timeStyle: "short",
      })
    : null;

  return (
    <div className="px-4 sm:px-8 py-6 sm:py-8 max-w-6xl">
      <h2 className="text-xl font-medium text-text-primary mb-6">Compliance Check</h2>

      <div className="grid grid-cols-1 lg:grid-cols-[320px_1fr] gap-6">
        <div
          ref={boxRef}
          className="bg-surface border border-border rounded-2xl p-6 h-fit lg:sticky lg:top-20"
        >
          <p className="text-text-secondary text-sm mb-4">
            Compares equipment specifications against vendor submittals and
            flags any deviations, with severity ranking.
          </p>
          <div className="text-xs text-text-muted mb-6 space-y-1">
            <div>Spec: UPS_System_Specification</div>
            <div>Submittal: UPS_Vendor_Submittal</div>
          </div>
          <button
            onClick={handleRun}
            disabled={loading}
            className="w-full py-2.5 rounded-xl bg-accent text-white text-sm disabled:opacity-50 hover:bg-accent/90 transition-colors"
          >
            {loading ? "Checking…" : hasRun ? "Re-run Compliance Check" : "Run Compliance Check"}
          </button>

          {hasRun && !loading && (
            <div className="mt-4 space-y-1">
              <div className="text-xs text-text-muted">Last run: {formattedTime}</div>
              <div className="text-xs">
                {deviationCount > 0 ? (
                  <span className="text-status-fail">{deviationCount} deviation(s) found</span>
                ) : (
                  <span className="text-status-match">All requirements matched</span>
                )}
              </div>
            </div>
          )}
        </div>

        <div className="space-y-3">
          {initialLoading && (
            <EmptyState icon="⏳" title="Loading last result…" />
          )}
          {!initialLoading && !hasRun && (
            <EmptyState
              icon="🛡️"
              title="No check run yet"
              description="Run a compliance check to compare spec vs. vendor submittal."
            />
          )}
          {!initialLoading && hasRun && results.length === 0 && (
            <EmptyState
              icon="⚠️"
              title="No results returned"
              description="The backend responded, but no comparisons were found."
            />
          )}
          {results.map((r, i) => (
            <ComplianceResultCard key={i} result={r} index={i} />
          ))}
        </div>
      </div>
    </div>
  );
}