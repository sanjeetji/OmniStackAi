"use client";

import { useEffect, useState, useCallback } from "react";
import {
  AlertCircle,
  Check,
  CheckCircle2,
  Clock,
  Copy,
  ExternalLink,
  Globe,
  HelpCircle,
  Info,
  Loader2,
  Lock,
  Plus,
  RefreshCw,
  ShieldCheck,
  Trash2,
} from "lucide-react";
import type { ProjectDomain } from "@/lib/control-plane";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface ProjectDomainManageProps {
  projectId: string;
  projectName: string;
}

const REGISTRAR_GUIDES: Record<
  string,
  { name: string; url: string; steps: string[] }
> = {
  cloudflare: {
    name: "Cloudflare",
    url: "https://dash.cloudflare.com",
    steps: [
      "Log into Cloudflare and select your domain zone.",
      "Navigate to DNS → Records and click 'Add record'.",
      "Select the Record Type shown below (CNAME for subdomains, A for apex).",
      "Enter the Name/Host (e.g. 'app' or '@') and Target/Value exactly as indicated.",
      "Important: Turn Proxy status OFF (set to DNS only / grey cloud) during initial verification.",
      "Click Save.",
    ],
  },
  godaddy: {
    name: "GoDaddy",
    url: "https://dcc.godaddy.com/manage/dns",
    steps: [
      "Go to your GoDaddy Domain Portfolio and select your domain.",
      "Click on DNS or Manage DNS.",
      "Click 'Add New Record' in the DNS Records section.",
      "Select the Record Type (CNAME or A) from the dropdown.",
      "In the Name field, enter the Host value (e.g. 'app' or '@').",
      "In the Value field, paste the target record value.",
      "Set TTL to 1/2 hour or 1 hour and click Save.",
    ],
  },
  namecheap: {
    name: "Namecheap",
    url: "https://ap.www.namecheap.com/domains/list/",
    steps: [
      "Sign in to your Namecheap dashboard and click Manage next to your domain.",
      "Go to the 'Advanced DNS' tab.",
      "In the Host Records section, click 'Add New Record'.",
      "Choose Record Type (CNAME Record or A Record).",
      "Enter Host and Value exactly as specified below.",
      "Set TTL to Automatic and click the green checkmark to save.",
    ],
  },
  hostinger: {
    name: "Hostinger",
    url: "https://hpanel.hostinger.com",
    steps: [
      "Log into hPanel and navigate to Domains.",
      "Select your domain and click 'DNS / Nameservers'.",
      "Under 'Manage DNS records', select the record type.",
      "Fill in Name and Points to / Content with the values provided below.",
      "Click 'Add Record'.",
    ],
  },
  bigrock: {
    name: "BigRock",
    url: "https://manage.bigrock.com",
    steps: [
      "Log in to your BigRock Control Panel and search for your domain.",
      "Click on DNS Management.",
      "Click 'Manage DNS' then choose CNAME Records or A Records.",
      "Click 'Add CNAME Record' or 'Add A Record'.",
      "Enter the Host Name and Value as shown below.",
      "Click 'Add Record' to submit.",
    ],
  },
};

export function ProjectDomainManage({
  projectId,
  projectName,
}: ProjectDomainManageProps) {
  const [domains, setDomains] = useState<ProjectDomain[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Form state
  const [newHostname, setNewHostname] = useState("");
  const [formatError, setFormatError] = useState<string | null>(null);
  const [addingDomain, setAddingDomain] = useState(false);
  const [addSuccess, setAddSuccess] = useState(false);

  // Active registrar guide tab
  const [activeRegistrar, setActiveRegistrar] = useState("cloudflare");

  // Per-domain action states
  const [verifyingId, setVerifyingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [settingPrimaryId, setSettingPrimaryId] = useState<string | null>(null);
  const [copiedField, setCopiedField] = useState<string | null>(null);

  const fetchDomains = useCallback(async () => {
    try {
      const res = await fetch(`/api/projects/${encodeURIComponent(projectId)}/domains`);
      if (!res.ok) {
        throw new Error("Failed to load project domains");
      }
      const data = await res.json();
      setDomains(data.domains || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load domains");
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const res = await fetch(`/api/projects/${encodeURIComponent(projectId)}/domains`);
        if (active && res.ok) {
          const data = await res.json();
          setDomains(data.domains || []);
        }
      } catch (err) {
        if (active) setError(err instanceof Error ? err.message : "Failed to load domains");
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [projectId]);

  // Live RFC 1123 hostname validator
  const validateHostname = (input: string) => {
    const trimmed = input.trim().toLowerCase();
    if (!trimmed) {
      setFormatError(null);
      return;
    }
    if (trimmed.includes("://")) {
      setFormatError("Enter only the domain name without http:// or https://");
      return;
    }
    if (trimmed.includes("/")) {
      setFormatError("Domain cannot contain paths or trailing slashes");
      return;
    }
    if (/^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$/.test(trimmed)) {
      setFormatError("IP addresses are not allowed. Please enter a domain name.");
      return;
    }
    const regex = /^([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$/;
    if (!regex.test(trimmed)) {
      setFormatError("Please enter a valid hostname (e.g. app.mycompany.com or mycompany.com)");
      return;
    }
    setFormatError(null);
  };

  const handleHostnameChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setNewHostname(val);
    validateHostname(val);
  };

  const handleAddDomain = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newHostname.trim() || formatError) return;

    setAddingDomain(true);
    setError(null);
    setAddSuccess(false);

    try {
      const res = await fetch(`/api/projects/${encodeURIComponent(projectId)}/domains`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ hostname: newHostname.trim() }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error || "Failed to add domain");
      }

      setNewHostname("");
      setAddSuccess(true);
      setTimeout(() => setAddSuccess(false), 4000);
      await fetchDomains();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add domain");
    } finally {
      setAddingDomain(false);
    }
  };

  const handleVerify = async (domainId: string) => {
    setVerifyingId(domainId);
    setError(null);
    try {
      const res = await fetch(
        `/api/projects/${encodeURIComponent(projectId)}/domains/${encodeURIComponent(domainId)}/verify`,
        { method: "POST" }
      );
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error || "Verification check failed");
      }
      await fetchDomains();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Verification check failed");
    } finally {
      setVerifyingId(null);
    }
  };

  const handleSetPrimary = async (domainId: string) => {
    setSettingPrimaryId(domainId);
    try {
      const res = await fetch(
        `/api/projects/${encodeURIComponent(projectId)}/domains/${encodeURIComponent(domainId)}`,
        { method: "PUT" }
      );
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.error || "Failed to set primary domain");
      }
      await fetchDomains();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to set primary domain");
    } finally {
      setSettingPrimaryId(null);
    }
  };

  const handleDelete = async (domainId: string) => {
    if (!window.confirm("Are you sure you want to disconnect this domain? Your app will no longer be reachable at this address.")) {
      return;
    }
    setDeletingId(domainId);
    try {
      const res = await fetch(
        `/api/projects/${encodeURIComponent(projectId)}/domains/${encodeURIComponent(domainId)}`,
        { method: "DELETE" }
      );
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.error || "Failed to delete domain");
      }
      await fetchDomains();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete domain");
    } finally {
      setDeletingId(null);
    }
  };

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedField(id);
    setTimeout(() => setCopiedField(null), 2000);
  };

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <Card className="border-border/60 bg-gradient-to-r from-card via-card to-primary/5 shadow-sm">
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="flex size-10 items-center justify-center rounded-lg bg-primary/10 text-primary ring-1 ring-primary/25">
              <Globe className="size-5" />
            </div>
            <div>
              <CardTitle className="text-xl font-bold tracking-tight">
                Custom Domains
              </CardTitle>
              <CardDescription className="text-sm">
                Bring your own domain from any registrar (Cloudflare, GoDaddy, Namecheap, etc.) and connect it to {projectName}.
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-2 text-xs text-muted-foreground bg-muted/40 p-2.5 rounded-md border border-border/40">
            <Info className="size-4 shrink-0 text-primary" />
            <span>
              <strong>Zero platform markup:</strong> Buy a domain from any registrar, then point your DNS records here. OmniStackAI never charges domain fees or renewals.
            </span>
          </div>
        </CardContent>
      </Card>

      {/* Global Alerts */}
      {error && (
        <div className="flex items-start gap-3 rounded-lg border border-destructive/40 bg-destructive/10 p-4 text-destructive">
          <AlertCircle className="size-5 shrink-0 mt-0.5" />
          <div className="text-sm">
            <p className="font-semibold">Domain Error</p>
            <p className="mt-0.5">{error}</p>
          </div>
        </div>
      )}

      {addSuccess && (
        <div className="flex items-start gap-3 rounded-lg border border-emerald-500/40 bg-emerald-500/10 p-4 text-emerald-600 dark:text-emerald-400">
          <CheckCircle2 className="size-5 shrink-0 mt-0.5" />
          <div className="text-sm">
            <p className="font-semibold">Domain Added Successfully</p>
            <p className="mt-0.5">
              Configure the DNS record below in your registrar&apos;s dashboard to complete setup.
            </p>
          </div>
        </div>
      )}

      {/* Add Domain Section */}
      <Card className="border-border/60">
        <CardHeader>
          <CardTitle className="text-base font-semibold">Connect a Custom Domain</CardTitle>
          <CardDescription className="text-xs">
            Enter the apex domain (e.g. <code>example.com</code>) or subdomain (e.g. <code>app.example.com</code>) you own.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleAddDomain} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="hostname" className="text-xs font-medium">
                Hostname
              </Label>
              <div className="flex flex-col sm:flex-row gap-2">
                <div className="relative flex-1">
                  <Input
                    id="hostname"
                    type="text"
                    placeholder="e.g. app.mycompany.com"
                    value={newHostname}
                    onChange={handleHostnameChange}
                    className={`font-mono text-sm ${formatError ? "border-destructive focus-visible:ring-destructive" : ""}`}
                    disabled={addingDomain}
                  />
                </div>
                <Button
                  type="submit"
                  disabled={addingDomain || !newHostname.trim() || !!formatError}
                  className="gap-2 shrink-0"
                >
                  {addingDomain ? (
                    <>
                      <Loader2 className="size-4 animate-spin" />
                      Connecting…
                    </>
                  ) : (
                    <>
                      <Plus className="size-4" />
                      Add Domain
                    </>
                  )}
                </Button>
              </div>
              {formatError && (
                <p className="text-xs text-destructive flex items-center gap-1.5 mt-1">
                  <AlertCircle className="size-3.5" />
                  {formatError}
                </p>
              )}
            </div>
          </form>
        </CardContent>
      </Card>

      {/* Existing Domains List */}
      <div className="space-y-4">
        <h3 className="text-base font-semibold tracking-tight">Connected Domains ({domains.length})</h3>

        {loading ? (
          <div className="flex items-center justify-center p-12 text-muted-foreground">
            <Loader2 className="size-6 animate-spin mr-2" />
            <span>Loading domains…</span>
          </div>
        ) : domains.length === 0 ? (
          <Card className="border-dashed border-border/80 bg-muted/20">
            <CardContent className="flex flex-col items-center justify-center py-12 text-center">
              <Globe className="size-10 text-muted-foreground/60 mb-3" />
              <p className="text-sm font-medium text-foreground">No custom domains connected</p>
              <p className="text-xs text-muted-foreground mt-1 max-w-sm">
                Add your own domain above to publish your project on a branded, professional URL with automatic SSL certificate.
              </p>
            </CardContent>
          </Card>
        ) : (
          domains.map((dom) => (
            <Card key={dom.id} className="border-border/60 overflow-hidden shadow-sm">
              <CardHeader className="bg-muted/30 border-b border-border/40 py-3.5 px-4 sm:px-6">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="flex items-center gap-2.5">
                    <span className="font-mono text-base font-semibold text-foreground">
                      {dom.hostname}
                    </span>
                    {dom.is_primary && (
                      <Badge variant="secondary" className="bg-primary/10 text-primary border-primary/20 text-[10px] uppercase font-bold tracking-wider">
                        Primary
                      </Badge>
                    )}
                  </div>

                  <div className="flex items-center gap-2">
                    {/* DNS Status Badge */}
                    {dom.status === "verified" ? (
                      <Badge variant="outline" className="border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 gap-1 text-xs">
                        <Check className="size-3" /> DNS Connected
                      </Badge>
                    ) : dom.status === "verifying" ? (
                      <Badge variant="outline" className="border-blue-500/30 bg-blue-500/10 text-blue-600 dark:text-blue-400 gap-1 text-xs">
                        <Loader2 className="size-3 animate-spin" /> DNS Resolving
                      </Badge>
                    ) : (
                      <Badge variant="outline" className="border-amber-500/30 bg-amber-500/10 text-amber-600 dark:text-amber-400 gap-1 text-xs">
                        <Clock className="size-3" /> DNS Pending
                      </Badge>
                    )}

                    {/* TLS Status Badge */}
                    {dom.tls_status === "issued" ? (
                      <Badge variant="outline" className="border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 gap-1 text-xs">
                        <Lock className="size-3" /> SSL Active
                      </Badge>
                    ) : (
                      <Badge variant="outline" className="border-muted-foreground/30 bg-muted/40 text-muted-foreground gap-1 text-xs">
                        <ShieldCheck className="size-3" /> SSL Pending
                      </Badge>
                    )}
                  </div>
                </div>
              </CardHeader>

              <CardContent className="p-4 sm:p-6 space-y-6">
                {/* DNS Configuration Box */}
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                      Required DNS Record
                    </span>
                    <span className="text-xs text-muted-foreground">
                      Provider: <strong className="capitalize">{dom.provider}</strong>
                    </span>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-4 gap-3 bg-muted/40 border border-border/60 rounded-lg p-3.5">
                    {/* Record Type */}
                    <div className="space-y-1">
                      <span className="text-[11px] text-muted-foreground uppercase font-medium">Type</span>
                      <div className="flex items-center justify-between font-mono text-sm font-semibold p-2 bg-background rounded border border-border/50">
                        <span>{dom.record_type}</span>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="size-6 text-muted-foreground hover:text-foreground"
                          onClick={() => copyToClipboard(dom.record_type, `type-${dom.id}`)}
                          title="Copy record type"
                        >
                          {copiedField === `type-${dom.id}` ? (
                            <Check className="size-3.5 text-emerald-500" />
                          ) : (
                            <Copy className="size-3.5" />
                          )}
                        </Button>
                      </div>
                    </div>

                    {/* Record Host / Name */}
                    <div className="space-y-1">
                      <span className="text-[11px] text-muted-foreground uppercase font-medium">Name / Host</span>
                      <div className="flex items-center justify-between font-mono text-sm font-semibold p-2 bg-background rounded border border-border/50">
                        <span className="truncate">{dom.record_name || "@"}</span>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="size-6 text-muted-foreground hover:text-foreground"
                          onClick={() => copyToClipboard(dom.record_name || "@", `name-${dom.id}`)}
                          title="Copy host name"
                        >
                          {copiedField === `name-${dom.id}` ? (
                            <Check className="size-3.5 text-emerald-500" />
                          ) : (
                            <Copy className="size-3.5" />
                          )}
                        </Button>
                      </div>
                    </div>

                    {/* Record Target / Value */}
                    <div className="space-y-1 md:col-span-2">
                      <span className="text-[11px] text-muted-foreground uppercase font-medium">Value / Target</span>
                      <div className="flex items-center justify-between font-mono text-sm font-semibold p-2 bg-background rounded border border-border/50">
                        <span className="truncate">{dom.record_value}</span>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="size-6 text-muted-foreground hover:text-foreground shrink-0"
                          onClick={() => copyToClipboard(dom.record_value, `value-${dom.id}`)}
                          title="Copy value"
                        >
                          {copiedField === `value-${dom.id}` ? (
                            <Check className="size-3.5 text-emerald-500" />
                          ) : (
                            <Copy className="size-3.5" />
                          )}
                        </Button>
                      </div>
                    </div>
                  </div>

                  {dom.error && dom.status !== "verified" && (
                    <div className="flex items-center gap-2 text-xs text-amber-600 dark:text-amber-400 bg-amber-500/10 border border-amber-500/20 p-2.5 rounded">
                      <Clock className="size-4 shrink-0" />
                      <span>{dom.error}</span>
                    </div>
                  )}

                  {dom.status === "verified" && (
                    <div className="flex items-center justify-between bg-emerald-500/10 border border-emerald-500/20 text-emerald-600 dark:text-emerald-400 p-3 rounded-lg text-sm">
                      <span className="flex items-center gap-2">
                        <CheckCircle2 className="size-4" />
                        Domain is active and serving traffic over HTTPS.
                      </span>
                      <a
                        href={`https://${dom.hostname}`}
                        target="_blank"
                        rel="noreferrer"
                        className="flex items-center gap-1 font-semibold underline underline-offset-4 hover:opacity-80"
                      >
                        Visit Site <ExternalLink className="size-3.5" />
                      </a>
                    </div>
                  )}
                </div>

                {/* Registrar Instructions Accordion / Tabs */}
                {dom.status !== "verified" && (
                  <div className="border border-border/50 rounded-lg p-3.5 bg-muted/20 space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold flex items-center gap-1.5 text-foreground">
                        <HelpCircle className="size-3.5 text-primary" />
                        Registrar Setup Instructions
                      </span>
                      <div className="flex gap-1">
                        {Object.keys(REGISTRAR_GUIDES).map((regKey) => (
                          <button
                            key={regKey}
                            type="button"
                            onClick={() => setActiveRegistrar(regKey)}
                            className={`px-2 py-1 text-[11px] rounded font-medium transition-colors ${
                              activeRegistrar === regKey
                                ? "bg-primary text-primary-foreground"
                                : "text-muted-foreground hover:text-foreground bg-muted/50"
                            }`}
                          >
                            {REGISTRAR_GUIDES[regKey].name}
                          </button>
                        ))}
                      </div>
                    </div>

                    <div className="text-xs text-muted-foreground space-y-1.5 pt-1">
                      <p className="font-medium text-foreground">
                        How to configure DNS on {REGISTRAR_GUIDES[activeRegistrar].name}:
                      </p>
                      <ol className="list-decimal list-inside space-y-1 pl-1">
                        {REGISTRAR_GUIDES[activeRegistrar].steps.map((step, idx) => (
                          <li key={idx} className="leading-relaxed">
                            {step}
                          </li>
                        ))}
                      </ol>
                      <div className="pt-2">
                        <a
                          href={REGISTRAR_GUIDES[activeRegistrar].url}
                          target="_blank"
                          rel="noreferrer"
                          className="inline-flex items-center gap-1 text-primary hover:underline font-medium text-[11px]"
                        >
                          Open {REGISTRAR_GUIDES[activeRegistrar].name} DNS Dashboard{" "}
                          <ExternalLink className="size-3" />
                        </a>
                      </div>
                    </div>

                    <div className="text-[11px] text-muted-foreground bg-muted/40 p-2 rounded border border-border/30">
                      <strong>DNS Propagation Notice:</strong> DNS record updates can take anywhere from a few minutes up to 48 hours to propagate worldwide depending on your registrar&apos;s TTL settings.
                    </div>
                  </div>
                )}
              </CardContent>

              <CardFooter className="bg-muted/20 border-t border-border/40 py-3 px-4 sm:px-6 flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleVerify(dom.id)}
                    disabled={verifyingId === dom.id}
                    className="gap-1.5 text-xs font-medium"
                  >
                    <RefreshCw className={`size-3.5 ${verifyingId === dom.id ? "animate-spin" : ""}`} />
                    {verifyingId === dom.id ? "Checking DNS…" : "Check DNS now"}
                  </Button>

                  {!dom.is_primary && dom.status === "verified" && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleSetPrimary(dom.id)}
                      disabled={settingPrimaryId === dom.id}
                      className="text-xs text-muted-foreground hover:text-foreground"
                    >
                      Make Primary
                    </Button>
                  )}
                </div>

                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleDelete(dom.id)}
                  disabled={deletingId === dom.id}
                  className="text-xs text-destructive hover:text-destructive hover:bg-destructive/10 gap-1"
                >
                  <Trash2 className="size-3.5" />
                  Remove
                </Button>
              </CardFooter>
            </Card>
          ))
        )}
      </div>
    </div>
  );
}
