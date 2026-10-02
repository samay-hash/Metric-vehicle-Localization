import { isAxiosError } from 'axios';
export function errorMessage(error: unknown, fallback = 'Request failed'): string {
    if (isAxiosError<{
        detail?: unknown;
    }>(error)) {
        const detail = error.response?.data?.detail;
        if (typeof detail === 'string')
            return detail;
    }
    return error instanceof Error ? error.message : fallback;
}
export function errorStatus(error: unknown): number | undefined {
    if (isAxiosError(error))
        return error.response?.status;
    if (error instanceof Error && 'status' in error && typeof error.status === 'number')
        return error.status;
    return undefined;
}
