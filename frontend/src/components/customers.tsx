import { useEffect, useState } from "react";

import { Card, CardContent } from "@/components/ui/card";
import { CustomerTable } from "@/components/customer-table";
import { Customer360 } from "@/components/customer-360";
import { fetchCustomers, type CustomerRow } from "@/lib/api";

export function Customers() {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [data, setData] = useState<CustomerRow[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchCustomers()
      .then(setData)
      .catch(() => setData([]))
      .finally(() => setLoading(false));
  }, []);

  if (selectedId) {
    return <Customer360 customerId={selectedId} onBack={() => setSelectedId(null)} />;
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-1 pt-4">
        <h1 className="text-2xl font-semibold tracking-tight">مشتریان</h1>
        <p className="text-sm text-muted-foreground">
          برای مشاهده خلاصه هوشمند ۳۶۰ درجه روی هر مشتری کلیک کنید.
        </p>
      </div>

      <Card className="animate-fade-in-up">
        <CardContent className="p-0 pt-0">
          {loading ? (
            <div className="h-64 animate-pulse rounded-xl bg-muted/50" />
          ) : (
            <CustomerTable data={data} pageSize={8} onSelectCustomer={(c) => setSelectedId(c.Customer_ID)} />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
