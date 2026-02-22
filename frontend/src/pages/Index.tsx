import { useNavigate } from "react-router-dom";
import { useRef, useEffect, useState } from "react";
import { motion, useScroll, useTransform } from "framer-motion";
import { ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import Navbar from "@/components/Navbar";
import { useProfile } from "@/hooks/use-profile";

const fadeUp = {
  hidden: { opacity: 0, y: 24 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.12, duration: 0.6, ease: [0.25, 0.46, 0.45, 0.94] as const },
  }),
};

const features = [
  {
    title: "Compensation Structure",
    text: "We model more than base salary.\nCash reliability. Equity dilution. Bonus probability.",
    visual: (
      <div className="space-y-3">
        <div className="flex items-end gap-2">
          {[65, 82, 45, 90, 72].map((h, i) => (
            <motion.div
              key={i}
              initial={{ height: 0 }}
              whileInView={{ height: `${h}%` }}
              viewport={{ once: true }}
              transition={{ delay: 0.3 + i * 0.08, duration: 0.5, ease: "easeOut" }}
              className="w-8 rounded-sm bg-primary/15"
              style={{ minHeight: 8 }}
            />
          ))}
        </div>
        <div className="space-y-2">
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>Base</span><span className="font-medium text-foreground">$145,000</span>
          </div>
          <div className="h-px bg-border" />
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>Equity (adj.)</span><span className="font-medium text-foreground">$62,400</span>
          </div>
          <div className="h-px bg-border" />
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>Bonus (prob.)</span><span className="font-medium text-foreground">$18,200</span>
          </div>
        </div>
      </div>
    ),
  },
  {
    title: "Risk Exposure",
    text: "Company survival odds.\nIndustry volatility.\nRole replaceability.",
    visual: (
      <div className="space-y-4">
        {[
          { label: "Company Stability", value: 78, color: "bg-primary/20" },
          { label: "Industry Growth", value: 64, color: "bg-primary/15" },
          { label: "Role Demand", value: 91, color: "bg-primary/25" },
        ].map((item, i) => (
          <div key={i} className="space-y-1.5">
            <div className="flex justify-between text-xs">
              <span className="text-muted-foreground">{item.label}</span>
              <span className="font-medium text-foreground">{item.value}%</span>
            </div>
            <div className="h-1.5 rounded-full bg-muted">
              <motion.div
                initial={{ width: 0 }}
                whileInView={{ width: `${item.value}%` }}
                viewport={{ once: true }}
                transition={{ delay: 0.3 + i * 0.1, duration: 0.6, ease: "easeOut" }}
                className={`h-full rounded-full ${item.color}`}
              />
            </div>
          </div>
        ))}
      </div>
    ),
  },
  {
    title: "Long-Term Value",
    text: "Five-year projection modeling.\nCareer acceleration delta.\nExit optionality.",
    visual: (
      <div className="space-y-3">
        {["Year 1", "Year 2", "Year 3", "Year 5"].map((year, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, x: -8 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.3 + i * 0.1, duration: 0.4 }}
            className="flex items-center gap-3"
          >
            <div className="flex h-8 w-8 items-center justify-center rounded-full border border-border text-[10px] font-medium text-muted-foreground">
              {year.replace("Year ", "Y")}
            </div>
            <div className="h-px flex-1 bg-border" />
            <span className="text-xs font-medium text-foreground">
              {["$225K", "$268K", "$312K", "$410K"][i]}
            </span>
          </motion.div>
        ))}
      </div>
    ),
  },
];

const Index = () => {
  const navigate = useNavigate();
  const { profile } = useProfile();
  const { scrollYProgress } = useScroll();
  const heroOpacity = useTransform(scrollYProgress, [0, 0.15], [1, 0]);
  const heroY = useTransform(scrollYProgress, [0, 0.15], [0, -40]);

  // Cursor-follow spotlight
  const heroRef = useRef<HTMLElement>(null);
  const [spotPos, setSpotPos] = useState({ x: 50, y: 50 });

  useEffect(() => {
    const hero = heroRef.current;
    if (!hero) return;
    const onMove = (e: MouseEvent) => {
      const rect = hero.getBoundingClientRect();
      setSpotPos({
        x: ((e.clientX - rect.left) / rect.width) * 100,
        y: ((e.clientY - rect.top) / rect.height) * 100,
      });
    };
    hero.addEventListener("mousemove", onMove);
    return () => hero.removeEventListener("mousemove", onMove);
  }, []);

  useEffect(() => {
    if (profile.completed) {
      navigate("/dashboard", { replace: true });
    }
  }, [profile.completed, navigate]);

  return (
    <div className="min-h-screen bg-background">
      <Navbar />

      {/* Hero */}
      <section
        ref={heroRef}
        className="relative flex min-h-screen flex-col items-center justify-center px-6 pt-16 -mt-16 overflow-hidden"
      >
        {/* Cursor-follow soft spotlight */}
        <div
          className="pointer-events-none absolute h-[600px] w-[600px] rounded-full transition-all duration-[1200ms] ease-out opacity-[0.035]"
          style={{
            left: `${spotPos.x}%`,
            top: `${spotPos.y}%`,
            transform: "translate(-50%, -50%)",
            background: "radial-gradient(circle, hsl(172 40% 60%), transparent 70%)",
          }}
        />

        {/* Subtle radial glow behind headline */}
        <div className="pointer-events-none absolute top-[40%] left-1/2 -translate-x-1/2 -translate-y-1/2 h-[500px] w-[500px] rounded-full bg-primary/[0.03] blur-[120px]" />

        {/* Faint grid */}
        <div
          className="pointer-events-none absolute inset-0 opacity-[0.025]"
          style={{
            backgroundImage: `linear-gradient(hsl(var(--foreground)) 1px, transparent 1px),
                              linear-gradient(90deg, hsl(var(--foreground)) 1px, transparent 1px)`,
            backgroundSize: "80px 80px",
          }}
        />

        <motion.div
          style={{ opacity: heroOpacity, y: heroY }}
          className="relative z-10 max-w-2xl text-center"
        >
          <motion.h1
            variants={fadeUp}
            initial="hidden"
            animate="visible"
            custom={0}
            className="mb-16 text-4xl font-bold leading-[1.1] tracking-tight sm:text-5xl lg:text-[3.5rem]"
          >
            <span className="block">
              Every Offer Is a{" "}
              <span className="green-halo">Decision</span>.
            </span>
            <span className="block whitespace-nowrap">
              Make It an{" "}
              <span className="green-halo">Intelligent</span> One.
            </span>
          </motion.h1>

          <motion.div
            variants={fadeUp}
            initial="hidden"
            animate="visible"
            custom={1}
          >
            <Button
              size="lg"
              onClick={() => navigate("/profile")}
              className="btn-premium px-8 py-6 text-sm font-bold tracking-wide"
            >
              Get Started
              <motion.span
                animate={{ x: [0, 4, 0] }}
                transition={{ duration: 1.2, repeat: Infinity, ease: "easeInOut" }}
                className="ml-2 inline-flex"
              >
                <ArrowRight className="h-4 w-4" />
              </motion.span>
            </Button>
          </motion.div>
        </motion.div>
      </section>

      {/* Features */}
      <section className="py-32 px-6">
        <div className="container mx-auto max-w-5xl">
          <motion.div
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="mb-24 text-center"
          >
            <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">
              What We Actually Analyze
            </h2>
          </motion.div>

          <div className="space-y-32">
            {features.map((feature, i) => {
              const isReversed = i % 2 === 1;
              return (
                <motion.div
                  key={feature.title}
                  initial={{ opacity: 0, y: 32 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true, margin: "-80px" }}
                  transition={{ duration: 0.6, delay: i * 0.1, ease: [0.25, 0.46, 0.45, 0.94] }}
                  className={`grid items-center gap-16 md:grid-cols-2 ${isReversed ? "md:[direction:rtl]" : ""}`}
                >
                  <div className={isReversed ? "md:[direction:ltr]" : ""}>
                    <h3 className="mb-4 text-xl font-semibold tracking-tight">
                      {feature.title}
                    </h3>
                    <p className="text-muted-foreground leading-relaxed whitespace-pre-line text-[15px]">
                      {feature.text}
                    </p>
                  </div>
                  <div className={`rounded-xl border border-border bg-card p-8 ${isReversed ? "md:[direction:ltr]" : ""}`}>
                    <div className="h-48 flex flex-col justify-center">
                      {feature.visual}
                    </div>
                  </div>
                </motion.div>
              );
            })}
          </div>
        </div>
      </section>

      {/* Final CTA */}
      <section className="py-32 px-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="mx-auto max-w-2xl text-center"
        >
          <p className="mb-12 text-2xl font-medium leading-snug tracking-tight text-foreground sm:text-3xl">
            Your career is the largest financial asset you will ever own.
          </p>
          <Button
            size="lg"
            onClick={() => navigate("/profile")}
            className="btn-premium px-8 py-6 text-sm font-medium tracking-wide"
          >
            Get Started
            <ArrowRight className="ml-2 h-4 w-4" />
          </Button>
        </motion.div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border py-8 px-6 text-center text-xs text-muted-foreground">
        © {new Date().getFullYear()} OfferGo
      </footer>
    </div>
  );
};

export default Index;
