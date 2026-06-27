/**
 * Agent client — the single integration seam between the UI and the agents.
 *
 * Streams Server-Sent Events from the FastAPI bridge (server/app.py), which
 * drives the real LangGraph pipeline: Apify restaurant search at the requested
 * location, the scoring system, Talabat/Tavily deal lookup, RAG nutrition, and
 * the order finalizer. There is no mock path — results are always live.
 */
import type { AgentEvent } from "./types";

export type ResumeValueT =
  | { kind: "restaurant"; index: number }
  | { kind: "deal"; index: number; quantity: number }
  | { kind: "no_deals"; index: number };

export interface AgentClient {
  /** Start a run for a fresh user query at the given location. */
  start(threadId: string, query: string, location: string): AsyncGenerator<AgentEvent>;
  /** Resume a paused (interrupted) run with the user's selection. */
  resume(threadId: string, value: ResumeValueT): AsyncGenerator<AgentEvent>;
}

class LiveAgentClient implements AgentClient {
  // Talk to the FastAPI bridge DIRECTLY (not through the Next.js rewrite, which
  // buffers SSE and would freeze the stream until the whole run finishes).
  // CORS on the bridge allows the dev origin.
  private base = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

  start(threadId: string, query: string, location: string): AsyncGenerator<AgentEvent> {
    return this.stream(`${this.base}/chat`, {
      thread_id: threadId,
      query,
      location,
    });
  }

  resume(threadId: string, value: ResumeValueT): AsyncGenerator<AgentEvent> {
    return this.stream(`${this.base}/resume`, { thread_id: threadId, resume: value });
  }

  private async *stream(url: string, body: unknown): AsyncGenerator<AgentEvent> {
    let res: Response;
    try {
      res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
    } catch {
      yield {
        type: "error",
        message: "تعذّر الاتصال بالخادم. تأكد إن السيرفر شغّال على المنفذ 8000.",
      };
      return;
    }

    if (!res.ok || !res.body) {
      yield { type: "error", message: `خطأ من الخادم (${res.status}).` };
      return;
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      const frames = buffer.split("\n\n");
      buffer = frames.pop() ?? "";
      for (const frame of frames) {
        const line = frame.split("\n").find((l) => l.startsWith("data:"));
        if (!line) continue;
        const json = line.slice(5).trim();
        if (!json || json === "[DONE]") continue;
        try {
          yield JSON.parse(json) as AgentEvent;
        } catch {
          /* ignore malformed frame */
        }
      }
    }
  }
}

export const agentClient: AgentClient = new LiveAgentClient();
export { LiveAgentClient };
