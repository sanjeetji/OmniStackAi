import type { Queryable } from "../db.ts";
import { hub } from "../lib/events.ts";

export async function notify(client: Queryable, userId: string, kind: string, title: string, body = ""): Promise<void> {
  const result = await client.query(
    `INSERT INTO notifications (user_id, kind, title, body) VALUES ($1, $2, $3, $4)
     RETURNING id, kind, title, body, read_at, created_at`,
    [userId, kind, title, body],
  );
  hub.publish(`user:${userId}`, "notification", result.rows[0]);
}

export async function audit(
  client: Queryable,
  actorId: string | null,
  action: string,
  entity: string,
  entityId: string,
  detail: Record<string, unknown> = {},
): Promise<void> {
  await client.query(
    "INSERT INTO audit_log (actor_id, action, entity, entity_id, detail) VALUES ($1, $2, $3, $4, $5)",
    [actorId, action, entity, entityId, JSON.stringify(detail)],
  );
}
