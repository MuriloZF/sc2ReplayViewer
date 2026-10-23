import type {
  BuildOrderResponse,
  ReplayMapMetadata,
  ReplaySummary,
  TimelineResponse,
  WinProbabilityResponse,
} from "./types";

const API_ROOT = "/api/v1";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_ROOT}${path}`, options);
  if (!response.ok) {
    let message = `Request failed with status ${response.status}`;
    try {
      const payload = (await response.json()) as { detail?: string };
      message = payload.detail ?? message;
    } catch {
      // Non-JSON server errors still receive a useful status-based message.
    }
    throw new ApiError(message, response.status);
  }
  return (await response.json()) as T;
}

export async function listReplays(): Promise<ReplaySummary[]> {
  const response = await request<{ items: ReplaySummary[] }>("/replays");
  return response.items;
}

export function uploadReplay(file: File, sampleSeconds = 5): Promise<ReplaySummary> {
  const body = new FormData();
  body.append("replay", file);
  return request<ReplaySummary>(`/replays?sample_seconds=${sampleSeconds}`, {
    method: "POST",
    body,
  });
}

export function getTimeline(replayId: string): Promise<TimelineResponse> {
  return request<TimelineResponse>(`/replays/${replayId}/timeline`);
}

export function getWinProbability(replayId: string): Promise<WinProbabilityResponse> {
  return request<WinProbabilityResponse>(`/replays/${encodeURIComponent(replayId)}/win-probability`);
}

export function getBuildOrder(replayId: string): Promise<BuildOrderResponse> {
  return request<BuildOrderResponse>(`/replays/${replayId}/build-order`);
}

export function getMinimapUrl(replayId: string): string {
  return `${API_ROOT}/replays/${encodeURIComponent(replayId)}/minimap`;
}

export function getMapMetadata(replayId: string): Promise<ReplayMapMetadata> {
  return request<ReplayMapMetadata>(`/replays/${replayId}/map-metadata`);
}
