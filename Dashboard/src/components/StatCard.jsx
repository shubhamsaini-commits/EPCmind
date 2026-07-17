import { useRef } from "react";
import { useGSAP } from "@gsap/react";
import gsap from "gsap";

/**
 * A single dashboard stat card (e.g. "12,530 Chunks"). Value counts up from
 * zero on mount, easing out as it approaches the target — per design spec.
 *
 * BACKEND NOTE: `value` should come from GET /stats (see api/client.js
 * getStats()). Pass raw numbers here, not pre-formatted strings.
 */
export default function StatCard({ label, value, index = 0 }) {
  const cardRef = useRef(null);
  const numberRef = useRef(null);
  const counter = useRef({ val: 0 });

  useGSAP(
    () => {
      // Staggered fade-up on mount, delayed per card index
      gsap.from(cardRef.current, {
        y: 16,
        opacity: 0,
        duration: 0.5,
        delay: index * 0.08,
        ease: "power2.out",
      });

      // Count-up, slowing near the end (power2.out easing does this naturally)
      gsap.to(counter.current, {
        val: value,
        duration: 1.2,
        delay: index * 0.08 + 0.15,
        ease: "power2.out",
        onUpdate: () => {
          if (numberRef.current) {
            numberRef.current.textContent = Math.round(counter.current.val).toLocaleString();
          }
        },
      });
    },
    { scope: cardRef, dependencies: [value] }
  );

  return (
    <div
      ref={cardRef}
      className="bg-surface border border-border rounded-2xl p-5 flex flex-col gap-1"
    >
      <span ref={numberRef} className="text-3xl font-semibold text-text-primary">
        0
      </span>
      <span className="text-sm text-text-secondary">{label}</span>
    </div>
  );
}
