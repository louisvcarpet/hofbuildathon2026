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

const Submission = () => {
  const navigate = useNavigate();
  const [offers, setOffers] = useState<UploadedOffer[]>([]);
  const [priorities, setPriorities] = useState<Priorities>({
    financial: 3, career: 3, lifestyle: 3, alignment: 3,
  });

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

  const handleSubmit = () => {
    if (offers.length === 0) {
      toast({ title: "Upload required", description: "Please upload at least one offer letter.", variant: "destructive" });
      return;
    }
    if (!offers.some((o) => o.isCurrent)) {
      toast({ title: "Selection required", description: "Please select a current offer.", variant: "destructive" });
      return;
    }
    const submission = {
      offers: offers.map((o) => ({ id: o.id, fileName: o.file.name, isCurrent: o.isCurrent })),
      priorities,
    };
    sessionStorage.setItem("offergo-submission", JSON.stringify(submission));
    navigate("/analyzing");
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
              className="glow-primary bg-primary text-primary-foreground hover:bg-primary/90 px-10 py-6 text-base font-semibold"
            >
              Analyze Offer
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </div>
        </motion.div>
      </div>
    </div>
  );
};

export default Submission;
