import {
  ArrowRight, BarChart3, CheckCircle2, Database, FileSearch, Fingerprint,
  Menu, MessageSquareText, Moon, ShieldCheck, Sparkles, Sun, X,
} from "lucide-react";
import { useState } from "react";
import { useTheme } from "../lib/theme";

const workflow = [
  ["01", "Describe the purchase", "Share the model, specifications, quantity, condition, and supplier quote in plain English."],
  ["02", "Review the evidence", "Procura AI normalizes the request and compares it with relevant, recent market observations."],
  ["03", "Make the decision", "Get an explainable assessment, confidence level, risks, and the checks to complete before buying."],
];

const capabilities = [
  { icon: FileSearch, title: "Quote intelligence", copy: "Turn an unstructured supplier quote into a consistent, reviewable procurement request." },
  { icon: Database, title: "Market evidence", copy: "Compare like with like using product identity, condition, specifications, freshness, and source quality." },
  { icon: BarChart3, title: "Explainable assessment", copy: "See price position, match quality, confidence limits, and the reasoning behind every recommendation." },
  { icon: MessageSquareText, title: "Contextual follow-up", copy: "Ask why, explore alternatives, and clarify missing information without restarting the analysis." },
];

export function LandingPage() {
  const [menuOpen, setMenuOpen] = useState(false);
  const { theme, toggleTheme } = useTheme();

  return (
    <div className="landing-shell">
      <header className="landing-nav">
        <a className="landing-brand" href="/" aria-label="Procura AI home">
          <span className="brand-mark"><Sparkles size={18} /></span>
          <span><strong>Procura AI</strong><small>Procurement intelligence</small></span>
        </a>
        <nav className={`landing-links ${menuOpen ? "landing-links-open" : ""}`} aria-label="Main navigation">
          <a href="#how-it-works" onClick={() => setMenuOpen(false)}>How it works</a>
          <a href="#capabilities" onClick={() => setMenuOpen(false)}>Capabilities</a>
          <a href="#trust" onClick={() => setMenuOpen(false)}>Trust</a>
          <a className="nav-cta" href="/app">Open assistant <ArrowRight size={15} /></a>
        </nav>
        <div className="landing-actions">
          <button className="icon-button theme-toggle" onClick={toggleTheme} aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}>
            {theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
          </button>
          <button className="icon-button landing-menu" onClick={() => setMenuOpen((open) => !open)} aria-label="Toggle navigation">
            {menuOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>
      </header>

      <main>
        <section className="landing-hero">
          <div className="hero-glow hero-glow-one" /><div className="hero-glow hero-glow-two" />
          <div className="hero-copy">
            <span className="hero-kicker"><i /> Evidence before decisions</span>
            <h1>Buy business laptops with <em>clarity.</em></h1>
            <p>Procura AI turns supplier quotes into evidence-backed recommendations—so teams can compare pricing, understand risk, and defend every purchasing decision.</p>
            <div className="hero-actions">
              <a className="primary-cta" href="/app">Analyze a quote <ArrowRight size={17} /></a>
              <a className="secondary-cta" href="#how-it-works">See how it works</a>
            </div>
            <div className="hero-trust">
              <span><CheckCircle2 size={14} /> Explainable results</span>
              <span><CheckCircle2 size={14} /> Source-aware evidence</span>
              <span><CheckCircle2 size={14} /> Human review built in</span>
            </div>
          </div>

          <div className="hero-product" aria-label="Example Procura AI assessment">
            <div className="product-window-bar"><span /><span /><span /><small>Procura AI · Quote review</small></div>
            <div className="product-preview">
              <div className="preview-heading"><div><span>Assessment</span><strong>Dell Latitude 5440</strong></div><span className="preview-pill">Review advised</span></div>
              <div className="preview-metrics">
                <div><small>Quote position</small><strong>Above range</strong><span>Verify configuration</span></div>
                <div><small>Evidence match</small><strong>Strong</strong><span>Recent comparables</span></div>
                <div><small>Confidence</small><strong>Moderate</strong><span>More evidence helps</span></div>
              </div>
              <div className="preview-chart">
                <div className="chart-labels"><span>Observed range</span><strong>Quoted price</strong></div>
                <div className="chart-track"><span className="chart-range" /><i /></div>
                <div className="chart-scale"><span>Lower</span><span>Market median</span><span>Higher</span></div>
              </div>
              <div className="preview-note"><ShieldCheck size={18} /><span><strong>Decision support, not guesswork.</strong> Verify warranty and exact processor generation before approval.</span></div>
            </div>
          </div>
        </section>

        <section className="signal-strip" aria-label="Product principles">
          <span>Built for thoughtful procurement</span><i /><span>Structured market comparison</span><i /><span>Transparent confidence</span><i /><span>Conversation with context</span>
        </section>

        <section className="landing-section workflow-section" id="how-it-works">
          <div className="section-heading"><span className="section-kicker">A clearer workflow</span><h2>From supplier quote to informed decision.</h2><p>Procura AI keeps the workflow conversational while making the underlying assessment structured and reviewable.</p></div>
          <div className="workflow-grid">
            {workflow.map(([number, title, copy]) => <article key={number}><span>{number}</span><h3>{title}</h3><p>{copy}</p></article>)}
          </div>
        </section>

        <section className="landing-section capabilities-section" id="capabilities">
          <div className="section-heading split-heading"><div><span className="section-kicker">Practical intelligence</span><h2>More than a chatbot.</h2></div><p>Every layer is designed to make laptop procurement easier to understand, compare, and explain to stakeholders.</p></div>
          <div className="capability-grid">
            {capabilities.map(({ icon: Icon, title, copy }) => <article key={title}><span><Icon size={20} /></span><h3>{title}</h3><p>{copy}</p><i><ArrowRight size={15} /></i></article>)}
          </div>
        </section>

        <section className="landing-section trust-section" id="trust">
          <div className="trust-visual"><Fingerprint size={46} /><span>Evidence trail</span><strong>Know what supports the answer.</strong></div>
          <div className="trust-copy"><span className="section-kicker">Trust by design</span><h2>Recommendations you can challenge.</h2><p>Procura AI separates verified observations from generated explanation. When evidence is weak, stale, or incomplete, the product says so instead of manufacturing certainty.</p><ul><li><CheckCircle2 size={16} /> Source and freshness context</li><li><CheckCircle2 size={16} /> Explicit confidence limitations</li><li><CheckCircle2 size={16} /> Human feedback and calibration</li></ul></div>
        </section>

        <section className="landing-cta"><span className="section-kicker">Ready when you are</span><h2>Bring the quote. Leave with clarity.</h2><p>Start with a supplier quote or simply ask what laptop specifications fit your team.</p><a className="primary-cta" href="/app">Open Procura AI <ArrowRight size={17} /></a></section>
      </main>

      <footer className="landing-footer"><a className="landing-brand" href="/"><span className="brand-mark"><Sparkles size={16} /></span><span><strong>Procura AI</strong><small>Evidence-backed procurement</small></span></a><p>Decision support for smarter laptop purchasing.</p><a href="/app">Launch assistant <ArrowRight size={14} /></a></footer>
    </div>
  );
}
