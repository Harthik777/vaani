import { useState, useEffect } from "react";

export default function Wave({ active }) {
  const [h, setH] = useState(Array(40).fill(5));

  useEffect(() => {
    if (!active) {
      setH(Array(40).fill(5));
      return;
    }
    const iv = setInterval(() => {
      setH(Array(40).fill(0).map(() => Math.random() * 60 + 6));
    }, 110);
    return () => clearInterval(iv);
  }, [active]);

  return (
    <div className="wave">
      {h.map((v, i) => (
        <span key={i} style={{ height: v }} />
      ))}
    </div>
  );
}
