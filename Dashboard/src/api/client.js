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
  timeout: 30000, // embedding + LLM calls can take a few seconds — don't set this too low
  withCredentials: true, // STEP: naya option add kiya
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
  const res = await fetch(`${API_BASE}/documents/${encodeURIComponent(filename)}`, {
    method: "DELETE",
    credentials: "include", // STEP: naya option add kiya
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

export default client;