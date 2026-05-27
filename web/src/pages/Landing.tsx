import React from "react";

interface LandingProps {
  onEnter: () => void;
}

export default function Landing({ onEnter }: LandingProps) {
  return (
    <div className="relative h-full w-full overflow-hidden bg-black">
      <iframe
        title="Invest Multi-Agent Landing"
        src="/landing.html"
        className="absolute inset-0 h-full w-full border-0"
      />
      <button
        type="button"
        aria-label="Start using the app"
        onClick={onEnter}
        className="absolute left-1/2 top-1/2 z-20 h-28 w-[min(90vw,720px)] -translate-x-1/2 -translate-y-1/2 cursor-pointer bg-transparent"
      />
    </div>
  );
}
