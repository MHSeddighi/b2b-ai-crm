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
  /** Max height of the scrollable body (default max-h-80). */
  scrollHeight?: string;
}

/** A section card whose body always shows every item inside a scroll area —
 * no "show more" toggles; the scrollbar follows the design system. */
export function SectionCard({
  icon: Icon,
  title,
  count,
  badge,
  children,
  className,
  scrollHeight = "max-h-80",
}: SectionCardProps) {
  return (
    <Card className={cn("flex h-full flex-col animate-fade-in-up", className)}>
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
      <CardContent className="min-h-0 flex-1">
        <div className={cn("overflow-y-auto scrollbar-thin", scrollHeight)}>{children}</div>
      </CardContent>
    </Card>
  );
}
