import { useState, useEffect } from "react";

function generateWorkspaceCode() {
  // STEP: Random 6-character code banata hai.
  // WHY: "Create Workspace" dabane par user ko ek unique, share-karne-layak
  // code milna chahiye — jaise "WS-7F3A9B".
  const chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
  let code = "";
  for (let i = 0; i < 6; i++) {
    code += chars[Math.floor(Math.random() * chars.length)];
  }
  return `WS-${code}`;
}

export default function WorkspaceGate({ children }) {
  const [workspaceId, setWorkspaceId] = useState(() => localStorage.getItem("workspace_id"));
  const [joinCode, setJoinCode] = useState("");
  const [createdCode, setCreatedCode] = useState(null);

  const handleCreate = async () => {
    const newCode = generateWorkspaceCode();
    // STEP: Backend ko call karke owner_key generate karwate hain.
    // // WHY: Sirf yehi user (jo Create dabata hai) ke paas owner_key
     // // hogi — isliye backend call yahi, "Join" wale flow mein nahi.
    try {
        const res = await fetch(`${import.meta.env.VITE_API_BASE || "http://localhost:8000"}/workspace/create`, {
            method: "POST",
            headers: { "X-Workspace-Id": newCode },
        });
        const data = await res.json();

        localStorage.setItem("workspace_id", newCode);
        localStorage.setItem("owner_key", data.owner_key);   // STEP: sirf creator ke paas save hoga
        setCreatedCode(newCode);
    } catch (err) {
        alert("Failed to create workspace. Please check if the backend is running.");
    }
};


  const handleJoin = () => {
    const trimmed = joinCode.trim().toUpperCase();
    if (!trimmed) return;
    localStorage.setItem("workspace_id", trimmed);
    setWorkspaceId(trimmed);
  };

  const handleContinue = () => {
    setWorkspaceId(createdCode);
  };

  // STEP: Agar workspace_id already localStorage mein hai (dubara visit),
  // seedha app dikhao, ye screen skip karo.
  if (workspaceId) {
    return children;
  }

  // STEP: Agar abhi "Create" dabaya hai aur code generate ho chuka hai,
  // use dikhao taaki user copy/share kar sake.
  if (createdCode) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-canvas px-4">
        <div className="max-w-sm w-full bg-surface border border-border rounded-2xl p-6 text-center">
          <p className="text-text-secondary text-sm mb-2">Your workspace code</p>
          <p className="text-2xl font-medium text-accent mb-4 tracking-wider">{createdCode}</p>
          <p className="text-text-muted text-xs mb-6">
            Share this code with your team — anyone who enters it will see the same documents.
          </p>
          <button
            onClick={handleContinue}
            className="w-full px-4 py-2.5 rounded-xl bg-accent text-white text-sm hover:bg-accent/90 transition-colors"
          >
            Continue
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-canvas px-4">
      <div className="max-w-sm w-full bg-surface border border-border rounded-2xl p-6">
        <h2 className="text-lg font-medium text-text-primary mb-1">Welcome to EPCmind</h2>
        <p className="text-text-secondary text-sm mb-6">Create a new workspace or join your team's existing one.</p>

        <button
          onClick={handleCreate}
          className="w-full px-4 py-2.5 rounded-xl bg-accent text-white text-sm hover:bg-accent/90 transition-colors mb-4"
        >
          Create New Workspace
        </button>

        <div className="flex items-center gap-2 mb-4">
          <div className="flex-1 h-px bg-border" />
          <span className="text-text-muted text-xs">or</span>
          <div className="flex-1 h-px bg-border" />
        </div>

        <input
          value={joinCode}
          onChange={(e) => setJoinCode(e.target.value)}
          placeholder="Enter workspace code (e.g. WS-7F3A9B)"
          className="w-full bg-surface-2 border border-border rounded-xl px-4 py-2.5 text-sm text-text-primary placeholder:text-text-muted mb-3 focus:outline-none focus:border-accent/50"
        />
        <button
          onClick={handleJoin}
          disabled={!joinCode.trim()}
          className="w-full px-4 py-2.5 rounded-xl border border-border text-text-primary text-sm disabled:opacity-40 hover:border-accent/50 transition-colors"
        >
          Join Workspace
        </button>
      </div>
    </div>
  );
}