import { Button } from "./ui/Button";
import { Card } from "./ui/Card";
import type { EligibilityResult } from "../types/eligibility";

const TONE: Record<EligibilityResult["decision"], string> = {
  ELIGIBLE: "text-emerald-300",
  INELIGIBLE: "text-rose-300",
  NEEDS_REVIEW: "text-amber-300",
};

type EligibilityPanelProps = {
  result: EligibilityResult | null;
  loading?: boolean;
  onRequestReview?: () => void;
  onExplain?: () => void;
  explainLoading?: boolean;
};

export function EligibilityPanel({ result, loading, onRequestReview, onExplain, explainLoading }: EligibilityPanelProps) {
  if (loading) {
    return <Card className="p-4 text-sm text-ink-muted">Checking eligibility…</Card>;
  }
  if (!result) {
    return null;
  }
  return (
    <Card className="space-y-3 p-5">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-sm font-semibold text-white">Eligibility decision</h2>
        <p className={`text-sm font-semibold ${TONE[result.decision]}`}>{result.decision.replaceAll("_", " ")}</p>
      </div>
      <p className="text-sm text-ink">{result.explanation}</p>
      <dl className="grid gap-1 text-xs text-ink-muted">
        <div>
          <dt className="inline font-medium text-ink">Code: </dt>
          <dd className="inline">{result.decision_code}</dd>
        </div>
        <div>
          <dt className="inline font-medium text-ink">Policy version: </dt>
          <dd className="inline">{result.policy_rule_version}</dd>
        </div>
        <div>
          <dt className="inline font-medium text-ink">Confidence: </dt>
          <dd className="inline">{result.decision_reason}</dd>
        </div>
      </dl>
      {result.missing_information.length > 0 ? (
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-ink-faint">Missing information</p>
          <ul className="mt-1 list-inside list-disc text-sm text-ink-muted">
            {result.missing_information.map((row) => (
              <li key={row.field ?? row.label}>{row.label ?? row.field}</li>
            ))}
          </ul>
        </div>
      ) : null}
      {result.policy_references.length > 0 ? (
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-ink-faint">Policy sources</p>
          <ul className="mt-1 space-y-1 text-xs text-ink-muted">
            {result.policy_references.map((ref, index) => (
              <li key={`${ref.rule_key}-${index}`}>
                {String(ref.source)} v{String(ref.version)} · {String(ref.rule_key)}
                {ref.detail ? ` (${String(ref.detail)})` : ""}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      {result.recommended_next_steps.length > 0 ? (
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-ink-faint">Recommended next steps</p>
          <ul className="mt-1 list-inside list-disc text-sm text-ink-muted">
            {result.recommended_next_steps.map((step) => (
              <li key={step}>{step}</li>
            ))}
          </ul>
        </div>
      ) : null}
      {result.ai_explanation ? (
        <div className="rounded-lg border border-navy-600 bg-navy-950 p-3 text-sm text-ink-muted">
          <p className="text-xs font-semibold uppercase tracking-wide text-ink-faint">AI summary (non-binding)</p>
          <p className="mt-2 whitespace-pre-wrap text-ink">{result.ai_explanation}</p>
        </div>
      ) : null}
      <div className="flex flex-wrap gap-2">
        {onExplain ? (
          <Button type="button" variant="secondary" disabled={explainLoading} onClick={onExplain}>
            Generate AI summary
          </Button>
        ) : null}
        {onRequestReview && !result.human_review_requested ? (
          <Button type="button" variant="secondary" onClick={onRequestReview}>
            Request human review
          </Button>
        ) : null}
      </div>
    </Card>
  );
}