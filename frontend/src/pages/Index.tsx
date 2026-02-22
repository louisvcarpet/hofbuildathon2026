import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowRight, BarChart3, Shield, TrendingUp, CheckCircle2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useProfile } from "@/hooks/use-profile";
import Navbar from "@/components/Navbar";

const features = [
  {
    icon: BarChart3,
    title: "Market Benchmarking",
    description: "Compare your offer against real-time compensation data across industries and roles.",
  },
  {
    icon: Shield,
    title: "Risk Profiling",
    description: "Understand financial exposure, vesting cliffs, and total compensation volatility.",
  },
  {
    icon: TrendingUp,
    title: "Career Trajectory",
    description: "Project long-term earnings and growth potential across competing offers.",
  },
];

const Index = () => {
  const navigate = useNavigate();
  const { profile } = useProfile();

  return (
    <div className="min-h-screen bg-background">
      <Navbar />

      {/* Hero */}
      <section className="relative flex min-h-screen flex-col items-center justify-center px-6 pt-16">
        <div className="pointer-events-none absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 h-[500px] w-[500px] rounded-full bg-primary/5 blur-[120px]" />

        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, ease: "easeOut" }}
          className="relative z-10 max-w-3xl text-center"
        >
          <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-border bg-secondary px-4 py-1.5 text-sm text-muted-foreground">
            <span className="h-1.5 w-1.5 rounded-full bg-primary animate-pulse-glow" />
            AI-Powered Offer Intelligence
          </div>

          <h1 className="mb-6 text-4xl font-extrabold leading-tight tracking-tight sm:text-5xl lg:text-6xl">
            Every Offer Is a Decision.{" "}
            <span className="text-gradient">Make It an Intelligent One.</span>
          </h1>

          <p className="mb-4 text-lg text-muted-foreground leading-relaxed sm:text-xl">
            OfferGo is your AI-powered offer intelligence platform. We analyze
            compensation, risk, market positioning, and long-term value — so you
            never accept blindly again.
          </p>

          <p className="mb-10 text-base text-foreground/70 leading-relaxed max-w-2xl mx-auto">
            Most people evaluate offers based on salary alone. OfferGo evaluates
            your offer against your financial position, career trajectory, and
            market benchmarks — delivering a structured grade, risk profile, and
            negotiation insights in seconds.
          </p>

          {!profile.completed && (
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.5 }}
              className="mb-6 text-sm text-primary/80"
            >
              Complete your profile for personalized evaluation.
            </motion.p>
          )}

          {profile.completed && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.3 }}
              className="mb-6 inline-flex items-center gap-2 rounded-full bg-primary/10 px-4 py-1.5 text-sm text-primary"
            >
              <CheckCircle2 className="h-3.5 w-3.5" />
              Profile Completed
            </motion.div>
          )}

          <Button
            size="lg"
            onClick={() => navigate("/submit")}
            className="glow-primary bg-primary text-primary-foreground hover:bg-primary/90 px-8 py-6 text-base font-semibold"
          >
            Get Started
            <ArrowRight className="ml-2 h-4 w-4" />
          </Button>
        </motion.div>
      </section>

      {/* Features */}
      <section className="border-t border-border py-24 px-6">
        <div className="container mx-auto max-w-5xl">
          <motion.div
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
            className="mb-16 text-center"
          >
            <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
              Intelligence, Not Guesswork
            </h2>
            <p className="mt-4 text-muted-foreground max-w-xl mx-auto">
              Every dimension of your offer — analyzed, scored, and presented with clarity.
            </p>
          </motion.div>

          <div className="grid gap-8 md:grid-cols-3">
            {features.map((f, i) => (
              <motion.div
                key={f.title}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.15, duration: 0.5 }}
                className="card-elevated p-6"
              >
                <div className="mb-4 inline-flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <f.icon className="h-5 w-5" />
                </div>
                <h3 className="mb-2 text-lg font-semibold">{f.title}</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">
                  {f.description}
                </p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border py-8 px-6 text-center text-sm text-muted-foreground">
        © {new Date().getFullYear()} OfferGo. Built for better decisions.
      </footer>
    </div>
  );
};

export default Index;
