"use client";

import { useEffect, useState } from "react";

const DAY_MS = 24 * 60 * 60 * 1000;

function getDeadline() {
  return Date.now() + DAY_MS;
}

function getTimeLeft(target: number) {
  const distance = Math.max(target - Date.now(), 0);
  const hours = Math.floor(distance / (1000 * 60 * 60));
  const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
  const seconds = Math.floor((distance % (1000 * 60)) / 1000);
  return { hours, minutes, seconds };
}

export function PromoCountdown() {
  const [deadline, setDeadline] = useState<number>(getDeadline);
  const [timeLeft, setTimeLeft] = useState(() => getTimeLeft(deadline));

  useEffect(() => {
    const saved = window.localStorage.getItem("promo-deadline");
    const parsed = saved ? Number(saved) : 0;
    const nextDeadline = parsed > Date.now() ? parsed : getDeadline();

    window.localStorage.setItem("promo-deadline", String(nextDeadline));
    setDeadline(nextDeadline);
    setTimeLeft(getTimeLeft(nextDeadline));

    const timer = window.setInterval(() => {
      const remaining = getTimeLeft(nextDeadline);
      if (remaining.hours === 0 && remaining.minutes === 0 && remaining.seconds === 0) {
        const renewedDeadline = getDeadline();
        window.localStorage.setItem("promo-deadline", String(renewedDeadline));
        setDeadline(renewedDeadline);
        setTimeLeft(getTimeLeft(renewedDeadline));
        return;
      }
      setTimeLeft(remaining);
    }, 1000);

    return () => window.clearInterval(timer);
  }, [deadline]);

  return (
    <div className="countdown-strip" aria-live="polite">
      <span>Oferta relampago ativa</span>
      <div className="countdown-boxes">
        <strong>{String(timeLeft.hours).padStart(2, "0")}h</strong>
        <strong>{String(timeLeft.minutes).padStart(2, "0")}m</strong>
        <strong>{String(timeLeft.seconds).padStart(2, "0")}s</strong>
      </div>
    </div>
  );
}
