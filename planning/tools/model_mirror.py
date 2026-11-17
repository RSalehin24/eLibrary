"""Independent Python mirrors of the planning models (NOT TLC/Alloy).

Explicit-state BFS for the TLA+ models and randomized small-scope checks for the Alloy policy.
Purpose: validate the *logic* of the specs while Java/TLC is unavailable. It does NOT check the
TLA+/Alloy syntax and is not a substitute for gate G2.

Safety: a state-count guard (STATE_LIMIT) stops explosions; run heavy checks under a memory cap, e.g.
    (ulimit -v 15000000; timeout 300 python3 -I -u planning/tools/model_mirror.py jobs)
Usage: python3 -I planning/tools/model_mirror.py [jobs|readonce|outbox|access|all]
Bounds (env): MIRROR_JOBS (default 3), MIRROR_ATTEMPTS (default 2), MIRROR_STATE_LIMIT (default 400000)
"""
import itertools
import os
import random
import sys
from collections import deque

# ---------------------------------------------------------------- generic helpers
STATE_LIMIT = int(os.environ.get('MIRROR_STATE_LIMIT', '400000'))


def bfs(init, successors):
    """successors(state) -> iterable of (action_label, next_state). Returns states, edges."""
    seen = {init}
    edges = {}
    queue = deque([init])
    while queue:
        if len(seen) > STATE_LIMIT:
            raise RuntimeError(f"state limit {STATE_LIMIT} exceeded (explosion guard)")
        s = queue.popleft()
        out = list(successors(s))
        edges[s] = out
        for _, t in out:
            if t not in seen:
                seen.add(t)
                queue.append(t)
    return seen, edges


def tarjan(nodes, adj):
    index, low, onstack, stack, sccs = {}, {}, set(), [], []
    counter = [0]
    sys.setrecursionlimit(1_000_000)

    def strong(v):
        index[v] = low[v] = counter[0]; counter[0] += 1
        stack.append(v); onstack.add(v)
        for w in adj.get(v, ()):
            if w not in index:
                strong(w); low[v] = min(low[v], low[w])
            elif w in onstack:
                low[v] = min(low[v], index[w])
        if low[v] == index[v]:
            comp = []
            while True:
                w = stack.pop(); onstack.discard(w); comp.append(w)
                if w == v:
                    break
            sccs.append(comp)

    for v in nodes:
        if v not in index:
            strong(v)
    return sccs


def fair_counterexample(states, edges, region, fair_actions, enabled_in):
    """Look for a weakly-fair infinite path staying in `region` (set of states).
    Returns a witness SCC or None. A fair SCC: for each fair action A, A is disabled in
    some state of the SCC, or A has a transition inside the SCC."""
    adj = {s: [t for _, t in edges[s] if t in region] for s in region}
    for comp in tarjan(region, adj):
        cset = set(comp)
        nontrivial = len(comp) > 1 or any(t in cset for t in adj[comp[0]])
        if not nontrivial:
            continue
        taken = {a for s in comp for a, t in edges[s] if t in cset}
        ok = True
        for a in fair_actions:
            disabled_somewhere = any(not enabled_in(s, a) for s in comp)
            if not disabled_somewhere and a not in taken:
                ok = False
                break
        if ok:
            return comp
    return None

# ---------------------------------------------------------------- JobLifecycle
def job_model(mutation=None):
    count = int(os.environ.get('MIRROR_JOBS', '3'))
    jobs = tuple(range(count))
    url_of = {j: ('u1' if j < (count + 1) // 2 else 'u2') for j in jobs}  # first half share one URL
    max_attempts = int(os.environ.get('MIRROR_ATTEMPTS', '2'))
    active = {'Queued', 'Running', 'Review'}
    terminal = {'Published', 'Failed', 'Cancelled'}
    # per job: (state, epoch, attempts, fetched, publishes, outcomes)
    # outcomes[e-1] = ghost: the TRUE result of the run that held epoch e (chosen at claim).
    init = tuple(('New', 0, 0, False, 0, ()) for _ in jobs)

    def put(s, j, v):
        return s[:j] + (v,) + s[j + 1:]

    def succ(s):
        for j in jobs:
            st, ep, at, fe, pu, outs = s[j]
            if st == 'New':
                others_active = any(k != j and url_of[k] == url_of[j] and s[k][0] in active for k in jobs)
                if mutation == 'no_url_exclusion' or not others_active:
                    yield (('Enqueue', j), put(s, j, ('Queued', ep, at, fe, pu, outs)))
            if st == 'Queued':
                for truth in (False, True):
                    yield (('Claim', j), put(s, j, ('Running', ep + 1, at + 1, False, pu, outs + (truth,))))
            if st == 'Running':
                nxt = 'Queued' if at < max_attempts else 'Failed'
                yield (('LeaseExpire', j), put(s, j, (nxt, ep, at, fe, pu, outs)))
                for e in range(1, ep + 1):          # workers of runs 1..ep may still be alive (zombies)
                    if e == ep or mutation == 'no_fencing':
                        # a worker of run e reports ITS run's real outcome
                        yield (('Fetch', j, e), put(s, j, (st, ep, at, outs[e - 1], pu, outs)))
                if fe or mutation == 'publish_without_complete':
                    yield (('Complete', j, ep), put(s, j, ('Published', ep, at, fe, pu + 1, outs)))
                if not fe:
                    yield (('NeedReview', j, ep), put(s, j, ('Review', ep, at, fe, pu, outs)))
            if st == 'Review' and at < max_attempts:
                yield (('ResolveRetry', j), put(s, j, ('Queued', ep, at, fe, pu, outs)))
            if st in ('New', 'Queued', 'Review'):
                yield (('Cancel', j), put(s, j, ('Cancelled', ep, at, fe, pu, outs)))

    def safety(s):
        errs = []
        for j in jobs:
            st, ep, at, fe, pu, outs = s[j]
            if st == 'Published' and not fe: errs.append('PublishedImpliesComplete')
            if st == 'Published' and not outs[ep - 1]: errs.append('PublishedImpliesCurrentRunComplete')
            if pu > 1: errs.append('PublishAtMostOnce')
            if (st == 'Published') != (pu == 1): errs.append('PublishedIffCounted')
            if at > max_attempts: errs.append('AttemptsBounded')
            if ep != at: errs.append('EpochMatchesAttempts')
        for a, b in itertools.combinations(jobs, 2):
            if url_of[a] == url_of[b] and s[a][0] in active and s[b][0] in active:
                errs.append('AtMostOneActivePerUrl')
        return errs

    fair = ([('Claim', j) for j in jobs] + [('LeaseExpire', j) for j in jobs] + [('Enqueue', j) for j in jobs]
            + [('Complete', j, e) for j in jobs for e in range(1, max_attempts + 1)]
            + [('NeedReview', j, e) for j in jobs for e in range(1, max_attempts + 1)])
    return init, succ, safety, fair, jobs, terminal


def check_jobs(mutation=None):
    init, succ, safety, fair, jobs, terminal = job_model(mutation)
    states, edges = bfs(init, succ)
    violations = {}
    for s in states:
        for e in safety(s):
            violations.setdefault(e, s)

    def enabled(s, a):
        return any(x == a for x, _ in edges[s])

    live_bad = None
    for j in jobs:
        # (Queued_j) ~> (settled_j): find fair cycle inside "not settled" region reachable from a Queued state
        region_all = {s for s in states if s[j][0] not in terminal and s[j][0] != 'Review'}
        queued = [s for s in states if s[j][0] == 'Queued']
        reach, dq = set(queued), deque(queued)
        while dq:
            s = dq.popleft()
            for _, t in edges[s]:
                if t in region_all and t not in reach:
                    reach.add(t); dq.append(t)
        # also a state with no successors inside region (deadlock before settling)
        for s in reach:
            if not any(t in region_all for _, t in edges[s]) and not edges[s]:
                live_bad = ('deadlock', j, s)
        cyc = fair_counterexample(states, edges, reach, fair, enabled)
        if cyc:
            live_bad = ('fair-cycle', j, cyc[0])
    return len(states), violations, live_bad

# ---------------------------------------------------------------- ReadOnce
def check_readonce(mutation=None):
    accounts, devices = (0, 1), (0, 1, 2)
    keys = [(a, d) for a in accounts for d in devices]
    init = (tuple('None' for _ in keys), tuple(0 for _ in accounts))

    def busy(phase, a):
        return any(phase[keys.index((a, d))] in ('Preparing', 'Active') for d in devices)

    def succ(s):
        phase, op = s
        for (a, d) in keys:
            i = keys.index((a, d))
            ph = phase[i]
            def setp(v):
                return phase[:i] + (v,) + phase[i + 1:]
            if ph in ('None', 'Closed') and op[a] == 0 and (mutation == 'no_busy_guard' or not busy(phase, a)):
                yield (('Start', a, d), (setp('Preparing'), op))
            if ph == 'Preparing':
                nop = op[:a] + (op[a] + 1,) + op[a + 1:]
                yield (('PrepOk', a, d), (setp('Active'), nop))
                yield (('PrepFail', a, d), (setp('None'), op))
            if ph == 'Active':
                yield (('Reconnect', a, d), s)
                yield (('Close', a, d), (setp('Closed'), op))

    states, edges = bfs(init, succ)
    bad = {}
    for phase, op in states:
        for a in accounts:
            if op[a] > 1: bad.setdefault('AtMostOneOpening', (phase, op))
            live = [d for d in devices if phase[keys.index((a, d))] in ('Preparing', 'Active')]
            if len(live) > 1: bad.setdefault('AtMostOneLiveSession', (phase, op))
            for d in devices:
                ph = phase[keys.index((a, d))]
                if ph == 'Preparing' and op[a] != 0: bad.setdefault('PreparingNeverConsumed', (phase, op))
                if ph in ('Active', 'Closed') and op[a] != 1: bad.setdefault('ActiveOrClosedMeansConsumed', (phase, op))
    return len(states), bad

# ---------------------------------------------------------------- Outbox
def check_outbox(mutation=None):
    events = (0, 1, 2)
    # state: produced, pending, inflight, seen (frozensets) ; applied tuple
    init = (frozenset(), frozenset(), frozenset(), frozenset(), (0, 0, 0))

    def succ(s):
        produced, pending, inflight, seen, applied = s
        for e in events:
            if e not in produced:
                yield (('Produce', e), (produced | {e}, pending | {e}, inflight, seen, applied))
            if e in pending:
                yield (('Send', e), (produced, pending, inflight | {e}, seen, applied))
            if e in inflight:
                if e in seen and mutation != 'no_dedupe':
                    yield (('Deliver', e), (produced, pending, inflight - {e}, seen, applied))
                else:
                    ap = applied[:e] + (min(applied[e] + 1, 2),) + applied[e + 1:]  # cap keeps the broken variant finite
                    yield (('Deliver', e), (produced, pending, inflight - {e}, seen | {e}, ap))
            if e in pending and e in seen:
                yield (('Ack', e), (produced, pending - {e}, inflight, seen, applied))

    states, edges = bfs(init, succ)
    bad = {}
    for produced, pending, inflight, seen, applied in states:
        for e in events:
            if applied[e] > 1: bad.setdefault('AppliedAtMostOnce', e)
            if (e in seen) != (applied[e] == 1): bad.setdefault('SeenIffApplied', e)
        if not seen <= produced: bad.setdefault('NoEffectWithoutCommit', seen)

    fair = [(a, e) for e in events for a in ('Send', 'Deliver', 'Ack')]

    def enabled(s, a):
        return any(x == a for x, _ in edges[s])

    live_bad = None
    for e in events:
        region_all = {s for s in states if e in s[0] and s[4][e] != 1}
        cyc = fair_counterexample(states, edges, region_all, fair, enabled)
        if cyc:
            live_bad = ('fair-cycle', e, cyc[0])
    return len(states), bad, live_bad

# ---------------------------------------------------------------- Access (Alloy mirror)
ACTIONS = ['Search', 'ViewMetadata', 'ViewPreview', 'Read', 'Download', 'SendToKindle', 'EditMetadata', 'ManageAccess']
PUBLIC = {'Search', 'ViewMetadata', 'ViewPreview'}


def allow(subj, act, book, G, facts, mutation=None):
    """subj: 'anon' or account id. facts: dict(active, mfa, admin sets; published set).
    G: iterable of (holder, act, frozenset(on), live)."""
    published = facts['published']
    live_grants = [g for g in G if g[3]]
    pub_rule = (act in PUBLIC and (book in published or mutation == 'public_unpublished'))
    active = subj != 'anon' and subj in facts['active']
    grant_rule = active and any(
        g[0] == subj and g[1] == act and book in g[2] and (book in published or act in ('EditMetadata', 'ManageAccess'))
        for g in live_grants)
    meta_rule = active and act in ('ViewMetadata', 'ViewPreview') and any(
        g[0] == subj and g[1] == 'EditMetadata' and book in g[2] for g in live_grants)
    priv = subj != 'anon' and subj in facts['active'] and subj in facts['admin'] and subj in facts['mfa']
    return pub_rule or grant_rule or meta_rule or priv


def check_access(mutation=None, samples=60000, seed=7):
    rnd = random.Random(seed)
    accounts, books = ('a1', 'a2'), ('b1', 'b2')
    subsets = lambda xs: [frozenset(c) for r in range(len(xs) + 1) for c in itertools.combinations(xs, r)]
    bad = {}
    grant_universe = [(h, act, on) for h in accounts for act in ACTIONS for on in subsets(books)]
    for _ in range(samples):
        facts = dict(published=set(rnd.sample(books, rnd.randint(0, 2))),
                     active=set(rnd.sample(accounts, rnd.randint(0, 2))),
                     mfa=set(rnd.sample(accounts, rnd.randint(0, 2))),
                     admin=set(rnd.sample(accounts, rnd.randint(0, 2))))
        n = rnd.randint(0, 4)
        G = [(*rnd.choice(grant_universe), rnd.random() < 0.7) for _ in range(n)]
        G2 = G + [(*rnd.choice(grant_universe), rnd.random() < 0.7) for _ in range(rnd.randint(0, 3))]
        for act in ACTIONS:
            for b in books:
                if allow('anon', act, b, G, facts, mutation):
                    if not (act in PUBLIC and b in facts['published']): bad.setdefault('AnonymousLimited', (act, b))
                if act == 'Read' and allow('anon', act, b, G, facts, mutation): bad.setdefault('ReadNeedsAccount', b)
                for s in ('anon',) + accounts:
                    if allow(s, act, b, G, facts, mutation) != allow(s, act, b, [g for g in G if g[3]], facts, mutation):
                        bad.setdefault('DeadGrantsIgnored', (s, act, b))
                    if allow(s, act, b, G, facts, mutation) and not allow(s, act, b, G2, facts, mutation):
                        bad.setdefault('Monotonic', (s, act, b))
                    if s != 'anon' and act == 'ManageAccess' and allow(s, act, b, G, facts, mutation):
                        priv = s in facts['active'] and s in facts['admin'] and s in facts['mfa']
                        has = s in facts['active'] and any(g[3] and g[0] == s and g[1] == act and b in g[2] for g in G)
                        if not (priv or has): bad.setdefault('ManagementNeedsAuthority', (s, b))
                    if b not in facts['published'] and act in ('ViewMetadata', 'ViewPreview', 'Read') and allow(s, act, b, G, facts, mutation):
                        priv = s != 'anon' and s in facts['active'] and s in facts['admin'] and s in facts['mfa']
                        has = s != 'anon' and s in facts['active'] and any(
                            g[3] and g[0] == s and b in g[2] and g[1] in ('EditMetadata', act) for g in G)
                        if not (priv or has): bad.setdefault('UnpublishedHidden', (s, act, b))
    return bad


def run_jobs():
    print('== JobLifecycle (jobs=%s attempts=%s)' % (os.environ.get('MIRROR_JOBS', '3'), os.environ.get('MIRROR_ATTEMPTS', '2')), flush=True)
    n, v, l = check_jobs()
    print(f'  states={n} safety_violations={v or "none"} liveness_counterexample={l or "none"}', flush=True)
    for m in ('no_url_exclusion', 'publish_without_complete', 'no_fencing'):
        n, v, l = check_jobs(m)
        print(f'  MUTATION {m}: states={n} violations={sorted(v) or "none"} live={l and l[0]}', flush=True)


def run_readonce():
    print('== ReadOnce (2 accounts, 3 devices)', flush=True)
    n, v = check_readonce()
    print(f'  states={n} violations={v or "none"}', flush=True)
    n, v = check_readonce('no_busy_guard')
    print(f'  MUTATION no_busy_guard: states={n} violations={sorted(v) or "none"}', flush=True)


def run_outbox():
    print('== Outbox (3 events)', flush=True)
    n, v, l = check_outbox()
    print(f'  states={n} violations={v or "none"} liveness={l or "none"}', flush=True)
    n, v, l = check_outbox('no_dedupe')
    print(f'  MUTATION no_dedupe: violations={sorted(v) or "none"}', flush=True)


def run_access():
    print('== Access policy (randomized small scope, mirrors Alloy asserts)', flush=True)
    print('  violations =', check_access(samples=8000) or 'none', flush=True)
    print('  MUTATION public_unpublished:', sorted(check_access('public_unpublished', samples=2000)) or 'none', flush=True)


if __name__ == '__main__':
    which = sys.argv[1] if len(sys.argv) > 1 else 'all'
    runners = {'jobs': run_jobs, 'readonce': run_readonce, 'outbox': run_outbox, 'access': run_access}
    for name, fn in runners.items():
        if which in ('all', name):
            fn()
