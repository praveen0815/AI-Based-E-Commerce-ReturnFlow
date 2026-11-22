import { useEffect, useState } from "react";

import { getAiReviewRun, latestAiReview, listAiReviewEvents, resumeAiReview, startAiReview } from "../services/aiReview";
import type { AiReviewEvent, AiReviewRun } from "../types/aiReview";
import { ApiError } from "../services/api";
import { Button } from "./ui/Button";
import { Card } from "./ui/Card";
import { Spinner } from "./ui/Spinner";

type AiReviewPanelProps = {
  returnId: string;
  canManage: boolean;
};

function isTerminal(status: AiReviewRun["status"]): boolean {
  return ["AWAITING_HUMAN", "COMPLETED", "FAILED", "TIMED_OUT"].includes(status);
}

export function AiReviewPanel({ returnId, canManage }: AiReviewPanelProps) {
  const [run, setRun] = useState<AiReviewRun | null>(null);
  const [events, setEvents] = useState<AiReviewEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function refresh(runId: string) {
    const [detail, history] = await Promise.all([
      getAiReviewRun(returnId, runId),
      listAiReviewEvents(returnId, runId),
    ]);
    setRun(detail);
    setEvents(history);
  }

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    latestAiReview(returnId)
      .then(async (latest) => {
        if (cancelled) {
          return;
        }
        if (!latest) {
          setRun(null);
          setEvents([]);
          return;
        }
        await refresh(latest.id);
      })
      .catch((caught: unknown) => {
        if (!cancelled) {
          setError(caught instanceof ApiError ? caught.message : "Could not load AI review.");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [returnId]);

  useEffect(() => {
    if (!run || isTerminal(run.status)) {
      return;
    }
    const timer = window.setInterval(() => {
      void refresh(run.id).catch(() => undefined);
    }, 2000);
    return () => window.clearInterval(timer);
  }, [run, returnId]);

  async function onStart() {
    setError("");
    try {
      const started = await startAiReview(returnId);
      setRun(started);
      await refresh(started.id);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Could not start AI review.");
    }
  }

  async function onAcknowledge() {
    if (!run) {
      return;
    }
    try {
      const updated = await resumeAiReview(returnId, run.id, {
        decision: "ACKNOWLEDGE",
        note: "Staff reviewed AI recommendation",
      });
      setRun(updated);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Resume failed.");
    }
  }

  const output = (run?.output_payload ?? null) as {
    finalization?: { recommendation?: string; summary?: string; next_steps?: string[] };
    eligibility?: { decision?: string; explanation?: string; locked?: boolean };
    policy_research?: { evidence_summary?: string; citations?: unknown[] };
    resolution?: { suggested_resolution?: string; rationale?: string };
  } | null;

  if (loading) {
    return <Spinner label="Loading AI review" />;
  }

  return (
    <Card className="space-y-4 p-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-base font-semibold text-white">AI review workflow</h2>
        {canManage ? (
          <Button type="button" variant="secondary" onClick={() => void onStart()}>
            {run ? "Run again" : "Start AI review"}
          </Button>
        ) : null}
      </div>
      {error ? <p className="text-sm text-rose-300">{error}</p> : null}
      {!run ? (
        <p className="text-sm text-ink-muted">No AI review has been run for this return yet.</p>
      ) : (
        <>
          <p className="text-sm text-ink-muted">
            Status: <span className="text-ink">{run.status}</span>
            {run.current_agent ? ` · Agent ${run.current_agent}` : ""}
          </p>
          {output?.eligibility ? (
            <ReviewSection title="Eligibility (deterministic)">
              <p className="text-sm text-ink">
                {output.eligibility.decision} — {output.eligibility.explanation}
              </p>
            </ReviewSection>
          ) : null}
          {output?.policy_research ? (
            <ReviewSection title="Policy evidence">
              <p className="text-sm text-ink-muted">{output.policy_research.evidence_summary}</p>
            </ReviewSection>
          ) : null}
          {output?.resolution ? (
            <ReviewSection title="Suggested resolution">
              <p className="text-sm text-ink">
                {output.resolution.suggested_resolution}: {output.resolution.rationale}
              </p>
            </ReviewSection>
          ) : null}
          {output?.finalization ? (
            <ReviewSection title="Recommendation">
              <p className="text-sm text-ink">{output.finalization.recommendation}</p>
              <p className="text-sm text-ink-muted">{output.finalization.summary}</p>
            </ReviewSection>
          ) : null}
          <section>
            <h3 className="text-sm font-medium text-white">Agent activity</h3>
            <ul className="mt-2 space-y-1 text-xs text-ink-muted">
              {events.map((event) => (
                <li key={event.id}>
                  {event.sequence}. {event.agent} — {event.event_type}
                </li>
              ))}
            </ul>
          </section>
          {run.status === "AWAITING_HUMAN" && canManage ? (
            <Button type="button" onClick={() => void onAcknowledge()}>
              Acknowledge recommendation
            </Button>
          ) : null}
        </>
      )}
    </Card>
  );
}

function ReviewSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-lg border border-navy-600 bg-navy-950/60 p-3">
      <h3 className="text-sm font-medium text-white">{title}</h3>
      <div className="mt-1">{children}</div>
    </section>
  );
}