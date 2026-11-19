--------------------------------- MODULE Outbox ---------------------------------
(* Transactional outbox with PULL consumption (ADR-0022).
   A producer commits the state change and an `events` row together (cursor =
   position in the log). A consumer pulls events after its stored cursor,
   applies each idempotently and advances its cursor in the SAME transaction as
   the effect. The consumer may crash after applying and before the cursor is
   persisted only if effect and cursor are not atomic; here they are, so a crash
   simply re-reads from the stored cursor, and a batch may be re-fetched
   (duplicate delivery is modeled by Pull not advancing anything).
   Covers INV-RDR-024 and INV-NTF-001 (consumer side: one effect per event,
   cursor advances with the effect); the producer side (INV-PLT-010, INV-IDN-023,
   INV-CAT-024, INV-ING-032) is a planned extension, see ../coverage.md.
   STATUS: checked with TLC 2.19 (2026-11-20): Safety holds in Spec and SpecWithReset (OutboxReset.cfg), NoLoss holds under SF(Apply). *)
EXTENDS Naturals, Sequences, FiniteSets

CONSTANT Events

VARIABLES log,       \* sequence of produced events (the producer's events table)
          cursor,    \* consumer's stored cursor: number of log entries consumed
          fetched,   \* batch currently held by the consumer (may be stale/duplicated)
          seen,      \* ids applied by the consumer (same transaction as cursor)
          applied    \* event -> number of effects applied

vars == <<log, cursor, fetched, seen, applied>>

TypeOK ==
  /\ log \in Seq(Events)
  /\ cursor \in Nat /\ cursor <= Len(log)
  /\ fetched \subseteq Events
  /\ seen \subseteq Events
  /\ applied \in [Events -> Nat]

Init ==
  /\ log = <<>> /\ cursor = 0 /\ fetched = {} /\ seen = {}
  /\ applied = [e \in Events |-> 0]

\* State change and events row commit together; an event id is produced once.
Produce(e) ==
  /\ \A i \in 1..Len(log) : log[i] # e
  /\ log' = Append(log, e)
  /\ UNCHANGED <<cursor, fetched, seen, applied>>

\* GET /internal/events?after=cursor: fetch everything after the stored cursor.
Pull ==
  /\ fetched' = {log[i] : i \in (cursor + 1)..Len(log)}
  /\ UNCHANGED <<log, cursor, seen, applied>>

\* Apply the next log entry idempotently; effect and cursor advance atomically.
Apply ==
  /\ cursor < Len(log)
  /\ log[cursor + 1] \in fetched
  /\ LET e == log[cursor + 1] IN
       /\ IF e \in seen
            THEN UNCHANGED <<seen, applied>>
            ELSE /\ seen'    = seen \cup {e}
                 /\ applied' = [applied EXCEPT ![e] = @ + 1]
       /\ cursor' = cursor + 1
  /\ UNCHANGED <<log, fetched>>

\* Consumer crash: in-memory batch lost; stored cursor and seen survive.
Crash ==
  /\ fetched' = {}
  /\ UNCHANGED <<log, cursor, seen, applied>>

\* Cursor lost (restore from backup): resynchronize by re-reading from 0;
\* effects are idempotent so nothing is applied twice.
ResetCursor ==
  /\ cursor' = 0 /\ fetched' = {}
  /\ UNCHANGED <<log, seen, applied>>

Next == \/ \E e \in Events : Produce(e)
        \/ Pull \/ Apply \/ Crash

\* Variant to check Safety only (NoLoss does not hold if the cursor is reset forever).
NextWithReset == Next \/ ResetCursor
SpecWithReset == Init /\ [][NextWithReset]_vars

\* Strong fairness for Apply: a consumer that crashes after every Pull would starve under weak
\* fairness (Apply is never continuously enabled). The assumption is that a consumer able to
\* make progress infinitely often does (it cannot crash forever); found by TLC at G2 prep.
Fairness == WF_vars(Pull) /\ SF_vars(Apply)

Spec == Init /\ [][Next]_vars /\ Fairness

AppliedAtMostOnce     == \A e \in Events : applied[e] <= 1
SeenIffApplied        == \A e \in Events : (e \in seen) <=> (applied[e] = 1)
NoEffectWithoutCommit == \A e \in seen : \E i \in 1..Len(log) : log[i] = e
Safety == TypeOK /\ AppliedAtMostOnce /\ SeenIffApplied /\ NoEffectWithoutCommit

\* No lost events (assumes ResetCursor is not taken forever): every committed
\* event is eventually applied exactly once.
NoLoss == \A e \in Events :
            (\E i \in 1..Len(log) : log[i] = e) ~> (applied[e] = 1)
===============================================================================
