import React, { useState, useRef, useCallback, useEffect } from 'react';
import './Tooltip.css';

/**
 * Tooltip — Click-triggered definition popover.
 *
 * Click the underlined text → definition card appears near the text.
 * Click × or anywhere outside → dismisses it.
 *
 * The card auto-sizes to its text content and is always rendered at the
 * highest z-index, guaranteed to be on top of everything else.
 *
 * Props:
 *   text     {string}  — Definition text shown in the card body
 *   term     {string}  — Optional bold title at the top of the card
 *   children           — Inline content to underline/click
 */
function Tooltip({ text, term, children }) {
  const [visible, setVisible]     = useState(false);
  const [anchorRect, setAnchorRect] = useState(null);
  const wrapRef                   = useRef(null);

  // Dismiss on outside click
  useEffect(() => {
    if (!visible) return;
    const dismiss = (e) => {
      if (wrapRef.current && wrapRef.current.contains(e.target)) return;
      setVisible(false);
    };
    document.addEventListener('mousedown', dismiss, true);
    return () => document.removeEventListener('mousedown', dismiss, true);
  }, [visible]);

  // Dismiss on Escape key
  useEffect(() => {
    if (!visible) return;
    const onKey = (e) => { if (e.key === 'Escape') setVisible(false); };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [visible]);

  const handleClick = useCallback((e) => {
    e.stopPropagation();
    if (!text) return;
    if (visible) { setVisible(false); return; }
    // Capture the bounding rect of the trigger element
    setAnchorRect(e.currentTarget.getBoundingClientRect());
    setVisible(true);
  }, [visible, text]);

  if (!text) return <>{children}</>;

  return (
    <span ref={wrapRef} className="tt-wrap" onClick={handleClick}>
      {children}
      {visible && anchorRect && (
        <TooltipCard
          text={text}
          term={term}
          anchorRect={anchorRect}
          onClose={() => setVisible(false)}
        />
      )}
    </span>
  );
}

/**
 * TooltipCard — Positions itself near the anchor without covering it.
 * Clamps to stay within viewport. Auto-sizes to content.
 */
function TooltipCard({ text, term, anchorRect, onClose }) {
  const boxRef = useRef(null);
  // Start invisible while we measure; then snap to correct position
  const [style, setStyle] = useState({ visibility: 'hidden', left: 0, top: 0 });

  useEffect(() => {
    if (!boxRef.current) return;
    const box = boxRef.current.getBoundingClientRect();
    const vw  = window.innerWidth;
    const vh  = window.innerHeight;
    const GAP = 6; // px gap between anchor and card

    // Preferred: below the anchor, left-aligned to anchor's left edge
    let left = anchorRect.left;
    let top  = anchorRect.bottom + GAP;

    // Clamp right edge
    if (left + box.width > vw - 8) left = Math.max(8, vw - box.width - 8);

    // If card would go off the bottom, flip it above the anchor
    if (top + box.height > vh - 8) {
      top = anchorRect.top - box.height - GAP;
    }

    // Clamp top
    if (top < 8) top = 8;

    setStyle({ visibility: 'visible', left, top });
  }, [anchorRect]);

  return (
    <div ref={boxRef} className="tt-box" style={style}>
      <button
        className="tt-box__close"
        onClick={(e) => { e.stopPropagation(); onClose(); }}
        aria-label="Close definition"
      >
        ×
      </button>
      {term && <span className="tt-box__term">{term}</span>}
      <span className="tt-box__text">{text}</span>
    </div>
  );
}

export default Tooltip;
