"use client";

import { useCallback, useEffect, useState, type KeyboardEvent } from "react";
import {
  AlertCircle,
  AlertTriangle,
  ArrowUpDown,
  Check,
  ChevronLeft,
  ChevronRight,
  Code2,
  Copy,
  Database,
  ExternalLink,
  FileCode,
  Info,
  LoaderCircle,
  Play,
  RefreshCw,
  Search,
  ShieldAlert,
  Table as TableIcon,
  Terminal,
} from "lucide-react";
import type {
  DBColumnMeta,
  DBQueryResult,
  DBTable,
  DBTableRowsResponse,
  DBTablesResponse,
  DBSchemaResponse,
} from "@/lib/control-plane";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

interface ProjectDbManageProps {
  projectId: string;
}

export function ProjectDbManage({ projectId }: ProjectDbManageProps) {
  const [activeTab, setActiveTab] = useState<"explorer" | "editor" | "schema">("explorer");

  // Database & tables state
  const [dbName, setDbName] = useState<string>("");
  const [tables, setTables] = useState<DBTable[]>([]);
  const [loadingTables, setLoadingTables] = useState(true);
  const [refreshingTables, setRefreshingTables] = useState(false);
  const [tablesError, setTablesError] = useState<string | null>(null);
  const [dbNotProvisioned, setDbNotProvisioned] = useState(false);

  // Table selection & data state
  const [selectedTable, setSelectedTable] = useState<string | null>(null);
  const [tableSearch, setTableSearch] = useState("");
  const [tableData, setTableData] = useState<DBTableRowsResponse | null>(null);
  const [loadingData, setLoadingData] = useState(false);
  const [dataError, setDataError] = useState<string | null>(null);
  const [dataVersion, setDataVersion] = useState(0);
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(50);
  const [sortColumn, setSortColumn] = useState<string | null>(null);
  const [sortDirection, setSortDirection] = useState<"ASC" | "DESC">("ASC");
  const [dataViewMode, setDataViewMode] = useState<"rows" | "columns">("rows");

  // SQL Editor state
  const [sql, setSql] = useState("SELECT table_name, table_schema FROM information_schema.tables WHERE table_schema = 'public';");
  const [writeMode, setWriteMode] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [queryResult, setQueryResult] = useState<DBQueryResult | null>(null);
  const [queryError, setQueryError] = useState<string | null>(null);

  // Schema viewer state
  const [schemaSql, setSchemaSql] = useState<string | null>(null);
  const [loadingSchema, setLoadingSchema] = useState(false);
  const [schemaError, setSchemaError] = useState<string | null>(null);
  const [schemaCopied, setSchemaCopied] = useState(false);

  // Fetch tables list (manual refresh)
  const fetchTables = useCallback(
    async (isSilent = false) => {
      if (!isSilent) setLoadingTables(true);
      else setRefreshingTables(true);
      setTablesError(null);
      setDbNotProvisioned(false);

      try {
        const res = await fetch(`/api/projects/${encodeURIComponent(projectId)}/db/tables`);
        if (res.status === 409) {
          setDbNotProvisioned(true);
          setTables([]);
          return;
        }
        if (!res.ok) {
          const body = await res.json().catch(() => ({}));
          throw new Error(body.error || `Failed to fetch tables (HTTP ${res.status})`);
        }
        const data: DBTablesResponse = await res.json();
        setDbName(data.db_name || "");
        setTables(data.tables || []);
        if (data.tables && data.tables.length > 0 && !selectedTable) {
          setSelectedTable(data.tables[0].name);
        }
      } catch (err) {
        setTablesError(err instanceof Error ? err.message : "Failed to load database tables");
      } finally {
        setLoadingTables(false);
        setRefreshingTables(false);
      }
    },
    [projectId, selectedTable],
  );

  // Fetch schema SQL (manual refresh)
  const fetchSchema = useCallback(async () => {
    setLoadingSchema(true);
    setSchemaError(null);
    try {
      const res = await fetch(`/api/projects/${encodeURIComponent(projectId)}/db/schema`);
      if (res.status === 404) {
        setSchemaSql(null);
        setSchemaError("No migration SQL file found. Build or preview the project to generate database migrations.");
        return;
      }
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.error || `Failed to load schema (HTTP ${res.status})`);
      }
      const data: DBSchemaResponse = await res.json();
      setSchemaSql(data.schema_sql);
    } catch (err) {
      setSchemaError(err instanceof Error ? err.message : "Failed to fetch schema");
    } finally {
      setLoadingSchema(false);
    }
  }, [projectId]);

  // Initial load of tables
  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const res = await fetch(`/api/projects/${encodeURIComponent(projectId)}/db/tables`);
        if (!active) return;
        if (res.status === 409) {
          setDbNotProvisioned(true);
          setTables([]);
          return;
        }
        if (!res.ok) {
          const body = await res.json().catch(() => ({}));
          throw new Error(body.error || `Failed to fetch tables (HTTP ${res.status})`);
        }
        const data: DBTablesResponse = await res.json();
        if (!active) return;
        setDbName(data.db_name || "");
        setTables(data.tables || []);
        if (data.tables && data.tables.length > 0) {
          setSelectedTable(data.tables[0].name);
        }
      } catch (err) {
        if (active) setTablesError(err instanceof Error ? err.message : "Failed to load database tables");
      } finally {
        if (active) setLoadingTables(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [projectId]);

  // Load table data when selected table, page, or sort changes
  useEffect(() => {
    if (!selectedTable || dbNotProvisioned) return;
    let active = true;
    void (async () => {
      setLoadingData(true);
      setDataError(null);
      try {
        const params = new URLSearchParams();
        params.set("limit", String(pageSize));
        params.set("offset", String(page * pageSize));
        if (sortColumn) {
          params.set("order_by", sortColumn);
          params.set("direction", sortDirection);
        }
        const res = await fetch(
          `/api/projects/${encodeURIComponent(projectId)}/db/tables/${encodeURIComponent(selectedTable)}?${params.toString()}`,
        );
        if (!active) return;
        if (res.status === 409) {
          setDbNotProvisioned(true);
          return;
        }
        if (!res.ok) {
          const body = await res.json().catch(() => ({}));
          throw new Error(body.error || `Failed to load table data (HTTP ${res.status})`);
        }
        const data: DBTableRowsResponse = await res.json();
        if (active) setTableData(data);
      } catch (err) {
        if (active) setDataError(err instanceof Error ? err.message : "Failed to fetch table data");
      } finally {
        if (active) setLoadingData(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [projectId, selectedTable, page, pageSize, sortColumn, sortDirection, dataVersion, dbNotProvisioned]);

  // Load schema when schema tab activated
  useEffect(() => {
    if (activeTab !== "schema" || schemaSql !== null) return;
    let active = true;
    void (async () => {
      setLoadingSchema(true);
      setSchemaError(null);
      try {
        const res = await fetch(`/api/projects/${encodeURIComponent(projectId)}/db/schema`);
        if (!active) return;
        if (res.status === 404) {
          setSchemaSql(null);
          setSchemaError("No migration SQL file found. Build or preview the project to generate database migrations.");
          return;
        }
        if (!res.ok) {
          const body = await res.json().catch(() => ({}));
          throw new Error(body.error || `Failed to load schema (HTTP ${res.status})`);
        }
        const data: DBSchemaResponse = await res.json();
        if (active) setSchemaSql(data.schema_sql);
      } catch (err) {
        if (active) setSchemaError(err instanceof Error ? err.message : "Failed to fetch schema");
      } finally {
        if (active) setLoadingSchema(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [activeTab, schemaSql, projectId]);

  const handleSelectTable = (tableName: string) => {
    setSelectedTable(tableName);
    setPage(0);
    setSortColumn(null);
    setSortDirection("ASC");
  };

  // Execute SQL Query
  const handleExecuteQuery = async () => {
    if (!sql.trim()) return;
    setExecuting(true);
    setQueryError(null);
    setQueryResult(null);

    try {
      const res = await fetch(`/api/projects/${encodeURIComponent(projectId)}/db/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sql, write: writeMode }),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error || `Query error (HTTP ${res.status})`);
      }
      setQueryResult(data as DBQueryResult);
      // If a write query succeeded and we're exploring tables, refresh tables list
      if (writeMode) {
        void fetchTables(true);
        setDataVersion((v) => v + 1);
      }
    } catch (err) {
      setQueryError(err instanceof Error ? err.message : "Failed to execute query");
    } finally {
      setExecuting(false);
    }
  };

  const handleKeyDownEditor = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault();
      void handleExecuteQuery();
    }
  };

  const handleSort = (column: string) => {
    let nextDir: "ASC" | "DESC" = "ASC";
    if (sortColumn === column) {
      nextDir = sortDirection === "ASC" ? "DESC" : "ASC";
    }
    setSortColumn(column);
    setSortDirection(nextDir);
    setPage(0);
  };

  const handlePageChange = (newPage: number) => {
    setPage(newPage);
  };

  const handleCopySchema = async () => {
    if (!schemaSql) return;
    try {
      await navigator.clipboard.writeText(schemaSql);
      setSchemaCopied(true);
      setTimeout(() => setSchemaCopied(false), 2000);
    } catch {
      // ignore
    }
  };

  const filteredTables = tables.filter((t) =>
    t.name.toLowerCase().includes(tableSearch.toLowerCase()),
  );

  return (
    <div className="space-y-6">
      {/* Top Header Card */}
      <Card>
        <CardHeader className="pb-4">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-lg bg-primary/10 text-primary border border-primary/20">
                <Database className="size-5" />
              </div>
              <div>
                <CardTitle className="text-xl flex items-center gap-2">
                  Database Explorer
                  {dbName && (
                    <Badge variant="outline" className="text-xs font-mono font-normal">
                      {dbName}
                    </Badge>
                  )}
                </CardTitle>
                <CardDescription className="text-xs">
                  Inspect tables, browse schemas, and execute SQL queries on the project PostgreSQL database.
                </CardDescription>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  void fetchTables(false);
                  setDataVersion((v) => v + 1);
                  if (activeTab === "schema") void fetchSchema();
                }}
                disabled={loadingTables || refreshingTables}
              >
                <RefreshCw
                  className={cn("size-3.5 mr-1.5", (loadingTables || refreshingTables) && "animate-spin")}
                />
                Refresh
              </Button>
            </div>
          </div>

          {/* Sub Navigation Tabs */}
          <div className="flex items-center gap-1 border-b border-border/60 pt-4 -mb-1">
            <button
              type="button"
              onClick={() => setActiveTab("explorer")}
              className={cn(
                "flex items-center gap-2 px-3 py-2 text-sm font-medium border-b-2 transition-colors",
                activeTab === "explorer"
                  ? "border-primary text-primary"
                  : "border-transparent text-muted-foreground hover:text-foreground",
              )}
            >
              <TableIcon className="size-4" />
              Tables & Data
              {tables.length > 0 && (
                <Badge variant="secondary" className="text-[10px] px-1.5 py-0 h-4">
                  {tables.length}
                </Badge>
              )}
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("editor")}
              className={cn(
                "flex items-center gap-2 px-3 py-2 text-sm font-medium border-b-2 transition-colors",
                activeTab === "editor"
                  ? "border-primary text-primary"
                  : "border-transparent text-muted-foreground hover:text-foreground",
              )}
            >
              <Terminal className="size-4" />
              SQL Editor
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("schema")}
              className={cn(
                "flex items-center gap-2 px-3 py-2 text-sm font-medium border-b-2 transition-colors",
                activeTab === "schema"
                  ? "border-primary text-primary"
                  : "border-transparent text-muted-foreground hover:text-foreground",
              )}
            >
              <FileCode className="size-4" />
              Schema SQL
            </button>
          </div>
        </CardHeader>
      </Card>

      {/* 409 Database Not Provisioned State */}
      {dbNotProvisioned ? (
        <Card className="border-amber-500/30 bg-amber-500/5">
          <CardContent className="pt-6 pb-6 text-center space-y-4">
            <div className="mx-auto w-12 h-12 rounded-full bg-amber-500/10 flex items-center justify-center text-amber-600 dark:text-amber-400">
              <AlertCircle className="size-6" />
            </div>
            <div className="max-w-md mx-auto space-y-1">
              <h3 className="text-base font-semibold text-foreground">Database Not Provisioned Yet</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">
                The local PostgreSQL database for this workspace is created during project preview or build. Run preview to initialize the database schema.
              </p>
            </div>
            <div className="pt-2 flex justify-center gap-3">
              <Button
                variant="outline"
                size="sm"
                onClick={() => void fetchTables(false)}
                disabled={loadingTables}
              >
                <RefreshCw className={cn("size-3.5 mr-1.5", loadingTables && "animate-spin")} />
                Check again
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : tablesError ? (
        <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive flex items-start gap-3">
          <AlertCircle className="size-5 shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold">Error connecting to database</p>
            <p className="mt-1 text-xs opacity-90">{tablesError}</p>
          </div>
        </div>
      ) : null}

      {/* TAB 1: Tables & Data Explorer */}
      {!dbNotProvisioned && activeTab === "explorer" && (
        <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
          {/* Tables Sidebar */}
          <div className="md:col-span-4 lg:col-span-3 space-y-3">
            <div className="relative">
              <Search className="size-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Search tables..."
                value={tableSearch}
                onChange={(e) => setTableSearch(e.target.value)}
                className="pl-8 text-xs h-8"
              />
            </div>

            <div className="border border-border/70 rounded-lg overflow-hidden bg-card divide-y divide-border/40 max-h-[600px] overflow-y-auto">
              {loadingTables ? (
                <div className="p-4 text-center text-xs text-muted-foreground flex items-center justify-center gap-2">
                  <LoaderCircle className="size-3.5 animate-spin" />
                  Loading tables...
                </div>
              ) : filteredTables.length === 0 ? (
                <div className="p-4 text-center text-xs text-muted-foreground">
                  {tables.length === 0 ? "No tables found in database" : "No tables match search"}
                </div>
              ) : (
                filteredTables.map((tbl) => {
                  const isSelected = selectedTable === tbl.name;
                  return (
                    <button
                      key={`${tbl.schema}.${tbl.name}`}
                      type="button"
                      onClick={() => handleSelectTable(tbl.name)}
                      className={cn(
                        "w-full px-3 py-2.5 text-left text-xs transition-colors flex items-center justify-between",
                        isSelected
                          ? "bg-primary/10 text-primary font-medium border-l-2 border-primary"
                          : "text-foreground hover:bg-muted/50",
                      )}
                    >
                      <span className="flex items-center gap-2 truncate">
                        <TableIcon className="size-3.5 shrink-0 opacity-70" />
                        <span className="truncate">{tbl.name}</span>
                      </span>
                      <span className="flex items-center gap-1.5 shrink-0 text-muted-foreground">
                        <span className="text-[10px] bg-muted px-1.5 py-0.5 rounded font-mono">
                          {tbl.row_count.toLocaleString()}
                        </span>
                      </span>
                    </button>
                  );
                })
              )}
            </div>
          </div>

          {/* Table Data View */}
          <div className="md:col-span-8 lg:col-span-9 space-y-4">
            {selectedTable ? (
              <Card>
                <CardHeader className="py-3 px-4 border-b border-border/50">
                  <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                    <div className="flex items-center gap-2.5">
                      <TableIcon className="size-4 text-primary" />
                      <span className="font-semibold text-sm">{selectedTable}</span>
                      {tableData?.total !== undefined && (
                        <Badge variant="outline" className="text-xs font-mono font-normal">
                          {tableData.total.toLocaleString()} rows
                        </Badge>
                      )}
                    </div>

                    <div className="flex items-center gap-1.5">
                      <div className="flex items-center rounded-md border border-border/60 p-0.5 bg-muted/40">
                        <button
                          type="button"
                          onClick={() => setDataViewMode("rows")}
                          className={cn(
                            "px-2.5 py-1 text-xs font-medium rounded transition-colors",
                            dataViewMode === "rows"
                              ? "bg-background text-foreground shadow-sm"
                              : "text-muted-foreground hover:text-foreground",
                          )}
                        >
                          Data
                        </button>
                        <button
                          type="button"
                          onClick={() => setDataViewMode("columns")}
                          className={cn(
                            "px-2.5 py-1 text-xs font-medium rounded transition-colors",
                            dataViewMode === "columns"
                              ? "bg-background text-foreground shadow-sm"
                              : "text-muted-foreground hover:text-foreground",
                          )}
                        >
                          Structure
                        </button>
                      </div>

                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-7 px-2 text-xs"
                        onClick={() => setDataVersion((v) => v + 1)}
                        disabled={loadingData}
                      >
                        <RefreshCw className={cn("size-3", loadingData && "animate-spin")} />
                      </Button>
                    </div>
                  </div>
                </CardHeader>

                <CardContent className="p-0">
                  {dataError && (
                    <div className="p-4 text-xs text-destructive bg-destructive/10 border-b border-destructive/20 flex items-center gap-2">
                      <AlertCircle className="size-4 shrink-0" />
                      <span>{dataError}</span>
                    </div>
                  )}

                  {loadingData && !tableData ? (
                    <div className="py-16 text-center text-xs text-muted-foreground flex items-center justify-center gap-2">
                      <LoaderCircle className="size-4 animate-spin" />
                      Loading table data...
                    </div>
                  ) : dataViewMode === "columns" ? (
                    /* Column Structure View */
                    <div className="overflow-x-auto">
                      <table className="w-full text-xs text-left">
                        <thead className="bg-muted/50 border-b border-border/50 text-muted-foreground font-medium">
                          <tr>
                            <th className="px-4 py-2.5">Column</th>
                            <th className="px-4 py-2.5">Data Type</th>
                            <th className="px-4 py-2.5">Nullable</th>
                            <th className="px-4 py-2.5">Default</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-border/30">
                          {tableData?.columns_meta?.map((col) => (
                            <tr key={col.column} className="hover:bg-muted/30 transition-colors">
                              <td className="px-4 py-2 font-mono font-medium text-foreground">
                                {col.column}
                              </td>
                              <td className="px-4 py-2 font-mono text-muted-foreground">
                                {col.type}
                              </td>
                              <td className="px-4 py-2">
                                <Badge
                                  variant={col.nullable ? "secondary" : "outline"}
                                  className="text-[10px] px-1.5 py-0"
                                >
                                  {col.nullable ? "YES" : "NO"}
                                </Badge>
                              </td>
                              <td className="px-4 py-2 font-mono text-muted-foreground text-[11px]">
                                {col.default || "—"}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    /* Data Rows Grid */
                    <div>
                      {tableData?.rows?.length === 0 ? (
                        <div className="py-12 text-center text-xs text-muted-foreground">
                          Table has no rows
                        </div>
                      ) : (
                        <div className="overflow-x-auto max-h-[500px]">
                          <table className="w-full text-xs text-left border-collapse">
                            <thead className="bg-muted/60 sticky top-0 z-10 border-b border-border/70 text-muted-foreground font-medium">
                              <tr>
                                {tableData?.columns?.map((col) => {
                                  const isSorted = sortColumn === col;
                                  return (
                                    <th
                                      key={col}
                                      onClick={() => handleSort(col)}
                                      className="px-3 py-2 cursor-pointer hover:bg-muted select-none whitespace-nowrap"
                                    >
                                      <div className="flex items-center gap-1">
                                        <span className="font-mono text-[11px] font-semibold text-foreground">
                                          {col}
                                        </span>
                                        <ArrowUpDown
                                          className={cn(
                                            "size-3 text-muted-foreground",
                                            isSorted && "text-primary opacity-100",
                                          )}
                                        />
                                        {isSorted && (
                                          <span className="text-[9px] text-primary">
                                            {sortDirection}
                                          </span>
                                        )}
                                      </div>
                                    </th>
                                  );
                                })}
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-border/30 font-mono text-[11px]">
                              {tableData?.rows?.map((row, idx) => (
                                <tr key={idx} className="hover:bg-muted/30 transition-colors">
                                  {tableData?.columns?.map((col) => {
                                    const val = row[col];
                                    const isNull = val === null || val === undefined;
                                    return (
                                      <td
                                        key={col}
                                        className={cn(
                                          "px-3 py-1.5 whitespace-nowrap max-w-xs truncate",
                                          isNull && "text-muted-foreground/60 italic",
                                        )}
                                        title={isNull ? "NULL" : String(val)}
                                      >
                                        {isNull ? "NULL" : String(val)}
                                      </td>
                                    );
                                  })}
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      )}

                      {/* Pagination Bar */}
                      <div className="flex items-center justify-between px-4 py-2.5 border-t border-border/50 text-xs text-muted-foreground bg-muted/20">
                        <div>
                          Showing {tableData?.rows?.length ? page * pageSize + 1 : 0} to{" "}
                          {tableData?.rows ? page * pageSize + tableData.rows.length : 0} of{" "}
                          {tableData?.total?.toLocaleString() ?? 0}
                        </div>

                        <div className="flex items-center gap-2">
                          <Button
                            variant="outline"
                            size="sm"
                            className="h-7 px-2"
                            disabled={page <= 0 || loadingData}
                            onClick={() => handlePageChange(page - 1)}
                          >
                            <ChevronLeft className="size-3.5" />
                          </Button>
                          <span className="text-[11px] font-medium px-1">
                            Page {page + 1} of{" "}
                            {Math.max(1, Math.ceil((tableData?.total || 1) / pageSize))}
                          </span>
                          <Button
                            variant="outline"
                            size="sm"
                            className="h-7 px-2"
                            disabled={
                              !tableData?.total ||
                              (page + 1) * pageSize >= tableData.total ||
                              loadingData
                            }
                            onClick={() => handlePageChange(page + 1)}
                          >
                            <ChevronRight className="size-3.5" />
                          </Button>
                        </div>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            ) : (
              <Card className="p-8 text-center text-muted-foreground text-xs">
                Select a table from the sidebar to inspect its data.
              </Card>
            )}
          </div>
        </div>
      )}

      {/* TAB 2: SQL Editor */}
      {!dbNotProvisioned && activeTab === "editor" && (
        <div className="space-y-4">
          <Card>
            <CardHeader className="py-3 px-4 border-b border-border/50">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                <div className="flex items-center gap-2">
                  <Terminal className="size-4 text-primary" />
                  <span className="font-semibold text-sm">Query Console</span>
                  {writeMode ? (
                    <Badge variant="destructive" className="text-[10px] flex items-center gap-1">
                      <ShieldAlert className="size-3" />
                      Write Mode Active
                    </Badge>
                  ) : (
                    <Badge variant="secondary" className="text-[10px]">
                      Read-Only (Auto-Rollback)
                    </Badge>
                  )}
                </div>

                <div className="flex items-center gap-3">
                  {/* Write Mode Toggle */}
                  <label className="flex items-center gap-1.5 cursor-pointer text-xs text-muted-foreground select-none">
                    <input
                      type="checkbox"
                      checked={writeMode}
                      onChange={(e) => setWriteMode(e.target.checked)}
                      className="rounded border-border text-primary focus:ring-primary size-3.5"
                    />
                    <span>Allow Write / Commit</span>
                  </label>

                  <Button
                    size="sm"
                    onClick={handleExecuteQuery}
                    disabled={executing || !sql.trim()}
                    className={cn("h-8 gap-1.5 text-xs", writeMode && "bg-amber-600 hover:bg-amber-700 text-white")}
                  >
                    {executing ? (
                      <LoaderCircle className="size-3.5 animate-spin" />
                    ) : (
                      <Play className="size-3.5 fill-current" />
                    )}
                    Run Query
                    <span className="text-[10px] opacity-75 font-mono ml-1">⌘⏎</span>
                  </Button>
                </div>
              </div>
            </CardHeader>

            <CardContent className="p-4 space-y-3">
              {writeMode && (
                <div className="rounded-md border border-amber-500/30 bg-amber-500/10 p-2.5 text-xs text-amber-700 dark:text-amber-300 flex items-center gap-2">
                  <AlertTriangle className="size-4 shrink-0 text-amber-500" />
                  <span>
                    <strong>Caution:</strong> Write mode is enabled. INSERT, UPDATE, DELETE, and DDL statements will be permanently committed to the database.
                  </span>
                </div>
              )}

              <div className="relative">
                <textarea
                  value={sql}
                  onChange={(e) => setSql(e.target.value)}
                  onKeyDown={handleKeyDownEditor}
                  rows={6}
                  placeholder="Enter SQL statement (e.g. SELECT * FROM users LIMIT 10;)"
                  className="w-full font-mono text-xs p-3 rounded-md bg-muted/40 border border-border/80 focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary leading-relaxed resize-y"
                  spellCheck={false}
                />
              </div>

              {queryError && (
                <div className="rounded-md border border-destructive/30 bg-destructive/10 p-3 text-xs text-destructive flex items-start gap-2.5">
                  <AlertCircle className="size-4 shrink-0 mt-0.5" />
                  <div className="space-y-1">
                    <p className="font-semibold">Query Failed</p>
                    <pre className="font-mono text-[11px] whitespace-pre-wrap">{queryError}</pre>
                  </div>
                </div>
              )}

              {queryResult && (
                <div className="space-y-3 pt-2">
                  <div className="flex items-center justify-between text-xs text-muted-foreground border-b border-border/50 pb-2">
                    <div className="flex items-center gap-3">
                      <span>
                        Returned <strong>{queryResult.rowcount}</strong> row{queryResult.rowcount === 1 ? "" : "s"}
                      </span>
                      <span>•</span>
                      <span>
                        Duration: <strong>{queryResult.duration_ms}ms</strong>
                      </span>
                    </div>
                    <Badge variant="outline" className="text-[10px] font-normal">
                      {queryResult.notice}
                    </Badge>
                  </div>

                  {queryResult.rows.length > 0 ? (
                    <div className="overflow-x-auto max-h-[400px] border border-border/60 rounded-md">
                      <table className="w-full text-xs text-left border-collapse">
                        <thead className="bg-muted/70 sticky top-0 border-b border-border/60 text-muted-foreground font-medium">
                          <tr>
                            {queryResult.columns.map((col) => (
                              <th key={col} className="px-3 py-2 font-mono text-[11px] font-semibold text-foreground whitespace-nowrap">
                                {col}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-border/30 font-mono text-[11px]">
                          {queryResult.rows.map((r, i) => (
                            <tr key={i} className="hover:bg-muted/30 transition-colors">
                              {queryResult.columns.map((col) => {
                                const v = r[col];
                                const isNull = v === null || v === undefined;
                                return (
                                  <td
                                    key={col}
                                    className={cn(
                                      "px-3 py-1.5 whitespace-nowrap max-w-xs truncate",
                                      isNull && "text-muted-foreground/60 italic",
                                    )}
                                  >
                                    {isNull ? "NULL" : String(v)}
                                  </td>
                                );
                              })}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <div className="p-4 text-center text-xs text-muted-foreground bg-muted/20 rounded-md">
                      Statement executed successfully. No rows returned.
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* TAB 3: Schema SQL Viewer */}
      {!dbNotProvisioned && activeTab === "schema" && (
        <Card>
          <CardHeader className="py-3 px-4 border-b border-border/50">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <FileCode className="size-4 text-primary" />
                <span className="font-semibold text-sm">Generated Migration Schema</span>
                <span className="text-xs text-muted-foreground font-mono">0001_init.sql</span>
              </div>

              <div className="flex items-center gap-2">
                {schemaSql && (
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-7 text-xs gap-1.5"
                    onClick={handleCopySchema}
                  >
                    {schemaCopied ? (
                      <>
                        <Check className="size-3 text-emerald-500" />
                        Copied
                      </>
                    ) : (
                      <>
                        <Copy className="size-3" />
                        Copy SQL
                      </>
                    )}
                  </Button>
                )}
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 px-2 text-xs"
                  onClick={() => void fetchSchema()}
                  disabled={loadingSchema}
                >
                  <RefreshCw className={cn("size-3", loadingSchema && "animate-spin")} />
                </Button>
              </div>
            </div>
          </CardHeader>

          <CardContent className="p-4">
            {loadingSchema ? (
              <div className="py-16 text-center text-xs text-muted-foreground flex items-center justify-center gap-2">
                <LoaderCircle className="size-4 animate-spin" />
                Loading schema SQL...
              </div>
            ) : schemaError ? (
              <div className="rounded-md border border-border/60 bg-muted/20 p-6 text-center space-y-2 text-xs text-muted-foreground">
                <Info className="size-5 mx-auto text-muted-foreground/70" />
                <p>{schemaError}</p>
              </div>
            ) : schemaSql ? (
              <div className="relative">
                <pre className="p-4 rounded-md bg-muted/40 border border-border/70 font-mono text-xs leading-relaxed overflow-x-auto max-h-[600px] text-foreground select-text">
                  {schemaSql}
                </pre>
              </div>
            ) : null}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
