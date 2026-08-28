import type { ChatApiResponse } from "./types";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");

export class ApiError extends Error {
  constructor(message: string, public status: number, public retryAfter?: string | null) {
    super(message);
  }
}

export async function sendChatMessage(message: string, conversationId: string | null | undefined, token: string): Promise<ChatApiResponse> {
  const response = await fetch(`${API_BASE_URL}/chat`, {
    method: "POST",
    headers: { "Authorization": `Bearer ${token}`, "Content-Type": "application/json" },
    body: JSON.stringify({ message, ...(conversationId ? { conversation_id: conversationId } : {}) }),
  });

  if (!response.ok) {
    let detail = "The service could not process your message.";
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) detail = body.detail;
    } catch { /* The API returned a non-JSON error page. */ }
    throw new ApiError(detail, response.status, response.headers.get("Retry-After"));
  }
  return response.json() as Promise<ChatApiResponse>;
}
