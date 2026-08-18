import { useState } from "react";

import { Card, CardContent } from "@/components/ui/card";
import { CustomerTable } from "@/components/customer-table";
import { Customer360 } from "@/components/customer-360";
import { customers } from "@/lib/mock-data";
import type { Customer } from "@/lib/types";

export function Customers() {
  const [selected, setSelected] = useState<Customer | null>(null);

  if (selected) {
    return <Customer360 customer={selected} onBack={() => setSelected(null)} />;
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-1 pt-4">
        <h1 className="text-2xl font-semibold tracking-tight">Customers</h1>
        <p className="text-sm text-muted-foreground">
          Click a customer to open their 360° intelligence summary — no manual searching needed.
        </p>
      </div>

      <Card className="animate-fade-in-up">
        <CardContent className="p-0 pt-0">
          <CustomerTable data={customers} pageSize={8} onSelectCustomer={setSelected} />
        </CardContent>
      </Card>
    </div>
  );
}
