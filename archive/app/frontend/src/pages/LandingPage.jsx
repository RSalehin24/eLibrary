import { Link } from "react-router-dom";
import { usePageTitle } from "../hooks/usePageTitle";
import { useSession } from "../hooks/useSession";

export default function LandingPage() {
  usePageTitle("Welcome");
  const { authenticated, user } = useSession();

  return (
    <div className="page-stack">
      <section className="landing-panel landing-create-panel">
        <div className="landing-create-stack">
          <p className="eyebrow">RSalehin24 Library</p>
          <h1>Manage ingestion, review metadata, and keep EPUB creation organized.</h1>
          <p className="landing-lead">
            {authenticated
              ? `${user?.full_name || user?.email}, your workspace is ready.`
              : "Sign in to create books, manage your queue, and work from your saved library."}
          </p>
          <div className="inline-pills">
            {authenticated ? (
              <>
                <Link to="/create" className="primary-button">
                  Open Create Books
                </Link>
                <Link to="/library" className="ghost-button">
                  Open Library
                </Link>
              </>
            ) : (
              <Link to="/login" className="primary-button">
                Sign in
              </Link>
            )}
          </div>
        </div>
      </section>

      <section className="page-grid">
        <article className="detail-card">
          <p className="eyebrow">Create</p>
          <h2>Separate creation workspace</h2>
          <p className="muted-copy">
            Logged-in users now get a dedicated create-books page from the header so submissions and follow-up actions stay in one place.
          </p>
        </article>
        <article className="detail-card">
          <p className="eyebrow">Profile</p>
          <h2>Profile and Two-Factor</h2>
          <p className="muted-copy">
            Use the profile page to update your name, finish two-factor setup, and turn it on or off when the account allows it.
          </p>
        </article>
      </section>
    </div>
  );
}
