import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import {
  DollarSign,
  TrendingUp,
  Heart,
  Target,
  ShieldAlert,
  CheckCircle2,
  AlertTriangle,
  BarChart3,
  Lightbulb,
  Send,
  Info,
  Bot,
  User,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

/* ── types ── */
interface CategoryScores {
  financial: number;
  career: number;
  lifestyle: number;
  alignment: number;
  risk: number;
}

interface OfferComparison {
  name: string;
  overall: number;
  financial: number;
  career: number;
  risk: number;
}

interface AnalysisData {
  overallScore: number;
  categoryScores: CategoryScores;
  grade: string;
  strengths: string[];
  risks: string[];
  financialProjection: string;
  negotiationInsights: string;
  comparisonData: OfferComparison[];
  confidence: number;
}

interface ChatMessage {
  role: "user" | "ai";
  content: string;
}

/* ── demo data generator ── */
function generateDemoData(): AnalysisData {
  // Check for preloaded demo analysis first
  const demoAnalysis = sessionStorage.getItem("offergo-demo-analysis");
  if (demoAnalysis) {
    return JSON.parse(demoAnalysis);
  }

  const submission = sessionStorage.getItem("offergo-submission");
  const parsed = submission ? JSON.parse(submission) : null;
  const offerCount = parsed?.offers?.length ?? 1;

  const base: AnalysisData = {
    overallScore: 87,
    categoryScores: {
      financial: 92,
      career: 81,
      lifestyle: 74,
      alignment: 85,
      risk: 68,
    },
    grade: "A-",
    strengths: [
      "Total compensation is 18% above market median for this role and geography.",
      "Equity package includes accelerated vesting on acquisition — significant upside.",
      "Strong 401(k) match and health benefits reduce hidden cost exposure.",
      "Role scope aligns well with senior leadership trajectory within 2–3 years.",
    ],
    risks: [
      "Sign-on bonus has a 12-month clawback clause — cash-flow risk if you leave early.",
      "Equity valuation is based on latest 409A which may not reflect current market.",
      "No explicit remote-work guarantee in the offer letter — lifestyle risk.",
      "Non-compete clause could limit lateral moves for 12 months post-departure.",
    ],
    financialProjection:
      "Over a 4-year vesting period, total projected compensation ranges from $820K (bear) to $1.4M (bull), depending on equity appreciation. The base + bonus structure alone places you in the 78th percentile for comparable roles.",
    negotiationInsights:
      "Consider negotiating the sign-on clawback down to 6 months and requesting a remote-work addendum. Equity refresh after Year 2 is common at this stage — worth raising upfront. PTO policy is below industry average; request 5 additional days.",
    comparisonData: [],
    confidence: 82,
  };

  if (offerCount > 1) {
    const names =
      parsed?.offers?.map((o: { fileName: string }) =>
        o.fileName.replace(/\.(pdf|doc|docx)$/i, "")
      ) ?? [];
    base.comparisonData = names.map((name: string, i: number) => ({
      name,
      overall: i === 0 ? 87 : 72 + Math.floor(Math.random() * 12),
      financial: i === 0 ? 92 : 65 + Math.floor(Math.random() * 20),
      career: i === 0 ? 81 : 60 + Math.floor(Math.random() * 25),
      risk: i === 0 ? 68 : 55 + Math.floor(Math.random() * 30),
    }));
  }

  return base;
}

/* ── helpers ── */
const CATEGORIES: {
  key: keyof CategoryScores;
  label: string;
  icon: React.ElementType;
}[] = [
  { key: "financial", label: "Financial Upside", icon: DollarSign },
  { key: "career", label: "Career Acceleration", icon: TrendingUp },
  { key: "lifestyle", label: "Lifestyle Sustainability", icon: Heart },
  { key: "alignment", label: "Mission & Alignment", icon: Target },
  { key: "risk", label: "Risk Exposure", icon: ShieldAlert },
];

function gradeColor(score: number) {
  if (score >= 80) return "text-emerald-400";
  if (score >= 60) return "text-sky-400";
  return "text-amber-400";
}

function barColor(score: number) {
  if (score >= 80) return "bg-emerald-500";
  if (score >= 60) return "bg-sky-500";
  return "bg-amber-500";
}

function highestInRow(comparison: OfferComparison[], field: keyof Omit<OfferComparison, "name">) {
  const max = Math.max(...comparison.map((c) => c[field]));
  return max;
}

/* ── demo chat responses ── */
const CHAT_RESPONSES: Record<string, string> = {
  default:
    "Based on the offer analysis, I'd recommend focusing on the equity clawback and remote-work terms as your primary negotiation levers. Would you like me to draft specific counter-proposal language?",
  equity:
    "The equity component represents approximately 35% of your total compensation. Given the current 409A valuation and typical Series C appreciation curves, the expected value over 4 years is $320K–$580K. However, liquidity risk is moderate — there's no guaranteed secondary market.",
  negotiate:
    "Three high-impact negotiation moves: (1) Reduce sign-on clawback from 12 to 6 months, (2) Request a Year-2 equity refresh clause, (3) Add explicit remote-work language. These are common asks at this level and unlikely to jeopardize the offer.",
  salary:
    "Your base salary sits at the 78th percentile for this role, level, and geography. Pushing for a 5–8% increase is reasonable given your experience, but I'd prioritize equity refresh over base — the long-term delta is significantly larger.",
};

function getAIResponse(msg: string): string {
  const lower = msg.toLowerCase();
  if (lower.includes("equity") || lower.includes("stock") || lower.includes("vest"))
    return CHAT_RESPONSES.equity;
  if (lower.includes("negotiat") || lower.includes("counter") || lower.includes("ask"))
    return CHAT_RESPONSES.negotiate;
  if (lower.includes("salary") || lower.includes("base") || lower.includes("pay"))
    return CHAT_RESPONSES.salary;
  return CHAT_RESPONSES.default;
}

/* ═══════════════ COMPONENT ═══════════════ */

const Results = () => {
  const navigate = useNavigate();
  const [data, setData] = useState<AnalysisData | null>(null);
  const [chat, setChat] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [typing, setTyping] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setData(generateDemoData());
  }, []);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chat, typing]);

  const sendMessage = () => {
    const text = input.trim();
    if (!text) return;
    setChat((prev) => [...prev, { role: "user", content: text }]);
    setInput("");
    setTyping(true);
    setTimeout(() => {
      setChat((prev) => [...prev, { role: "ai", content: getAIResponse(text) }]);
      setTyping(false);
    }, 1500);
  };

  if (!data) return null;

  const fadeUp = (delay = 0) => ({
    initial: { opacity: 0, y: 20 },
    animate: { opacity: 1, y: 0 },
    transition: { duration: 0.5, delay },
  });

  return (
    <div className="min-h-screen bg-background">
      {/* Nav */}
      <nav className="fixed top-0 left-0 right-0 z-50 border-b border-border bg-background/80 backdrop-blur-md">
        <div className="container mx-auto flex h-16 items-center justify-between px-6">
          <button
            onClick={() => navigate("/")}
            className="text-xl font-bold tracking-tight"
          >
            Offer<span className="text-gradient">Go</span>
          </button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => navigate("/submit")}
          >
            New Analysis
          </Button>
        </div>
      </nav>

      <div className="container mx-auto max-w-6xl px-6 pt-28 pb-20">
        {/* Page Header */}
        <motion.div {...fadeUp()} className="mb-12 text-center">
          <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">
            Offer Intelligence Report
          </h1>
          <p className="mx-auto mt-3 max-w-2xl text-muted-foreground">
            AI-powered evaluation based on compensation structure, market
            benchmarks, and your personal priorities.
          </p>
        </motion.div>

        {/* Two-column: Score blocks + AI Insights */}
        <div className="grid gap-8 lg:grid-cols-2">
          {/* LEFT — Score Visualization */}
          <motion.div {...fadeUp(0.1)} className="space-y-6">
            <h2 className="text-lg font-semibold">Offer Score Breakdown</h2>

            {/* Score Blocks */}
            <div className="space-y-3">
              {CATEGORIES.map(({ key, label, icon: Icon }, i) => {
                const score = data.categoryScores[key];
                return (
                  <motion.div
                    key={key}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.4, delay: 0.15 + i * 0.08 }}
                    className="card-elevated p-4"
                  >
                    <div className="mb-2 flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Icon className="h-4 w-4 text-muted-foreground" />
                        <span className="text-sm font-medium">{label}</span>
                      </div>
                      <span
                        className={`text-lg font-bold tabular-nums ${gradeColor(score)}`}
                      >
                        {score}
                      </span>
                    </div>
                    <div className="h-2 w-full overflow-hidden rounded-full bg-secondary">
                      <motion.div
                        className={`h-full rounded-full ${barColor(score)}`}
                        initial={{ width: 0 }}
                        animate={{ width: `${score}%` }}
                        transition={{ duration: 0.8, delay: 0.3 + i * 0.08 }}
                      />
                    </div>
                  </motion.div>
                );
              })}
            </div>

            {/* Overall Grade */}
            <motion.div
              {...fadeUp(0.6)}
              className="card-elevated flex items-center justify-between p-6"
            >
              <div>
                <p className="text-sm text-muted-foreground">
                  Overall Offer Grade
                </p>
                <p className="mt-1 text-4xl font-bold tracking-tight">
                  <span className={gradeColor(data.overallScore)}>
                    {data.grade}
                  </span>
                  <span className="ml-3 text-xl text-muted-foreground">
                    {data.overallScore}/100
                  </span>
                </p>
              </div>
              <Tooltip>
                <TooltipTrigger asChild>
                  <div className="flex flex-col items-center gap-1">
                    <div className="flex items-center gap-1 text-xs text-muted-foreground">
                      <Info className="h-3 w-3" />
                      AI Confidence
                    </div>
                    <span className="text-lg font-semibold text-primary">
                      {data.confidence}%
                    </span>
                  </div>
                </TooltipTrigger>
                <TooltipContent className="max-w-[240px] text-xs">
                  Confidence reflects clarity of compensation structure and
                  market comparables.
                </TooltipContent>
              </Tooltip>
            </motion.div>
          </motion.div>

          {/* RIGHT — AI Reasoning Panel */}
          <motion.div {...fadeUp(0.2)} className="space-y-6">
            <h2 className="text-lg font-semibold">AI Analysis & Key Insights</h2>

            <Accordion
              type="multiple"
              defaultValue={["strengths", "risks", "financial", "negotiation"]}
              className="space-y-3"
            >
              <AccordionItem
                value="strengths"
                className="card-elevated overflow-hidden border-none"
              >
                <AccordionTrigger className="px-5 py-4 hover:no-underline">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                    <span className="text-sm font-medium">Strengths</span>
                  </div>
                </AccordionTrigger>
                <AccordionContent className="px-5 pb-4">
                  <ul className="space-y-2">
                    {data.strengths.map((s, i) => (
                      <li
                        key={i}
                        className="flex gap-2 text-sm text-muted-foreground"
                      >
                        <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-emerald-400" />
                        {s}
                      </li>
                    ))}
                  </ul>
                </AccordionContent>
              </AccordionItem>

              <AccordionItem
                value="risks"
                className="card-elevated overflow-hidden border-none"
              >
                <AccordionTrigger className="px-5 py-4 hover:no-underline">
                  <div className="flex items-center gap-2">
                    <AlertTriangle className="h-4 w-4 text-amber-400" />
                    <span className="text-sm font-medium">Risks</span>
                  </div>
                </AccordionTrigger>
                <AccordionContent className="px-5 pb-4">
                  <ul className="space-y-2">
                    {data.risks.map((r, i) => (
                      <li
                        key={i}
                        className="flex gap-2 text-sm text-muted-foreground"
                      >
                        <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-amber-400" />
                        {r}
                      </li>
                    ))}
                  </ul>
                </AccordionContent>
              </AccordionItem>

              <AccordionItem
                value="financial"
                className="card-elevated overflow-hidden border-none"
              >
                <AccordionTrigger className="px-5 py-4 hover:no-underline">
                  <div className="flex items-center gap-2">
                    <BarChart3 className="h-4 w-4 text-sky-400" />
                    <span className="text-sm font-medium">
                      Financial Projection
                    </span>
                  </div>
                </AccordionTrigger>
                <AccordionContent className="px-5 pb-4">
                  <p className="text-sm leading-relaxed text-muted-foreground">
                    {data.financialProjection}
                  </p>
                </AccordionContent>
              </AccordionItem>

              <AccordionItem
                value="negotiation"
                className="card-elevated overflow-hidden border-none"
              >
                <AccordionTrigger className="px-5 py-4 hover:no-underline">
                  <div className="flex items-center gap-2">
                    <Lightbulb className="h-4 w-4 text-primary" />
                    <span className="text-sm font-medium">
                      Negotiation Opportunities
                    </span>
                  </div>
                </AccordionTrigger>
                <AccordionContent className="px-5 pb-4">
                  <p className="text-sm leading-relaxed text-muted-foreground">
                    {data.negotiationInsights}
                  </p>
                </AccordionContent>
              </AccordionItem>
            </Accordion>
          </motion.div>
        </div>

        {/* Offer Comparison Table */}
        {data.comparisonData.length > 1 && (
          <motion.div {...fadeUp(0.4)} className="mt-12 space-y-4">
            <h2 className="text-lg font-semibold">Offer Comparison</h2>
            <div className="card-elevated overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border text-left">
                    <th className="px-5 py-3 font-medium text-muted-foreground">
                      Metric
                    </th>
                    {data.comparisonData.map((c) => (
                      <th
                        key={c.name}
                        className="px-5 py-3 font-medium text-muted-foreground"
                      >
                        {c.name}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {(
                    [
                      ["Overall Score", "overall"],
                      ["Financial Score", "financial"],
                      ["Career Score", "career"],
                      ["Risk Score", "risk"],
                    ] as const
                  ).map(([label, field]) => {
                    const best = highestInRow(data.comparisonData, field);
                    return (
                      <tr key={field} className="border-b border-border/50">
                        <td className="px-5 py-3 font-medium">{label}</td>
                        {data.comparisonData.map((c) => (
                          <td
                            key={c.name}
                            className={`px-5 py-3 tabular-nums ${
                              c[field] === best
                                ? "font-semibold text-emerald-400"
                                : "text-muted-foreground"
                            }`}
                          >
                            {c[field]}
                          </td>
                        ))}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </motion.div>
        )}

        {/* Chat Interface */}
        <motion.div {...fadeUp(0.5)} className="mt-12 space-y-4">
          <h2 className="text-lg font-semibold">
            Ask OfferGo Anything About This Offer
          </h2>

          <div className="card-elevated flex flex-col" style={{ height: 420 }}>
            {/* Messages */}
            <ScrollArea className="flex-1 p-5">
              {chat.length === 0 && (
                <div className="flex h-full items-center justify-center py-16">
                  <p className="text-sm text-muted-foreground">
                    Ask about negotiation strategy, equity risk, relocation
                    impact…
                  </p>
                </div>
              )}
              <div className="space-y-4">
                {chat.map((msg, i) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    className={`flex gap-3 ${
                      msg.role === "user" ? "justify-end" : "justify-start"
                    }`}
                  >
                    {msg.role === "ai" && (
                      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary/10">
                        <Bot className="h-4 w-4 text-primary" />
                      </div>
                    )}
                    <div
                      className={`max-w-[75%] rounded-xl px-4 py-2.5 text-sm leading-relaxed ${
                        msg.role === "user"
                          ? "bg-primary text-primary-foreground"
                          : "bg-secondary text-secondary-foreground"
                      }`}
                    >
                      {msg.content}
                    </div>
                    {msg.role === "user" && (
                      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-secondary">
                        <User className="h-4 w-4 text-muted-foreground" />
                      </div>
                    )}
                  </motion.div>
                ))}
                {typing && (
                  <div className="flex items-center gap-3">
                    <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary/10">
                      <Bot className="h-4 w-4 text-primary" />
                    </div>
                    <div className="flex gap-1 rounded-xl bg-secondary px-4 py-3">
                      <span className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground/50 [animation-delay:0ms]" />
                      <span className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground/50 [animation-delay:150ms]" />
                      <span className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground/50 [animation-delay:300ms]" />
                    </div>
                  </div>
                )}
                <div ref={chatEndRef} />
              </div>
            </ScrollArea>

            {/* Input */}
            <div className="border-t border-border p-4">
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  sendMessage();
                }}
                className="flex gap-2"
              >
                <Input
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="Ask about negotiation strategy, equity risk, relocation impact…"
                  className="flex-1"
                />
                <Button
                  type="submit"
                  size="icon"
                  disabled={!input.trim() || typing}
                  className="shrink-0"
                >
                  <Send className="h-4 w-4" />
                </Button>
              </form>
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
};

export default Results;
