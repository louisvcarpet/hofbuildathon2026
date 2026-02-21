import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";

const MESSAGES = [
  "Extracting compensation structure…",
  "Interpreting equity terms…",
  "Evaluating risk exposure…",
  "Aligning with your priorities…",
  "Generating structured insights…",
];

const Analyzing = () => {
  const navigate = useNavigate();
  const [msgIndex, setMsgIndex] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setMsgIndex((i) => (i + 1) % MESSAGES.length);
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const timeout = setTimeout(() => {
      navigate("/results");
    }, 8000);
    return () => clearTimeout(timeout);
  }, [navigate]);

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-background px-6">
      <div className="pointer-events-none absolute h-[400px] w-[400px] rounded-full bg-primary/5 blur-[100px]" />

      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5 }}
        className="relative z-10 flex flex-col items-center text-center"
      >
        <div className="relative mb-10">
          <div className="h-16 w-16 rounded-full border-2 border-border" />
          <div className="absolute inset-0 h-16 w-16 animate-spin rounded-full border-2 border-transparent border-t-primary" style={{ animationDuration: "1.5s" }} />
        </div>

        <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">
          Analyzing Your Offer Document…
        </h1>
        <p className="mt-4 max-w-md text-muted-foreground">
          Evaluating market benchmarks, financial impact, risk exposure, and long-term opportunity cost.
        </p>

        <motion.p
          key={msgIndex}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.4 }}
          className="mt-8 text-sm font-mono text-primary"
        >
          {MESSAGES[msgIndex]}
        </motion.p>
      </motion.div>
    </div>
  );
};

export default Analyzing;
