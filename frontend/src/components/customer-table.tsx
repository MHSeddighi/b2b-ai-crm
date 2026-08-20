import { useMemo, useState } from "react";
import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getSortedRowModel,
  useReactTable,
  type ColumnFiltersState,
  type SortingState,
} from "@tanstack/react-table";
import {
  ArrowDown,
  ArrowUp,
  ArrowUpDown,
  ChevronLeft,
  ChevronRight,
  Search,
} from "lucide-react";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { formatCurrency, formatNumber, cn } from "@/lib/utils";
import type { CustomerRow } from "@/lib/api";

const columnHelper = createColumnHelper<CustomerRow>();

const statusBadge: Record<string, string> = {
  فعال: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
  غیرفعال: "bg-muted text-muted-foreground",
};

interface CustomerTableProps {
  data: CustomerRow[];
  pageSize?: number;
  dense?: boolean;
  toolbar?: boolean;
  onSelectCustomer?: (customer: CustomerRow) => void;
}

export function CustomerTable({
  data,
  pageSize = 8,
  dense = false,
  toolbar = true,
  onSelectCustomer,
}: CustomerTableProps) {
  const [sorting, setSorting] = useState<SortingState>([{ id: "revenue", desc: true }]);
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([]);
  const [globalFilter, setGlobalFilter] = useState("");
  const [pageIndex, setPageIndex] = useState(0);

  const columns = useMemo(
    () => [
      columnHelper.accessor("Customer_ID", {
        header: "کد مشتری",
        cell: (info) => (
          <span className="font-medium tabular-nums">{info.getValue()}</span>
        ),
      }),
      columnHelper.accessor("Customer_Segment", {
        header: "سگمنت",
        cell: (info) => (
          <span className="text-muted-foreground">{info.getValue() ?? "—"}</span>
        ),
      }),
      columnHelper.accessor("Customer_Status", {
        header: "وضعیت",
        cell: (info) => {
          const status = info.getValue() ?? "";
          return (
            <Badge variant="outline" className={cn(statusBadge[status] ?? "", "border-transparent")}>
              {status || "—"}
            </Badge>
          );
        },
      }),
      columnHelper.accessor("revenue", {
        header: () => <span className="text-left">درآمد</span>,
        cell: (info) => (
          <span className="block text-left font-medium tabular-nums">
            {formatCurrency(info.getValue())}
          </span>
        ),
      }),
      columnHelper.accessor("orders", {
        header: () => <span className="text-left">سفارش</span>,
        cell: (info) => <span className="block text-left tabular-nums">{formatNumber(info.getValue())}</span>,
      }),
      columnHelper.accessor("complaints", {
        header: () => <span className="text-left">شکایت</span>,
        cell: (info) => <span className="block text-left tabular-nums">{formatNumber(info.getValue())}</span>,
      }),
      columnHelper.accessor("Credit_Limit", {
        header: () => <span className="text-left">سقف اعتبار</span>,
        cell: (info) => (
          <span className="block text-left tabular-nums">
            {info.getValue() != null ? formatCurrency(Number(info.getValue())) : "—"}
          </span>
        ),
      }),
      ...(onSelectCustomer
        ? [
            columnHelper.display({
              id: "actions",
              header: () => <span className="sr-only">باز کردن</span>,
              cell: (info) => (
                <Button
                  variant="ghost"
                  size="icon"
                  className="mr-auto h-7 w-7 text-muted-foreground hover:text-foreground"
                  onClick={(e) => {
                    e.stopPropagation();
                    onSelectCustomer(info.row.original);
                  }}
                  aria-label="باز کردن نمای ۳۶۰ مشتری"
                >
                  <ChevronLeft className="h-4 w-4" />
                </Button>
              ),
            }),
          ]
        : []),
    ],
    [onSelectCustomer]
  );

  const table = useReactTable({
    data,
    columns,
    state: { sorting, columnFilters, globalFilter },
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    onGlobalFilterChange: setGlobalFilter,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
  });

  const statusFilterValue =
    (columnFilters.find((f) => f.id === "Customer_Status")?.value as string | undefined) ?? "all";

  const setStatusFilter = (value: string) => {
    if (value === "all") {
      setColumnFilters((prev) => prev.filter((f) => f.id !== "Customer_Status"));
    } else {
      setColumnFilters((prev) => [
        ...prev.filter((f) => f.id !== "Customer_Status"),
        { id: "Customer_Status", value },
      ]);
    }
    setPageIndex(0);
  };

  const pageCount = Math.max(1, Math.ceil(table.getFilteredRowModel().rows.length / pageSize));
  const currentPage = Math.min(pageIndex, pageCount - 1);
  const pageRows = table.getFilteredRowModel().rows.slice(
    currentPage * pageSize,
    currentPage * pageSize + pageSize
  );

  return (
    <div>
      {toolbar && (
        <div className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="relative sm:w-64">
            <Search className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={globalFilter}
              onChange={(e) => {
                setGlobalFilter(e.target.value);
                setPageIndex(0);
              }}
              placeholder="جستجوی مشتری..."
              className="pr-9"
              aria-label="جستجوی مشتری"
            />
          </div>
          <Select value={statusFilterValue} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-full sm:w-44" aria-label="فیلتر بر اساس وضعیت">
              <SelectValue placeholder="همه وضعیت‌ها" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">همه وضعیت‌ها</SelectItem>
              <SelectItem value="فعال">فعال</SelectItem>
              <SelectItem value="غیرفعال">غیرفعال</SelectItem>
            </SelectContent>
          </Select>
        </div>
      )}

      <div className="overflow-x-auto">
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header) => {
                  const isSorted = header.column.getIsSorted();
                  const numeric =
                    header.column.id === "revenue" ||
                    header.column.id === "orders" ||
                    header.column.id === "complaints" ||
                    header.column.id === "Credit_Limit";
                  return (
                    <TableHead key={header.id} className={cn(numeric && "text-left")}>
                      {header.isPlaceholder ? null : (
                        <button
                          className={cn(
                            "inline-flex items-center gap-1 tracking-wide hover:text-foreground",
                            header.column.getCanSort() && "cursor-pointer select-none"
                          )}
                          onClick={header.column.getToggleSortingHandler()}
                        >
                          {flexRender(header.column.columnDef.header, header.getContext())}
                          {header.column.getCanSort() &&
                            (isSorted === "asc" ? (
                              <ArrowUp className="h-3 w-3" />
                            ) : isSorted === "desc" ? (
                              <ArrowDown className="h-3 w-3" />
                            ) : (
                              <ArrowUpDown className="h-3 w-3 opacity-40" />
                            ))}
                        </button>
                      )}
                    </TableHead>
                  );
                })}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {pageRows.length === 0 ? (
              <TableRow>
                <TableCell
                  colSpan={columns.length}
                  className="h-24 text-center text-muted-foreground"
                >
                  هیچ مشتری‌ای با فیلترهای شما مطابقت ندارد.
                </TableCell>
              </TableRow>
            ) : (
              pageRows.map((row) => (
                <TableRow
                  key={row.id}
                  className={cn(dense && "h-12", onSelectCustomer && "cursor-pointer")}
                  title={onSelectCustomer ? "باز کردن نمای ۳۶۰ مشتری" : undefined}
                  onClick={
                    onSelectCustomer ? () => onSelectCustomer(row.original) : undefined
                  }
                >
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id}>
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      <div className="flex items-center justify-between border-t px-4 py-2">
        <p className="text-xs text-muted-foreground">
          {formatNumber(table.getFilteredRowModel().rows.length)} مشتری
        </p>
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            disabled={currentPage === 0}
            onClick={() => setPageIndex((p) => Math.max(0, p - 1))}
            aria-label="صفحه قبل"
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
          <span className="px-2 text-xs tabular-nums text-muted-foreground">
            {formatNumber(currentPage + 1)} / {formatNumber(pageCount)}
          </span>
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            disabled={currentPage >= pageCount - 1}
            onClick={() => setPageIndex((p) => Math.min(pageCount - 1, p + 1))}
            aria-label="صفحه بعد"
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
