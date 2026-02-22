import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Check, Save } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useProfile } from "@/hooks/use-profile";
import Navbar from "@/components/Navbar";

const ProfileSetup = () => {
  const navigate = useNavigate();
  const { profile, updateProfile, completeProfile } = useProfile();
  const isEditMode = profile.completed;

  const handleComplete = () => {
    completeProfile();
    navigate("/dashboard");
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Nav */}
      <Navbar />

      <div className="container mx-auto max-w-2xl px-6 pt-28 pb-16">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="space-y-10"
        >
          <div>
            <h1 className="text-3xl font-bold tracking-tight">
              {isEditMode ? "Edit Your Profile" : "Create Your OfferGo Profile"}
            </h1>
            <p className="mt-2 text-muted-foreground">
              {isEditMode ? "Update your information below." : "This profile personalizes your evaluation."}
            </p>
          </div>

          {/* Account */}
          {!isEditMode && (
            <section className="card-elevated p-6 space-y-5">
              <h2 className="text-lg font-semibold">Account</h2>
              <div className="grid gap-5 sm:grid-cols-2">
                <div className="space-y-1.5 sm:col-span-2">
                  <Label>Email</Label>
                  <Input type="email" placeholder="e.g. alex@example.com" value={profile.email} onChange={(e) => updateProfile({ email: e.target.value })} />
                </div>
                <div className="space-y-1.5 sm:col-span-2">
                  <Label>Password</Label>
                  <Input type="password" placeholder="Create a password" value={profile.password} onChange={(e) => updateProfile({ password: e.target.value })} />
                </div>
              </div>
            </section>
          )}

          {/* Personal */}
          <section className="card-elevated p-6 space-y-5">
            <h2 className="text-lg font-semibold">Personal</h2>
            <div className="grid gap-5 sm:grid-cols-2">
              <div className="space-y-1.5 sm:col-span-2">
                <Label>Name</Label>
                <Input placeholder="e.g. Alex Johnson" value={profile.name} onChange={(e) => updateProfile({ name: e.target.value })} />
              </div>
              <div className="space-y-1.5">
                <Label>City</Label>
                <Input placeholder="e.g. New York" value={profile.city} onChange={(e) => updateProfile({ city: e.target.value })} />
              </div>
              <div className="space-y-1.5">
                <Label>Country</Label>
                <Input placeholder="e.g. United States" value={profile.country} onChange={(e) => updateProfile({ country: e.target.value })} />
              </div>
              <div className="space-y-1.5">
                <Label>Nationality</Label>
                <Input placeholder="e.g. American" value={profile.nationality} onChange={(e) => updateProfile({ nationality: e.target.value })} />
              </div>
            </div>
          </section>

          {/* Financial */}
          <section className="card-elevated p-6 space-y-5">
            <h2 className="text-lg font-semibold">Financial</h2>
            <div className="grid gap-5 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label>Monthly Expenses</Label>
                <Input type="number" placeholder="e.g. 4500" value={profile.monthlyExpenses} onChange={(e) => updateProfile({ monthlyExpenses: e.target.value })} />
              </div>
              <div className="space-y-1.5">
                <Label>Owned Assets (value)</Label>
                <Input type="number" placeholder="e.g. 50000" value={profile.ownedAsset} onChange={(e) => updateProfile({ ownedAsset: e.target.value })} />
              </div>
              <div className="space-y-1.5 sm:col-span-2">
                <Label>Debts + Interest Rate</Label>
                <Input placeholder="e.g. 20000 @ 5.5%" value={profile.debts} onChange={(e) => updateProfile({ debts: e.target.value })} />
              </div>
            </div>
          </section>

          <div className="flex justify-end">
            <Button onClick={handleComplete} className="glow-primary bg-primary text-primary-foreground hover:bg-primary/90 px-8">
              {isEditMode ? (
                <><Save className="mr-2 h-4 w-4" /> Save Changes</>
              ) : (
                <><Check className="mr-2 h-4 w-4" /> Complete</>
              )}
            </Button>
          </div>
        </motion.div>
      </div>
    </div>
  );
};

export default ProfileSetup;
