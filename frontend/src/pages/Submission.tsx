import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowRight, Upload, Plus, FileText, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import { toast } from "@/hooks/use-toast";
import Navbar from "@/components/Navbar";

interface UploadedOffer {
  id: string;
  file: File;
  isCurrent: boolean;
}

interface Priorities {
  financial: number;
  career: number;
  lifestyle: number;
  alignment: number;
}

type WorkflowEvaluation = {
  score: number;
  recommendation: "accept" | "renegotiate" | "needs_more_info";
  confidence: number;
  key_drivers: { label: string; impact: "positive" | "negative" | "neutral" }[];
  negotiation_targets: { item: string; ask: string; reason: string }[];
  risks: string[];
  followup_questions: string[];
  one_paragraph_summary: string;
};

type IngestResponse = {
  offer_id?: number;
  parsed?: {
    base_salary?: number | null;
    bonus_target?: number | null;
    equity_amount?: number | null;
  };
};

type MarketSnapshotResponse = {
  provider: string;
  databricks_table?: string | null;
  sample_size: number;
  market_base_median: number;
  market_bonus_avg: number;
  market_signing_avg: number;
  market_total_est: number;
  offer_total_est: number;
  offer_vs_market_ratio: number;
};

type ResultsAnalysisData = {
  overallScore: number;
  categoryScores: {
    financial: number;
    career: number;
    lifestyle: number;
    alignment: number;
    risk: number;
  };
  grade: string;
  strengths: string[];
  risks: string[];
  financialProjection: string;
  negotiationInsights: string;
  comparisonData: { name: string; overall: number; financial: number; career: number; risk: number }[];
  confidence: number;
  recommendation: WorkflowEvaluation["recommendation"];
};

const Submission = () => {
  const navigate = useNavigate();
  const [offers, setOffers] = useState<UploadedOffer[]>([]);
  const [priorities, setPriorities] = useState<Priorities>({
    financial: 3, career: 3, lifestyle: 3, alignment: 3,
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "http://127.0.0.1:8000";

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const newOffer: UploadedOffer = {
      id: crypto.randomUUID(),
      file,
      isCurrent: offers.length === 0,
    };
    setOffers((prev) => [...prev, newOffer]);
    e.target.value = "";
  };

  const removeOffer = (id: string) => {
    setOffers((prev) => {
      const filtered = prev.filter((o) => o.id !== id);
      if (filtered.length > 0 && !filtered.some((o) => o.isCurrent)) {
        filtered[0].isCurrent = true;
      }
      return [...filtered];
    });
  };

  const selectCurrent = (id: string) => {
    setOffers((prev) =>
      prev.map((o) => ({ ...o, isCurrent: o.id === id }))
    );
  };

  const toGrade = (score100: number): string => {
    if (score100 >= 93) return "A";
    if (score100 >= 85) return "A-";
    if (score100 >= 78) return "B+";
    if (score100 >= 70) return "B";
    if (score100 >= 62) return "C";
    return "D";
  };

  const clamp = (n: number, low: number, high: number) => Math.max(low, Math.min(high, n));

  const mapEvalToAnalysis = (evalOut: WorkflowEvaluation, currentFileName: string): ResultsAnalysisData => {
    const overallScore = clamp(Math.round(evalOut.score * 10), 0, 100);
    const confidence = clamp(Math.round(evalOut.confidence * 100), 0, 100);
    const riskPenalty = evalOut.recommendation === "needs_more_info" ? 18 : evalOut.recommendation === "renegotiate" ? 8 : 0;
    const riskScore = clamp(Math.round(76 - evalOut.risks.length * 7 - riskPenalty + confidence * 0.1), 12, 95);
    const categoryScores = {
      financial: clamp(Math.round(overallScore + (priorities.financial - 3) * 6), 8, 98),
      career: clamp(Math.round(overallScore - 4 + (priorities.career - 3) * 6), 8, 98),
      lifestyle: clamp(Math.round(overallScore - 8 + (priorities.lifestyle - 3) * 6), 8, 95),
      alignment: clamp(Math.round(overallScore - 6 + (priorities.alignment - 3) * 6), 8, 96),
      risk: riskScore,
    };

    const strengths = evalOut.key_drivers
      .filter((d) => d.impact === "positive" || d.impact === "neutral")
      .map((d) => d.label)
      .slice(0, 6);
    const negotiationInsights =
      evalOut.negotiation_targets.length > 0
        ? evalOut.negotiation_targets.map((t) => `${t.item}: ${t.ask} (${t.reason})`).join(" ")
        : "No negotiation targets were returned by the model.";

    return {
      overallScore,
      categoryScores,
      grade: toGrade(overallScore),
      strengths: strengths.length ? strengths : ["Model did not return positive key drivers."],
      risks: evalOut.risks,
      financialProjection: evalOut.one_paragraph_summary,
      negotiationInsights,
      comparisonData: [
        {
          name: currentFileName.replace(/\.(pdf|doc|docx)$/i, ""),
          overall: overallScore,
          financial: categoryScores.financial,
          career: categoryScores.career,
          risk: categoryScores.risk,
        },
      ],
      confidence,
      recommendation: evalOut.recommendation,
    };
  };

  const handleSubmit = async () => {
    if (offers.length === 0) {
      toast({ title: "Upload required", description: "Please upload at least one offer letter.", variant: "destructive" });
      return;
    }
    if (!offers.some((o) => o.isCurrent)) {
      toast({ title: "Selection required", description: "Please select a current offer.", variant: "destructive" });
      return;
    }
    const currentOffer = offers.find((o) => o.isCurrent);
    if (!currentOffer) return;
    if (!currentOffer.file.name.toLowerCase().endsWith(".pdf")) {
      toast({ title: "PDF required", description: "Please upload a PDF offer letter.", variant: "destructive" });
      return;
    }

    setIsSubmitting(true);
    try {
      const formData = new FormData();
      formData.append("file", currentOffer.file);
      formData.append("priority_financial", String(priorities.financial));
      formData.append("priority_career", String(priorities.career));
      formData.append("priority_lifestyle", String(priorities.lifestyle));
      formData.append("priority_alignment", String(priorities.alignment));

      const ingestResp = await fetch(`${apiBaseUrl}/offers/ingest-pdf?create_records=true`, {
        method: "POST",
        headers: { "X-User-Id": "42" },
        body: formData,
      });
      if (!ingestResp.ok) {
        throw new Error(await ingestResp.text());
      }
      const ingestJson = (await ingestResp.json()) as IngestResponse;
      if (!ingestJson.offer_id) {
        throw new Error("Ingest succeeded but no offer_id was returned.");
      }

      const evalResp = await fetch(`${apiBaseUrl}/offers/${ingestJson.offer_id}/evaluate?mode=workflow`, {
        method: "POST",
        headers: { "X-User-Id": "42" },
      });
      if (!evalResp.ok) {
        throw new Error(await evalResp.text());
      }
      const evalJson = (await evalResp.json()) as WorkflowEvaluation;

      let marketSnapshot: MarketSnapshotResponse | null = null;
      try {
        const marketResp = await fetch(`${apiBaseUrl}/offers/${ingestJson.offer_id}/market-snapshot`, {
          method: "GET",
          headers: { "X-User-Id": "42" },
        });
        if (marketResp.ok) {
          marketSnapshot = (await marketResp.json()) as MarketSnapshotResponse;
        }
      } catch {
        // Keep UX resilient; chart can still use fallback derivation.
      }

      const submission = {
        offers: offers.map((o) => ({ id: o.id, fileName: o.file.name, isCurrent: o.isCurrent })),
        priorities,
        backendOfferId: ingestJson.offer_id,
      };
      sessionStorage.setItem("offergo-submission", JSON.stringify(submission));
      sessionStorage.setItem("offergo-demo-analysis", JSON.stringify(mapEvalToAnalysis(evalJson, currentOffer.file.name)));
      sessionStorage.setItem("offergo-workflow-eval", JSON.stringify(evalJson));
      sessionStorage.setItem("offergo-ingest-parsed", JSON.stringify(ingestJson.parsed ?? {}));
      if (marketSnapshot) {
        sessionStorage.setItem("offergo-market-snapshot", JSON.stringify(marketSnapshot));
      }
      navigate("/results");
    } catch (error) {
      toast({
        title: "Analysis failed",
        description: error instanceof Error ? error.message : "Unknown error",
        variant: "destructive",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Nav */}
      <Navbar />

      <div className="container mx-auto max-w-3xl px-6 pt-28 pb-16">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="space-y-12"
        >
          {/* Header */}
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Upload Your Offer & Set Your Priorities</h1>
            <p className="mt-2 text-muted-foreground">Upload one or more offers and rank what matters most to you.</p>
          </div>

          {/* Upload Section */}
          <section className="space-y-5">
            <h2 className="text-lg font-semibold">Offer Letters</h2>

            {offers.length === 0 ? (
              <label className="flex cursor-pointer flex-col items-center gap-3 rounded-lg border-2 border-dashed border-border bg-secondary/30 px-6 py-10 text-center transition-colors hover:border-primary/50 hover:bg-secondary/50">
                <Upload className="h-8 w-8 text-muted-foreground" />
                <div>
                  <p className="text-sm font-medium text-foreground">Upload Offer Letter</p>
                  <p className="text-xs text-muted-foreground">PDF or DOC accepted</p>
                </div>
                <input type="file" accept=".pdf,.doc,.docx" className="hidden" onChange={handleFileUpload} />
              </label>
            ) : (
              <div className="space-y-3">
                {offers.map((offer) => (
                  <motion.div
                    key={offer.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className={`flex items-center gap-4 rounded-lg border p-4 transition-all ${
                      offer.isCurrent
                        ? "border-primary/50 bg-primary/5 glow-primary"
                        : "border-border bg-card"
                    }`}
                  >
                    <FileText className="h-5 w-5 shrink-0 text-muted-foreground" />
                    <span className="flex-1 truncate text-sm font-medium">{offer.file.name}</span>

                    <label className="flex cursor-pointer items-center gap-2 text-xs text-muted-foreground whitespace-nowrap">
                      <input
                        type="checkbox"
                        checked={offer.isCurrent}
                        onChange={() => selectCurrent(offer.id)}
                        className="accent-[hsl(172,66%,50%)] h-4 w-4"
                      />
                      Select as current offer
                    </label>

                    <button
                      onClick={() => removeOffer(offer.id)}
                      className="rounded p-1 text-muted-foreground hover:bg-destructive/10 hover:text-destructive transition-colors"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </motion.div>
                ))}

                <label className="flex cursor-pointer items-center gap-2 rounded-lg border border-dashed border-border px-4 py-3 text-sm text-muted-foreground transition-colors hover:border-primary/50 hover:text-foreground">
                  <Plus className="h-4 w-4" />
                  Add Another Offer
                  <input type="file" accept=".pdf,.doc,.docx" className="hidden" onChange={handleFileUpload} />
                </label>
              </div>
            )}
          </section>

          {/* Divider */}
          <div className="border-t border-border" />

          {/* Preferences */}
          <section className="space-y-6">
            <div>
              <h2 className="text-lg font-semibold">Your Evaluation Priorities</h2>
              <p className="mt-1 text-sm text-muted-foreground">Rank what matters most in evaluating this offer.</p>
            </div>

            <div className="space-y-6">
              {[
                { key: "financial" as const, q: "How important is total financial upside (salary + bonus + equity + future earnings potential)?" },
                { key: "career" as const, q: "How important is skill development and long-term career acceleration in this role?" },
                { key: "lifestyle" as const, q: "How important is lifestyle sustainability (hours, stress, flexibility)?" },
                { key: "alignment" as const, q: "How important is alignment with the company's mission, culture, and industry interest?" },
              ].map(({ key, q }) => (
                <div key={key} className="card-elevated p-5 space-y-4">
                  <p className="text-sm font-medium leading-relaxed">{q}</p>
                  <div className="flex items-center gap-4">
                    <span className="text-xs text-muted-foreground w-6">1</span>
                    <Slider
                      min={1}
                      max={5}
                      step={1}
                      value={[priorities[key]]}
                      onValueChange={([v]) => setPriorities((p) => ({ ...p, [key]: v }))}
                      className="flex-1"
                    />
                    <span className="text-xs text-muted-foreground w-6">5</span>
                    <span className="ml-2 flex h-8 w-8 items-center justify-center rounded-md bg-primary/10 text-sm font-semibold text-primary">
                      {priorities[key]}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* Submit */}
          <div className="flex justify-center pt-4">
            <Button
              size="lg"
              onClick={handleSubmit}
              disabled={isSubmitting}
              className="glow-primary bg-primary text-primary-foreground hover:bg-primary/90 px-10 py-6 text-base font-semibold"
            >
              {isSubmitting ? "Analyzing..." : "Analyze Offer"}
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </div>
        </motion.div>
      </div>
    </div>
  );
};

export default Submission;
