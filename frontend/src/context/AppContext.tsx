// src/context/AppContext.tsx
'use client';

import React, { createContext, useContext, useEffect, useState } from "react";

interface AppContextType {
  verifiedUser: boolean;
  setVerifiedUser: React.Dispatch<React.SetStateAction<boolean>>;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

// This will only store the context for the session. 
// If the user closes the app, then it will have the user sign in again

export const AppProvider = ({ children }: { children: React.ReactNode }) => {
  const [verifiedUser, setVerifiedUser] = useState(false);

  // On mount load from sessionStorage
  useEffect(() => {
    const stored = sessionStorage.getItem("verifiedUser");
    if (stored === "true") {
      setVerifiedUser(true);
    }
  }, []);

  // Whenever verifiedUser changes store it
  useEffect(() => {
    sessionStorage.setItem("verifiedUser", String(verifiedUser));
  }, [verifiedUser]);

  return (
    <AppContext.Provider value={{ verifiedUser, setVerifiedUser }}>
      {children}
    </AppContext.Provider>
  );
};

export const useAppContext = () => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error("useAppContext must be used inside AppProvider");
  }
  return context;
};
