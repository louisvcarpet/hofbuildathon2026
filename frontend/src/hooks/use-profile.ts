import { useState, useEffect, useCallback } from "react";

export interface ProfileData {
  name: string;
  city: string;
  country: string;
  nationality: string;
  monthlyExpenses: string;
  ownedAsset: string;
  debts: string;
  resumeName: string | null;
  completed: boolean;
}

const STORAGE_KEY = "offergo-profile";

const emptyProfile: ProfileData = {
  name: "",
  city: "",
  country: "",
  nationality: "",
  monthlyExpenses: "",
  ownedAsset: "",
  debts: "",
  resumeName: null,
  completed: false,
};

function loadProfile(): ProfileData {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return JSON.parse(raw);
  } catch {}
  return { ...emptyProfile };
}

export function useProfile() {
  const [profile, setProfile] = useState<ProfileData>(loadProfile);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(profile));
  }, [profile]);

  const updateProfile = useCallback((patch: Partial<ProfileData>) => {
    setProfile((prev) => {
      const next = { ...prev, ...patch };
      localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      return next;
    });
  }, []);

  const completeProfile = useCallback(() => {
    setProfile((prev) => {
      const next = { ...prev, completed: true };
      localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      return next;
    });
  }, []);

  return { profile, updateProfile, completeProfile };
}
