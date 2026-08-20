import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

interface SectionCardProps {
  icon?: LucideIcon;
  title: string;
  count?: number;
  badge?: ReactNode;
  children: ReactNode;
  className?: string;
  /** Height of the scrollable body (default max-h-72 ≈ 10 items at a time).
   * The card keeps a fixed height and scrolls internally for the rest. */
  bodyHeight?: string;
}

/** A section card with a FIXED body height: only a handful of items are
 * visible at once (default ~10) and the rest are reached by scrolling inside
 * the card — the card never grows to show everything. */
export function SectionCard({
  icon: Icon,
  title,
  count,
  badge,
  children,
  className,
  bodyHeight = "max-h-72",
}: SectionCardProps) {
  return (
    <Card className={cn("flex flex-col animate-fade-in-up", className)}>
      <CardHeader className="shrink-0 pb-2">
        <div className="flex w-full items-center gap-2">
          {Icon && <Icon className="h-4 w-4 shrink-0 text-muted-foreground" />}
          <CardTitle className="text-sm">{title}</CardTitle>
          {count != null && (
            <Badge variant="secondary" className="tabular-nums">
              {count}
            </Badge>
          )}
          {badge && <span className="mr-auto">{badge}</span>}
        </div>
      </CardHeader>
      <CardContent className="min-h-0">
        <div className={cn("overflow-y-auto scrollbar-thin", bodyHeight)}>{children}</div>
      </CardContent>
    </Card>
  );
}
