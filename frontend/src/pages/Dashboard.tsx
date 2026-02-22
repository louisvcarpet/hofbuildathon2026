import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowRight, FileUp, UserCircle } from "lucide-react";
import Navbar from "@/components/Navbar";
import { Button } from "@/components/ui/button";
import { useProfile } from "@/hooks/use-profile";

const Dashboard = () => {
  const navigate = useNavigate();
  const { profile } = useProfile();

  return (
    <div className="min-h-screen bg-background">
      <Navbar />

      <main className="container mx-auto max-w-5xl px-6 pt-28 pb-16">
        <motion.section
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="mb-8"
        >
          <h1 className="text-3xl font-bold tracking-tight">
            Welcome{profile.name ? `, ${profile.name}` : ""}.
          </h1>
          <p className="mt-2 text-muted-foreground">
            Your account is ready. Start a new offer analysis or update your profile.
          </p>
        </motion.section>

        <section className="grid gap-5 md:grid-cols-2">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45, delay: 0.05 }}
            className="card-elevated p-6"
          >
            <div className="mb-4 inline-flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
              <FileUp className="h-5 w-5 text-primary" />
            </div>
            <h2 className="text-lg font-semibold">Start Offer Analysis</h2>
            <p className="mt-2 text-sm text-muted-foreground">
              Upload one or more offers and get your AI-powered report.
            </p>
            <Button
              onClick={() => navigate("/submit")}
              className="mt-6 glow-primary bg-primary text-primary-foreground hover:bg-primary/90"
            >
              Analyze Offer
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45, delay: 0.1 }}
            className="card-elevated p-6"
          >
            <div className="mb-4 inline-flex h-10 w-10 items-center justify-center rounded-lg bg-secondary">
              <UserCircle className="h-5 w-5 text-muted-foreground" />
            </div>
            <h2 className="text-lg font-semibold">Manage Profile</h2>
            <p className="mt-2 text-sm text-muted-foreground">
              Keep your personal and financial context up to date for better scoring.
            </p>
            <Button variant="outline" onClick={() => navigate("/profile")} className="mt-6">
              Edit Profile
            </Button>
          </motion.div>
        </section>

      </main>
    </div>
  );
};

export default Dashboard;
