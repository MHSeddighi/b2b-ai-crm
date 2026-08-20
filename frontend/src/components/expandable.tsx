import { useState, type ReactNode } from "react";
import { ChevronDown, ChevronUp, type LucideIcon } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface ExpandableSectionProps {
  icon?: LucideIcon;
  title: string;
  count?: number;
  badge?: ReactNode;
  preview: ReactNode;
  full?: ReactNode;
  /** Show the expand toggle even when count is missing (e.g. fixed lists). */
  alwaysExpandable?: boolean;
  defaultOpen?: boolean;
  className?: string;
}

/** A card whose body shows a minimal preview first and expands on click —
 * keeps the first view compact while all data stays one click away. */
export function ExpandableSection({
  icon: Icon,
  title,
  count,
  badge,
  preview,
  full,
  alwaysExpandable = false,
  defaultOpen = false,
  className,
}: ExpandableSectionProps) {
  const [open, setOpen] = useState(defaultOpen);
  const expandable = alwaysExpandable || (full != null && (count ?? 1) > 0);

  return (
    <Card className={cn("animate-fade-in-up", className)}>
      <CardHeader className="pb-2">
        <button
          type="button"
          onClick={() => expandable && setOpen((v) => !v)}
          className={cn(
            "flex w-full items-center gap-2 text-right",
            expandable && "cursor-pointer"
          )}
          aria-expanded={open}
        >
          {Icon && <Icon className="h-4 w-4 shrink-0 text-muted-foreground" />}
          <CardTitle className="text-sm">{title}</CardTitle>
          {count != null && (
            <Badge variant="secondary" className="tabular-nums">
              {count}
            </Badge>
          )}
          {badge}
          {expandable && (
            <span className="mr-auto text-muted-foreground">
              {open ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </span>
          )}
        </button>
      </CardHeader>
      <CardContent>
        {open && full ? full : preview}
        {expandable && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setOpen((v) => !v)}
            className="mt-3 w-full gap-1 text-muted-foreground"
          >
            {open ? "نمایش کمتر" : `مشاهده همه${count != null ? ` (${count})` : ""}`}
            {open ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
          </Button>
        )}
      </CardContent>
    </Card>
  );
}
