import {
  FileText,
  TrendingDown,
  MessageSquareWarning,
  AlertTriangle,
  Clock,
} from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

interface Analysis {
  id: string;
  title: string;
  description: string;
  icon: typeof FileText;
  type: "ریسک" | "ریزش" | "شکایات";
  updated: string;
}

const analyses: Analysis[] = [
  {
    id: "a1",
    title: "نمای کلی حساب‌های پرریسک",
    description: "مشتریان پرریسک و متوسط با کاهش حجم خرید در دو فصل گذشته.",
    icon: AlertTriangle,
    type: "ریسک",
    updated: "۲ ساعت پیش",
  },
  {
    id: "a2",
    title: "عوامل ریزش",
    description: "همبستگی بین تعداد شکایات و کاهش خرید برای شناسایی سیگنال‌های ریزش.",
    icon: TrendingDown,
    type: "ریزش",
    updated: "۱ روز پیش",
  },
  {
    id: "a3",
    title: "مضامین شکایات",
    description: "دسته‌بندی دلایل شکایت تجمیع‌شده از همه حساب‌ها در دوره جاری.",
    icon: MessageSquareWarning,
    type: "شکایات",
    updated: "۳ روز پیش",
  },
  {
    id: "a4",
    title: "تمرکز درآمد",
    description: "سهم مشتریان سازمانی از کل درآمد و ریسک ریزش آن‌ها.",
    icon: FileText,
    type: "ریسک",
    updated: "۱ هفته پیش",
  },
];

const typeColor: Record<Analysis["type"], string> = {
  ریسک: "text-red-600 dark:text-red-400",
  ریزش: "text-amber-600 dark:text-amber-400",
  شکایات: "text-indigo-600 dark:text-indigo-400",
};

export function Analyses() {
  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-1 pt-4">
        <h1 className="text-2xl font-semibold tracking-tight">تحلیل‌ها</h1>
        <p className="text-sm text-muted-foreground">
          بینش‌های ذخیره‌شده که توسط دستیار هوشمند از داده‌های مشتریان تولید شده‌اند.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {analyses.map((analysis, i) => {
          const Icon = analysis.icon;
          return (
            <Card
              key={analysis.id}
              className="animate-fade-in-up cursor-pointer transition-colors hover:border-primary/40"
              style={{ animationDelay: `${i * 60}ms` }}
            >
              <CardHeader className="flex flex-row items-start gap-4 space-y-0">
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <Icon className="h-5 w-5" />
                </span>
                <div className="space-y-1">
                  <CardTitle className="text-base leading-snug">{analysis.title}</CardTitle>
                  <CardDescription className="leading-relaxed">
                    {analysis.description}
                  </CardDescription>
                </div>
              </CardHeader>
              <CardContent className="flex items-center gap-2">
                <Badge variant="outline" className="gap-1.5">
                  <span className={`h-1.5 w-1.5 rounded-full ${typeColor[analysis.type]}`} />
                  {analysis.type}
                </Badge>
                <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
                  <Clock className="h-3 w-3" />
                  {analysis.updated}
                </span>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
