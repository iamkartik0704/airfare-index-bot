import { authTables } from "@convex-dev/auth/server";
import { defineSchema, defineTable } from "convex/server";
import { Infer, v } from "convex/values";

// default user roles. can add / remove based on the project as needed
export const ROLES = {
  ADMIN: "admin",
  USER: "user",
  MEMBER: "member",
} as const;

export const roleValidator = v.union(
  v.literal(ROLES.ADMIN),
  v.literal(ROLES.USER),
  v.literal(ROLES.MEMBER),
);
export type Role = Infer<typeof roleValidator>;

const schema = defineSchema(
  {
    // default auth tables using convex auth.
    ...authTables, // do not remove or modify

    // the users table is the default users table that is brought in by the authTables
    users: defineTable({
      name: v.optional(v.string()), // name of the user. do not remove
      image: v.optional(v.string()), // image of the user. do not remove
      email: v.optional(v.string()), // email of the user. do not remove
      emailVerificationTime: v.optional(v.number()), // email verification time. do not remove
      isAnonymous: v.optional(v.boolean()), // is the user anonymous. do not remove

      role: v.optional(roleValidator), // role of the user. do not remove
    }).index("email", ["email"]), // index for the email. do not remove or modify

    // -------------------------------------------------------- SAFAR ---------
    // Single-row pipeline state. `epoch` is bumped by every crawl: the fare
    // engine is a pure function of (date, route, carrier, channel, epoch), so
    // re-running the collector genuinely re-observes the market and every
    // reactive query downstream recomputes — that is the demo.
    appState: defineTable({
      epoch: v.number(),
      lastRunAt: v.optional(v.string()),
      lastRunDate: v.optional(v.string()),
      runs: v.number(),
    }),

    // One row per (run, source): the collector registry's audit trail.
    scrapeRuns: defineTable({
      epoch: v.number(),
      date: v.string(),
      sourceId: v.string(),
      sourceName: v.string(),
      kind: v.union(v.literal("airline"), v.literal("ota")),
      status: v.union(v.literal("ok"), v.literal("degraded"), v.literal("blocked")),
      startedAt: v.string(),
      durationMs: v.number(),
      requests: v.number(),
      rawQuotes: v.number(),
      httpErrors: v.number(),
      retries: v.number(),
      blockEvents: v.number(),
      robotsAllowed: v.boolean(),
      crawlDelaySec: v.number(),
      rateLimitPerMin: v.number(),
      notes: v.string(),
      hue: v.string(),
    })
      .index("by_epoch", ["epoch"])
      .index("by_date", ["date"]),

    // Publication ledger — what was released to NSO/RBI and when.
    releases: defineTable({
      period: v.string(),
      frequency: v.union(v.literal("daily"), v.literal("weekly"), v.literal("monthly")),
      value: v.number(),
      publishedAt: v.string(),
      channels: v.array(v.string()),
    }).index("by_period", ["period"]),

    // API credentials for the NSO / RBI / academic consumers.
    apiKeys: defineTable({
      label: v.string(),
      keyHash: v.string(),
      org: v.string(),
      createdAt: v.string(),
      lastUsedAt: v.optional(v.string()),
      scopes: v.array(v.string()),
    }).index("by_hash", ["keyHash"]),

    // tableName: defineTable({
    //   ...
    //   // table fields
    // }).index("by_field", ["field"])
  },
  {
    schemaValidation: false,
  },
);

export default schema;
