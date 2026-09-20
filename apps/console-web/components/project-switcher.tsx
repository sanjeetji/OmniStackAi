"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Check,
  ChevronDown,
  FolderTree,
  Plus,
  Settings,
} from "lucide-react";
import type { Project } from "@/lib/control-plane";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

interface ProjectSwitcherProps {
  currentProject?: Project | null;
  currentProjectId?: string | null;
  currentProjectName?: string | null;
}

export default function ProjectSwitcher({
  currentProject,
  currentProjectId,
  currentProjectName,
}: ProjectSwitcherProps) {
  const router = useRouter();
  const [recentProjects, setRecentProjects] = useState<Project[]>([]);
  const [loaded, setLoaded] = useState(false);

  const activeId = currentProject?.id || currentProjectId;
  const displayName = currentProject?.name || currentProjectName || "New project";

  useEffect(() => {
    let active = true;
    async function loadRecent() {
      try {
        const resp = await fetch("/api/projects?status=active&sort=updated&limit=5");
        if (resp.ok && active) {
          const data = await resp.json();
          setRecentProjects(data.projects ?? []);
        }
      } catch {
        // quiet fallback
      } finally {
        if (active) setLoaded(true);
      }
    }
    loadRecent();
    return () => {
      active = false;
    };
  }, []);

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          className="h-8 max-w-[220px] justify-between gap-1.5 px-2 font-medium"
        >
          <span className="truncate text-sm font-semibold">{displayName}</span>
          <ChevronDown className="size-3.5 shrink-0 opacity-60" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-56">
        <DropdownMenuLabel className="text-xs font-normal text-muted-foreground">
          Recent projects
        </DropdownMenuLabel>
        {recentProjects.length > 0 ? (
          recentProjects.map((p) => {
            const isCurrent = p.id === activeId;
            return (
              <DropdownMenuItem
                key={p.id}
                onClick={() => router.push(`/studio/${p.id}`)}
                className="flex items-center justify-between"
              >
                <span className="truncate font-medium">{p.name}</span>
                {isCurrent && <Check className="size-3.5 text-primary" />}
              </DropdownMenuItem>
            );
          })
        ) : (
          <div className="px-2 py-1.5 text-xs text-muted-foreground">
            No saved projects
          </div>
        )}

        <DropdownMenuSeparator />

        {activeId && (
          <DropdownMenuItem asChild>
            <Link href={`/studio/${activeId}/manage`}>
              <Settings className="mr-2 size-3.5" />
              Manage project
            </Link>
          </DropdownMenuItem>
        )}

        <DropdownMenuItem asChild>
          <Link href="/projects">
            <FolderTree className="mr-2 size-3.5" />
            All projects…
          </Link>
        </DropdownMenuItem>

        <DropdownMenuItem asChild>
          <Link href="/studio">
            <Plus className="mr-2 size-3.5" />
            New app
          </Link>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
