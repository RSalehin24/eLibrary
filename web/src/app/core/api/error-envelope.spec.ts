import { describe, expect, it } from 'vitest';

import { parseErrorEnvelope } from './error-envelope';
import { Scope } from './generated/common';

describe('parseErrorEnvelope', () => {
  it('reads the documented error shape', () => {
    const body = { error: { code: 'not_found', message: 'No such book', request_id: 'req-1' } };
    expect(parseErrorEnvelope(body)?.error.code).toBe('not_found');
  });

  it('rejects anything else', () => {
    for (const body of [
      null,
      'oops',
      {},
      { error: {} },
      { error: { code: 1, message: 'm', request_id: 'r' } },
    ]) {
      expect(parseErrorEnvelope(body)).toBeUndefined();
    }
  });

  it('uses the generated scope type', () => {
    const scope: Scope = 'read_once';
    expect(scope).toBe('read_once');
  });
});
