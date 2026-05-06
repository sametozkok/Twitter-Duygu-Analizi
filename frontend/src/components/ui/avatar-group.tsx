"use client";

import { useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";

export interface AvatarGroupProps {
  avatars: { src: string; alt?: string; label?: string }[];
  maxVisible?: number;
  size?: number;
  overlap?: number;
  value?: number;
  onChange?: (idx: number) => void;
}

const AvatarGroup = ({
  avatars,
  maxVisible = 5,
  size = 40,
  overlap = 14,
  value,
  onChange,
}: AvatarGroupProps) => {
  const [open, setOpen] = useState(false);
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);

  const visibleAvatars = avatars.slice(0, maxVisible);
  const extraCount = avatars.length - maxVisible;

  const containerWidth = useMemo(() => {
    const count = Math.max(1, visibleAvatars.length + (extraCount > 0 ? 1 : 0));
    const closed = size + (count - 1) * (size - overlap);
    const opened = count * size + (count - 1) * 8;
    return { closed, opened };
  }, [extraCount, overlap, size, visibleAvatars.length]);

  return (
    <button
      type="button"
      className="flex items-center"
      style={{ width: open ? containerWidth.opened : containerWidth.closed }}
      onClick={() => setOpen((v) => !v)}
      aria-label="Channel avatars"
    >
      <div className="flex">
        {visibleAvatars.map((avatar, idx) => {
          const isHovered = hoveredIdx === idx;
          const isSelected = typeof value === "number" ? value === idx : false;
          const marginLeft = idx === 0 ? 0 : open ? 8 : -overlap;

          return (
            <div
              key={idx}
              className="relative rounded-full bg-background border border-white/10"
              style={{
                width: size,
                height: size,
                zIndex: isHovered ? 100 : visibleAvatars.length - idx,
                marginLeft,
                transition:
                  "margin-left 220ms cubic-bezier(0.16,1,0.3,1), transform 220ms cubic-bezier(0.16,1,0.3,1), box-shadow 220ms cubic-bezier(0.16,1,0.3,1), border-color 220ms cubic-bezier(0.16,1,0.3,1)",
                transform: isHovered ? "translateY(-4px)" : "translateY(0)",
                boxShadow: isSelected
                  ? "0 0 0 3px rgba(29,155,240,0.35)"
                  : undefined,
                borderColor: isSelected ? "rgba(29,155,240,0.6)" : undefined,
              }}
              onMouseEnter={() => setHoveredIdx(idx)}
              onMouseLeave={() => setHoveredIdx(null)}
              onClick={(e) => {
                e.stopPropagation();
                onChange?.(idx);
                setOpen(false);
              }}
            >
              <img
                src={avatar.src}
                alt={avatar.alt || `Avatar ${idx + 1}`}
                width={size}
                height={size}
                className="rounded-full object-cover"
                draggable={false}
              />
              <AnimatePresence>
                {isHovered && avatar.label && (
                  <motion.div
                    key="tooltip"
                    initial={{ x: "-50%", y: 10, opacity: 0, scale: 0.7 }}
                    animate={{ x: "-50%", y: 0, opacity: 1, scale: 1 }}
                    exit={{ x: "-50%", y: 10, opacity: 0, scale: 0.7 }}
                    transition={{ type: "spring", stiffness: 400, damping: 24 }}
                    className="absolute z-50 px-2 py-1 bg-primary text-primary-foreground text-xs rounded shadow-lg whitespace-nowrap pointer-events-none font-semibold"
                    style={{ top: -size * 0.8, left: "50%" }}
                  >
                    {avatar.label}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          );
        })}

        {extraCount > 0 && (
          <div
            className="flex items-center justify-center bg-primary text-primary-foreground font-semibold border border-white/10 rounded-full"
            style={{
              width: size,
              height: size,
              marginLeft: open ? 8 : -overlap,
              zIndex: 0,
              fontSize: size * 0.32,
              transition: "margin-left 220ms cubic-bezier(0.16,1,0.3,1)",
            }}
          >
            +{extraCount}
          </div>
        )}
      </div>
    </button>
  );
};

export { AvatarGroup };

