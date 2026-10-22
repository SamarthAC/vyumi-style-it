import type { Product } from "./catalog";

const base = (import.meta.env.VITE_API_BASE_URL || "/api").replace(/\/$/, "");
export function assetUrl(path: string): string {
  // Result paths are backend-relative. Do not allow a server response to navigate
  // the user to an arbitrary origin or protocol.
  if (!path.startsWith("/") || path.startsWith("//"))
    throw new Error("Invalid image address returned by the server.");
  return `${base}${path}`;
}

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const signal = options.signal
    ? AbortSignal.any([options.signal, AbortSignal.timeout(30_000)])
    : AbortSignal.timeout(30_000);
  let response: Response;
  try {
    response = await fetch(`${base}${path}`, { ...options, signal });
  } catch (error) {
    if (options.signal?.aborted) throw error;
    throw new ApiError(
      "We couldn’t reach the studio. Check your connection and try again.",
      0,
    );
  }
  if (!response.ok) {
    let message = `The request could not be completed (${response.status}).`;
    try {
      const body = await response.json();
      if (typeof body.detail === "string") message = body.detail;
      else if (Array.isArray(body.detail))
        message = body.detail.map((d: { msg: string }) => d.msg).join(". ");
    } catch {
      /* Keep the HTTP fallback for non-JSON gateway failures. */
    }
    throw new ApiError(message, response.status);
  }
  return response.json() as Promise<T>;
}

export interface Health {
  status: string;
  engine_ready: boolean;
  product_count: number;
}
export type Job =
  | { status: "pending" | "processing" }
  | { status: "completed"; result_image_url: string }
  | { status: "failed"; error_code: string; message: string };

export const api = {
  products: (signal?: AbortSignal) =>
    request<Product[]>("/products", { signal }),
  health: (signal?: AbortSignal) => request<Health>("/health", { signal }),
  upload: (file: File, signal: AbortSignal) => {
    const body = new FormData();
    body.append("file", file);
    return request<{ user_image_id: string }>("/style-it/upload", {
      method: "POST",
      body,
      signal,
    });
  },
  generate: (image: string, product: string, signal: AbortSignal) =>
    request<{ job_id: string; status: string }>("/style-it/generate", {
      method: "POST",
      signal,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_image_id: image, product_id: product }),
    }),
  job: (id: string, signal: AbortSignal) =>
    request<Job>(`/style-it/jobs/${encodeURIComponent(id)}`, { signal }),
};

export function wait(ms: number, signal: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal.aborted) {
      reject(new DOMException("Cancelled", "AbortError"));
      return;
    }
    const cancel = () => {
      clearTimeout(timer);
      reject(new DOMException("Cancelled", "AbortError"));
    };
    const timer = setTimeout(() => {
      signal.removeEventListener("abort", cancel);
      resolve();
    }, ms);
    signal.addEventListener("abort", cancel, { once: true });
  });
}
