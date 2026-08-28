import { SignIn, SignUp } from "@clerk/react";
import { ArrowLeft, Sparkles } from "lucide-react";

export function AuthPage({ mode }: { mode: "sign-in" | "sign-up" }) {
  const signingIn = mode === "sign-in";
  return (
    <main className="auth-shell">
      <a className="auth-back" href="/"><ArrowLeft size={15} /> Back to Procura AI</a>
      <section className="auth-story">
        <div className="brand-mark"><Sparkles size={20} /></div>
        <span className="section-kicker">Your private workspace</span>
        <h1>{signingIn ? "Welcome back." : "Start making clearer laptop decisions."}</h1>
        <p>Your conversations and analyses stay connected to your account, so you can return to the evidence and continue where you stopped.</p>
        <div className="auth-points"><span>Protected conversation history</span><span>User-owned analysis records</span><span>Secure managed authentication</span></div>
      </section>
      <section className="auth-panel">
        {signingIn ? (
          <SignIn routing="path" path="/sign-in" signUpUrl="/sign-up" fallbackRedirectUrl="/app" />
        ) : (
          <SignUp routing="path" path="/sign-up" signInUrl="/sign-in" fallbackRedirectUrl="/app" />
        )}
      </section>
    </main>
  );
}
