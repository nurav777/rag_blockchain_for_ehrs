export default function LoadingState({ label = "Loading…", fullPage = false }) {
  return (
    <div className={fullPage ? "loading-state loading-state--page" : "loading-state"}>
      <span className="spinner" aria-hidden="true" />
      <span>{label}</span>
    </div>
  );
}
