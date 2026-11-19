import { ErrorEnvelope } from './generated/common';

function isErrorBody(value: unknown): value is ErrorEnvelope['error'] {
  return (
    typeof value === 'object' &&
    value !== null &&
    'code' in value &&
    typeof value.code === 'string' &&
    'message' in value &&
    typeof value.message === 'string' &&
    'request_id' in value &&
    typeof value.request_id === 'string'
  );
}

/** Reads the one error shape every route returns; `undefined` when the body is something else. */
export function parseErrorEnvelope(body: unknown): ErrorEnvelope | undefined {
  if (typeof body !== 'object' || body === null || !('error' in body)) {
    return undefined;
  }
  return isErrorBody(body.error) ? { error: body.error } : undefined;
}
