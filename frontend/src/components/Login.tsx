import { useState, type FormEvent } from "react";
import { HeartPulse, Eye, EyeOff, ShieldCheck, ArrowRight } from "lucide-react";
import { useAuth } from "../context/AuthContext";

export default function Login() {
  const { login, isLoading } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");

    try {
      await login(email.trim(), password);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to sign in. Please try again.",
      );
    }
  }

  return (
    <main className="login-page">
      <section className="login-brand-panel">
        <div className="login-brand">
          <div className="brand-mark">
            <HeartPulse size={27} />
          </div>
          <div>
            <h1>AHENDA</h1>
            <span>HEALTHCARE CONTINUITY</span>
          </div>
        </div>

        <div className="login-message">
          <span className="eyebrow">CONNECTED CARE. CONTINUOUSLY.</span>
          <h2>Every result deserves a journey that leads to care.</h2>
          <p>
            Coordinate screening results, manage follow-ups and help ensure that
            no patient is lost in the transition between care providers.
          </p>
        </div>

        <div className="login-brand-footer">
          <ShieldCheck size={17} />
          <span>Secure healthcare coordination workspace</span>
        </div>
      </section>

      <section className="login-form-panel">
        <div className="login-form-container">
          <div className="login-heading">
            <div className="mobile-brand">
              <div className="brand-mark">
                <HeartPulse size={24} />
              </div>
              <strong>AHENDA</strong>
            </div>

            <span className="eyebrow">WELCOME BACK</span>
            <h2>Sign in to AHENDA</h2>
            <p>Enter your credentials to access your workspace.</p>
          </div>

          <form onSubmit={handleSubmit}>
            <label htmlFor="email">Work email address</label>
            <input
              id="email"
              type="email"
              placeholder="name@organisation.com"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              autoComplete="username"
              required
            />

            <div className="password-label">
              <label htmlFor="password">Password</label>
            </div>

            <div className="password-input">
              <input
                id="password"
                type={showPassword ? "text" : "password"}
                placeholder="Enter your password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                autoComplete="current-password"
                required
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                aria-label={showPassword ? "Hide password" : "Show password"}
              >
                {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>

            {error && (
              <div className="login-error" role="alert">
                {error}
              </div>
            )}

            <button className="login-submit" type="submit" disabled={isLoading}>
              {isLoading ? "Signing in..." : "Sign in to workspace"}
              {!isLoading && <ArrowRight size={17} />}
            </button>
          </form>

          <div className="login-security">
            <ShieldCheck size={16} />
            <span>Your access is protected by AHENDA authentication.</span>
          </div>

          <div className="login-legal">
            AHENDA · No Result Left Behind. No Patient Lost in Transition.
          </div>
        </div>
      </section>
    </main>
  );
}
