type Level = "debug" | "info" | "warn" | "error";

const LEVEL_PRIORITY: Record<Level, number> = {
  debug: 0,
  info: 1,
  warn: 2,
  error: 3,
};

const currentLevel: Level =
  process.env.NODE_ENV === "production" ? "info" : "debug";

function shouldLog(level: Level): boolean {
  return LEVEL_PRIORITY[level] >= LEVEL_PRIORITY[currentLevel];
}

function fmt(level: Level, tag: string, msg: string): string {
  return `[${level.toUpperCase()}][${tag}] ${msg}`;
}

export const logger = {
  debug(tag: string, msg: string, data?: unknown) {
    if (!shouldLog("debug")) return;
    console.debug(fmt("debug", tag, msg), data ?? "");
  },
  info(tag: string, msg: string, data?: unknown) {
    if (!shouldLog("info")) return;
    console.info(fmt("info", tag, msg), data ?? "");
  },
  warn(tag: string, msg: string, data?: unknown) {
    if (!shouldLog("warn")) return;
    console.warn(fmt("warn", tag, msg), data ?? "");
  },
  error(tag: string, msg: string, data?: unknown) {
    if (!shouldLog("error")) return;
    console.error(fmt("error", tag, msg), data ?? "");
  },
};
