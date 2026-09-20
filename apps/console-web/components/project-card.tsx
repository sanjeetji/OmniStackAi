"use client";

import Link from "next/link";
import {
  Archive,
  Coins,
  FileCode2,
  FolderTree,
  MoreVertical,
  Pencil,
  Trash2,
} from "lucide-react";
import type { Project } from "@/lib/control-plane";
import { formatRelativeTime } from "@/lib/time";
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
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

interface ProjectCardProps {
  project: Project;
  onRename?: (project: Project) => void;
  onArchive?: (project: Project) => void;
  onDelete?: (project: Project) => void;
}

export default function ProjectCard({
  project,
  onRename,
  onArchive,
  onDelete,
}: ProjectCardProps) {
  const displayPrompt = project.last_prompt || project.description || "No prompt recorded";

  return (
    <Card className="group relative flex flex-col justify-between transition-all hover:border-foreground/30 hover:shadow-sm">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-2">
          <Link
            href={`/studio/${project.id}`}
            className="line-clamp-1 font-semibold hover:underline focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
          >
            <CardTitle className="text-base font-medium">{project.name}</CardTitle>
          </Link>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="icon-xs"
                className="opacity-0 group-hover:opacity-100 focus:opacity-100 transition-opacity"
                aria-label="Project actions"
              >
                <MoreVertical className="size-3.5" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-40">
              <DropdownMenuItem asChild>
                <Link href={`/studio/${project.id}`}>
                  <FolderTree className="mr-2 size-3.5" />
                  Open
                </Link>
              </DropdownMenuItem>
              <DropdownMenuItem asChild>
                <Link href={`/studio/${project.id}/manage`}>
                  Manage
                </Link>
              </DropdownMenuItem>
              {onRename && (
                <DropdownMenuItem onClick={() => onRename(project)}>
                  <Pencil className="mr-2 size-3.5" />
                  Rename
                </DropdownMenuItem>
              )}
              {onArchive && (
                <DropdownMenuItem onClick={() => onArchive(project)}>
                  <Archive className="mr-2 size-3.5" />
                  {project.status === "archived" ? "Unarchive" : "Archive"}
                </DropdownMenuItem>
              )}
              {onDelete && (
                <>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem
                    onClick={() => onDelete(project)}
                    className="text-destructive focus:text-destructive"
                  >
                    <Trash2 className="mr-2 size-3.5" />
                    Delete
                  </DropdownMenuItem>
                </>
              )}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
        <CardDescription className="line-clamp-2 text-xs">
          {displayPrompt}
        </CardDescription>
      </CardHeader>

      <CardContent className="pb-3">
        {project.entities && project.entities.length > 0 ? (
          <div className="flex flex-wrap gap-1">
            {project.entities.slice(0, 3).map((entity) => (
              <Badge key={entity} variant="secondary" className="px-1.5 py-0 text-[10px]">
                {entity}
              </Badge>
            ))}
            {project.entities.length > 3 && (
              <Badge variant="outline" className="px-1.5 py-0 text-[10px] text-muted-foreground">
                +{project.entities.length - 3}
              </Badge>
            )}
          </div>
        ) : (
          <p className="text-xs text-muted-foreground">No entities</p>
        )}
      </CardContent>

      <CardFooter className="flex items-center justify-between border-t bg-muted/20 px-4 py-2 text-xs text-muted-foreground">
        <span title={new Date(project.updated_at).toLocaleString()}>
          {formatRelativeTime(project.updated_at)}
        </span>
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1" title={`${project.file_count} files`}>
            <FileCode2 className="size-3" />
            {project.file_count}
          </span>
          <span className="flex items-center gap-1" title={`${project.credits_spent} credits spent`}>
            <Coins className="size-3" />
            {project.credits_spent}
          </span>
        </div>
      </CardFooter>
    </Card>
  );
}
