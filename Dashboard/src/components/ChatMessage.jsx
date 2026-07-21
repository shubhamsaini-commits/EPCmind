import { useRef, useState } from "react";
import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import ReactMarkdown from "react-markdown";
import DocumentBadge from "./DocumentBadge";
// we try to add new helper function which help to show 
// or don't show source file if question is not completely to document
// ______________________________________________________________________
function hasNoConfidentAnswer(text) {
  const lowerText = text.toLowerCase();
  return (
    lowerText.includes("does not contain") ||
    lowerText.includes("doesn't contain") ||
    lowerText.includes("no information") ||
    lowerText.includes("not mentioned") ||
    lowerText.includes("cannot find")
  );
}
//________________________________________________________________________
/**
 * A single chat message. `role` is "user" or "ai".
 * `sources` (AI messages only) is the array your FastAPI /ask endpoint
 * should return alongside `answer` — see api/client.js askQuestion() docs.
 * Each source: { filename, document_type, text, distance }
 */
export default function ChatMessage({ role, text, sources = [] }) {
  const msgRef = useRef(null);

  useGSAP(
    () => {
      // Slide up from bottom + fade in on entry
      gsap.from(msgRef.current, {
        y: 15,
        opacity: 0,
        duration: 0.4,
        ease: "power2.out",
      });
    },
    { scope: msgRef }
  );

  const isUser = role === "user";

  return (
    <div ref={msgRef} className={`flex ${isUser ? "justify-end" : "justify-start"} mb-4`}>
      <div className={`max-w-[75%] ${isUser ? "" : "w-full"}`}>
        <div
          className={
            isUser
              ? "bg-accent-soft border border-accent/30 text-text-primary rounded-2xl rounded-br-sm px-4 py-2.5"
              : "bg-transparent border border-border text-text-primary rounded-2xl rounded-bl-sm px-4 py-3"
          }
        >
          {isUser ? (
            <p className="text-sm leading-relaxed whitespace-pre-wrap">{text}</p>
          ) : (
            <div
              className="text-sm leading-relaxed prose prose-invert prose-sm max-w-none
                prose-p:my-1.5 prose-ul:my-1.5 prose-ol:my-1.5 prose-li:my-0.5
                prose-headings:text-text-primary prose-headings:font-medium prose-headings:mt-2 prose-headings:mb-1
                prose-strong:text-text-primary prose-strong:font-semibold
                prose-code:text-accent prose-code:bg-surface-2 prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-code:text-xs"
            >
              <ReactMarkdown>{text}</ReactMarkdown>
            </div>
          )}
        </div>

        {!isUser && sources.length > 0 && (
          hasNoConfidentAnswer(text) ? (
            <div className="mt-2 ml-1 px-3 py-1.5 rounded-lg bg-surface-2 border border-border-soft text-xs text-text-muted italic">
              No confident match found in the uploaded documents.
            </div>
          ) : (
            <div className="flex flex-wrap gap-2 mt-2 ml-1">
              {sources.map((src, i) => (
                <SourceChip key={i} source={src} index={i} />
              ))}
            </div>
          )
        )}
      </div>
    </div>
  );
}

/**
 * Pill-shaped citation chip. Expands to show the retrieved chunk text
 * so judges can verify the AI actually grounded its answer in a real
 * document — this is a strong trust-builder in a live demo.
 */

function getConfidenceLevel(distance) {
  // if (distance < 0.5) return { label: "High", color: "text-green-500 bg-green-500/10 border-green-500/30" };
  // if (distance < 1.0) return { label: "Medium", color: "text-yellow-500 bg-yellow-500/10 border-yellow-500/30" };
  // return { label: "Low", color: "text-red-500 bg-red-500/10 border-red-500/30" };
  if (distance < 0.65) return { label: "High", color: "text-green-500 bg-green-500/10 border-green-500/30" };
  if (distance < 0.85) return { label: "Medium", color: "text-yellow-500 bg-yellow-500/10 border-yellow-500/30" };
  return { label: "Low", color: "text-red-500 bg-red-500/10 border-red-500/30" };

}

function SourceChip({ source, index }) {
  const [open, setOpen] = useState(false);
  const bodyRef = useRef(null);
  const confidence = getConfidenceLevel(source.distance);
  // console.log("Distance value:",source.distance);
  useGSAP(
    () => {
      if (!bodyRef.current) return;
      if (open) {
        gsap.fromTo(
          bodyRef.current,
          { height: 0, opacity: 0 },
          { height: "auto", opacity: 1, duration: 0.3, ease: "power2.out" }
        );
      } else {
        gsap.to(bodyRef.current, { height: 0, opacity: 0, duration: 0.2, ease: "power2.in" });
      }
    },
    { dependencies: [open] }
  );
    
  return (
    <div className="flex flex-col">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-1.5 px-3 py-1 rounded-full border border-border bg-surface text-xs text-text-secondary hover:text-text-primary transition-colors"
      >
        Source {index + 1}
        <DocumentBadge type={source.document_type} />
        <span className={`px-1.5 py-0.5 rounded-full text-[10px] border ${confidence.color}`}>
          {confidence.label}
        </span>
      </button>
      <div ref={bodyRef} className="overflow-hidden" style={{ height: 0, opacity: 0 }}>
        <div className="mt-1.5 px-3 py-2 rounded-lg bg-surface-2 border border-border-soft text-xs text-text-secondary">
          <div className="text-text-muted mb-1">{source.filename}</div>
          {source.text}
        </div>
      </div>
    </div>
  );
}