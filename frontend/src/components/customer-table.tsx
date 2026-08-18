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
import { riskColor } from "@/lib/mock-data";
import { formatCurrency, formatPercent, cn } from "@/lib/utils";
import type { Customer, RiskLevel } from "@/lib/types";

const columnHelper = createColumnHelper<Customer>();

interface CustomerTableProps {
  data: Customer[];
  pageSize?: number;
  dense?: boolean;
  toolbar?: boolean;
  onSelectCustomer?: (customer: Customer) => void;
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
      columnHelper.accessor("name", {
        header: "Customer",
        cell: (info) => {
          const customer = info.row.original;
          const initials = customer.name
            .split(" ")
            .map((p) => p[0])
            .slice(0, 2)
            .join("");
          return (
            <div className="flex items-center gap-3">
              <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-secondary text-xs font-medium text-secondary-foreground">
                {initials}
              </span>
              <div className="flex min-w-0 flex-col leading-tight">
                <span className="truncate font-medium">{customer.name}</span>
                <span className="truncate text-xs text-muted-foreground">
                  {customer.segment} · {customer.region}
                </span>
              </div>
            </div>
          );
        },
      }),
      columnHelper.accessor("revenue", {
        header: () => <span className="text-right">Revenue</span>,
        cell: (info) => (
          <span className="block text-right font-medium tabular-nums">
            {formatCurrency(info.getValue())}
          </span>
        ),
      }),
      columnHelper.accessor("complaints", {
        header: () => <span className="text-right">Complaints</span>,
        cell: (info) => <span className="block text-right tabular-nums">{info.getValue()}</span>,
      }),
      columnHelper.accessor("purchaseChange", {
        header: () => <span className="text-right">Purchase Change</span>,
        cell: (info) => {
          const v = info.getValue();
          const positive = v >= 0;
          return (
            <span
              className={cn(
                "block text-right font-medium tabular-nums",
                positive ? "text-emerald-600 dark:text-emerald-400" : "text-red-600 dark:text-red-400"
              )}
            >
              {formatPercent(v)}
            </span>
          );
        },
      }),
      columnHelper.accessor("risk", {
        header: () => <span>Risk</span>,
        cell: (info) => {
          const risk = info.getValue() as RiskLevel;
          const palette = riskColor[risk];
          return (
            <Badge variant="outline" className={cn(palette.bg, "gap-1.5 border-transparent")}>
              <span className={cn("h-1.5 w-1.5 rounded-full", palette.dot)} />
              <span className={palette.text}>{palette.label}</span>
            </Badge>
          );
        },
      }),
      ...(onSelectCustomer
        ? [
            columnHelper.display({
              id: "actions",
              header: () => <span className="sr-only">Open</span>,
              cell: (info) => (
                <Button
                  variant="ghost"
                  size="icon"
                  className="ml-auto h-7 w-7 text-muted-foreground hover:text-foreground"
                  onClick={(e) => {
                    e.stopPropagation();
                    onSelectCustomer(info.row.original);
                  }}
                  aria-label="Open customer 360"
                >
                  <ChevronRight className="h-4 w-4" />
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

  const riskFilterValue =
    (columnFilters.find((f) => f.id === "risk")?.value as string | undefined) ?? "all";

  const setRiskFilter = (value: string) => {
    if (value === "all") {
      setColumnFilters((prev) => prev.filter((f) => f.id !== "risk"));
    } else {
      setColumnFilters((prev) => [
        ...prev.filter((f) => f.id !== "risk"),
        { id: "risk", value },
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
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={globalFilter}
              onChange={(e) => {
                setGlobalFilter(e.target.value);
                setPageIndex(0);
              }}
              placeholder="Search customers..."
              className="pl-9"
              aria-label="Search customers"
            />
          </div>
          <Select value={riskFilterValue} onValueChange={setRiskFilter}>
            <SelectTrigger className="w-full sm:w-44" aria-label="Filter by risk">
              <SelectValue placeholder="All risk levels" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All risk levels</SelectItem>
              <SelectItem value="high">High risk</SelectItem>
              <SelectItem value="medium">Medium risk</SelectItem>
              <SelectItem value="low">Low risk</SelectItem>
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
                    header.column.id === "complaints" ||
                    header.column.id === "purchaseChange";
                  return (
                    <TableHead key={header.id} className={cn(numeric && "text-right")}>
                      {header.isPlaceholder ? null : (
                        <button
                          className={cn(
                            "inline-flex items-center gap-1 uppercase tracking-wide hover:text-foreground",
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
                  No customers match your filters.
                </TableCell>
              </TableRow>
            ) : (
              pageRows.map((row) => (
                <TableRow
                  key={row.id}
                  className={cn(dense && "h-12", onSelectCustomer && "cursor-pointer")}
                  title={onSelectCustomer ? "Open customer 360" : undefined}
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
          {table.getFilteredRowModel().rows.length} customers
        </p>
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            disabled={currentPage === 0}
            onClick={() => setPageIndex((p) => Math.max(0, p - 1))}
            aria-label="Previous page"
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <span className="px-2 text-xs tabular-nums text-muted-foreground">
            {currentPage + 1} / {pageCount}
          </span>
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            disabled={currentPage >= pageCount - 1}
            onClick={() => setPageIndex((p) => Math.min(pageCount - 1, p + 1))}
            aria-label="Next page"
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
