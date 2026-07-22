import axios from "axios";

/**
 * =============================================================
 * BACKEND DEVELOPER: READ THIS FILE FIRST
 * =============================================================
 * This is the ONLY file in the entire frontend that makes HTTP
 * calls to FastAPI. Every component below imports functions from
 * here — none of them use axios/fetch directly. Same principle
 * as your llm_client.py: one place to change if the API shape
 * changes, nothing else in the app needs to know.
 *
 * Update API_BASE to match wherever uvicorn is running.
 * CORS: your FastAPI app needs to allow this origin (see the
 * CORSMiddleware snippet you already have from earlier).
 * =============================================================
 */

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

const client = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
});

// STEP: Naya interceptor add kiya.
// WHY: Har request jaane se pehle, ye automatically localStorage se
// workspace_id nikal ke 'X-Workspace-Id' header mein daal dega —
// taaki humein har API call mein manually ye likhna na pade.
client.interceptors.request.use((config) => {
  const workspaceId = localStorage.getItem("workspace_id");
  if (workspaceId) {
    config.headers["X-Workspace-Id"] = workspaceId;
  }
  return config;
});

/**
 * ---- 1. ASK DOCUMENTS (RAG Q&A) ----
 */
export const askQuestion = (question, documentType = null) =>
  client.post("/ask", { question, document_type: documentType });

/**
 * ---- 2. COMPLIANCE CHECK ----
 */
export const runComplianceCheck = (payload = {}) =>
  client.post("/compliance-check", payload);

export const getLastComplianceCheck = () => client.get("/compliance-check");

/**
 * ---- 3. DOCUMENT UPLOAD ----
 */
export const uploadDocument = (file, onProgress) => {
  const formData = new FormData();
  formData.append("file", file);
  return client.post("/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    onUploadProgress: (evt) => {
      if (onProgress && evt.total) {
        onProgress(Math.round((evt.loaded / evt.total) * 100));
      }
    },
  });
};

// ___________________________________________________________________
// Adding Delete function
export async function deleteDocument(filename) {
  const workspaceId = localStorage.getItem("workspace_id");
  const ownerKey = localStorage.getItem("owner_key") || "";   // STEP: naya

  const res = await fetch(`${API_BASE}/documents/${encodeURIComponent(filename)}`, {
    method: "DELETE",
    headers: {
      "X-Workspace-Id": workspaceId,
      "X-Owner-Key": ownerKey,   // STEP: naya, WHY: backend isse verify karega
    },
  });
  return { data: await res.json() };
}
//_____________________________________________________________________

/**
 * ---- 4. LIST DOCUMENTS ----
 */
export const getDocuments = () => client.get("/documents");

/**
 * ---- 5. DASHBOARD STATS (Home page) ----
 */
export const getStats = () => client.get("/stats");

/**
 * ---- 6. OPEN/DOWNLOAD A DOCUMENT ----
 * STEP: Naya function.
 * WHY: File ko fetch karke (workspace header ke saath), browser mein
 * naye tab mein khulwata hai. Seedha <a href> se nahi ho sakta tha
 * kyunki custom headers bhejni zaroori hain.
 */
export async function openDocument(filename) {
  const workspaceId = localStorage.getItem("workspace_id");

  const res = await fetch(`${API_BASE}/documents/${encodeURIComponent(filename)}/file`, {
    headers: { "X-Workspace-Id": workspaceId },
  });

  if (!res.ok) {
    throw new Error("Failed to open file");
  }

  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  window.open(url, "_blank");
}

export default client;