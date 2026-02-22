const DEMO_SESSION_KEY = "offergo-demo-user";

export function loginDemoUser() {
  const profileData = {
    name: "Bob Wang",
    city: "New York",
    country: "USA",
    nationality: "Chinese",
    monthlyExpenses: "3200",
    ownedAsset: "40000",
    debts: "10000 @ 5%",
    resumeName: "resume_bob_wang.pdf",
    completed: true,
  };
  localStorage.setItem("offergo-profile", JSON.stringify(profileData));
  sessionStorage.setItem(DEMO_SESSION_KEY, "demo-bob");
}

export function logoutDemoUser() {
  localStorage.removeItem("offergo-profile");
  sessionStorage.removeItem("offergo-submission");
  sessionStorage.removeItem("offergo-demo-analysis");
  sessionStorage.removeItem(DEMO_SESSION_KEY);
}

export function getActiveDemoUserId(): string | null {
  return sessionStorage.getItem(DEMO_SESSION_KEY);
}
