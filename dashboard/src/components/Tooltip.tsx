import { createContext, useCallback, useContext, useState, type ReactNode } from "react";

interface TooltipState {
  x: number;
  y: number;
  content: ReactNode;
}

interface TooltipApi {
  show: (e: React.MouseEvent | React.FocusEvent, content: ReactNode) => void;
  hide: () => void;
}

const TooltipContext = createContext<TooltipApi>({ show: () => {}, hide: () => {} });

/** One shared, pointer-following tooltip for every chart mark on the page. */
export function TooltipProvider({ children }: { children: ReactNode }) {
  const [tip, setTip] = useState<TooltipState | null>(null);

  const show = useCallback<TooltipApi["show"]>((e, content) => {
    if ("clientX" in e) {
      setTip({ x: e.clientX, y: e.clientY, content });
    } else {
      const r = (e.target as HTMLElement).getBoundingClientRect();
      setTip({ x: r.left + r.width / 2, y: r.top, content });
    }
  }, []);
  const hide = useCallback(() => setTip(null), []);

  return (
    <TooltipContext.Provider value={{ show, hide }}>
      {children}
      {tip && (
        <div className="tooltip" role="tooltip" style={{ left: tip.x, top: tip.y }}>
          {tip.content}
        </div>
      )}
    </TooltipContext.Provider>
  );
}

export const useTooltip = () => useContext(TooltipContext);
