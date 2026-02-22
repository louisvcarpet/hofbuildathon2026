import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { LogOut, User, ChevronDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useProfile } from "@/hooks/use-profile";
import { logoutDemoUser } from "@/lib/demo-users";
import DemoLoginModal from "@/components/DemoLoginModal";

const Navbar = () => {
  const navigate = useNavigate();
  const { profile } = useProfile();
  const [loginOpen, setLoginOpen] = useState(false);

  const handleLogout = () => {
    logoutDemoUser();
    window.location.href = "/";
  };

  const initials = profile.name
    ? profile.name
        .split(" ")
        .map((n) => n[0])
        .join("")
        .toUpperCase()
    : "U";

  return (
    <>
      <nav className="fixed top-0 left-0 right-0 z-50 bg-background/70 backdrop-blur-lg">
        <div className="container mx-auto flex h-16 items-center justify-between px-6">
          <button
            onClick={() => navigate(profile.completed ? "/dashboard" : "/")}
            className="text-lg font-semibold tracking-tight text-foreground"
          >
            Offer<span className="text-primary">Go</span>
          </button>

          <div className="flex items-center gap-3">
            {profile.completed ? (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <button className="flex items-center gap-2.5 rounded-full border border-border bg-card px-3 py-1.5 text-sm font-medium transition-colors hover:bg-muted focus:outline-none">
                    <Avatar className="h-7 w-7">
                      <AvatarFallback className="bg-primary/10 text-xs font-semibold text-primary">
                        {initials}
                      </AvatarFallback>
                    </Avatar>
                    <span className="hidden sm:inline text-foreground">{profile.name || "User"}</span>
                    <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
                  </button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-48">
                  <DropdownMenuItem
                    onClick={() => navigate("/profile")}
                    className="cursor-pointer"
                  >
                    <User className="mr-2 h-4 w-4" />
                    Profile
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem
                    onClick={handleLogout}
                    className="cursor-pointer text-destructive focus:text-destructive"
                  >
                    <LogOut className="mr-2 h-4 w-4" />
                    Log Out
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            ) : (
              <>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setLoginOpen(true)}
                  className="btn-login text-muted-foreground hover:text-foreground hover:bg-transparent"
                >
                  Log In
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => navigate("/profile")}
                  className="btn-signup"
                >
                  Sign Up
                </Button>
              </>
            )}
          </div>
        </div>
      </nav>

      <DemoLoginModal open={loginOpen} onOpenChange={setLoginOpen} />
    </>
  );
};

export default Navbar;
