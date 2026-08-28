import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { ClerkProvider, RedirectToSignIn, Show } from "@clerk/react";
import App from "./App";
import { LandingPage } from "./components/LandingPage";
import { AuthPage } from "./components/AuthPage";
import "./index.css";

const publishableKey = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY;
const path = window.location.pathname;

function Routes() {
  if (path === "/sign-in" || path.startsWith("/sign-in/")) return <AuthPage mode="sign-in" />;
  if (path === "/sign-up" || path.startsWith("/sign-up/")) return <AuthPage mode="sign-up" />;
  if (path === "/app" || path.startsWith("/app/")) {
    return <><Show when="signed-in"><App /></Show><Show when="signed-out"><RedirectToSignIn /></Show></>;
  }
  return <LandingPage />;
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    {publishableKey ? (
      <ClerkProvider publishableKey={publishableKey} signInUrl="/sign-in" signUpUrl="/sign-up" signInFallbackRedirectUrl="/app" signUpFallbackRedirectUrl="/app" afterSignOutUrl="/">
        <Routes />
      </ClerkProvider>
    ) : <div className="auth-config-error"><strong>Authentication setup required</strong><span>Add VITE_CLERK_PUBLISHABLE_KEY to start Procura AI.</span></div>}
  </StrictMode>,
);
