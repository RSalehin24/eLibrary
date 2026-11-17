--------------------------------- MODULE Outbox ---------------------------------
(* Transactional outbox with an at-least-once relay and an idempotent consumer.
   Covers INV-PLT-009, INV-NTF-001 (one effective send per event) and
   INV-ING-016 (one effective publish per event).
   Duplicate delivery is modeled: Send can fire again while an event is still
   pending (relay crashed before Ack), and Deliver can see an event it already saw.
   STATUS: written, NOT YET MODEL-CHECKED. Must pass TLC at gate G2. *)
EXTENDS Naturals, FiniteSets

CONSTANT Events

VARIABLES produced,  \* events whose state change committed (with its outbox row)
          pending,   \* outbox rows not yet acknowledged
          inflight,  \* events handed to the consumer
          seen,      \* consumer dedupe table (committed atomically with the effect)
          applied    \* event -> number of effects applied

vars == <<produced, pending, inflight, seen, applied>>

TypeOK ==
  /\ produced \subseteq Events /\ pending \subseteq Events
  /\ inflight \subseteq Events /\ seen \subseteq Events
  /\ applied \in [Events -> Nat]

Init ==
  /\ produced = {} /\ pending = {} /\ inflight = {} /\ seen = {}
  /\ applied = [e \in Events |-> 0]

\* State change and outbox row commit together.
Produce(e) ==
  /\ e \notin produced
  /\ produced' = produced \cup {e}
  /\ pending'  = pending  \cup {e}
  /\ UNCHANGED <<inflight, seen, applied>>

Send(e) ==
  /\ e \in pending
  /\ inflight' = inflight \cup {e}
  /\ UNCHANGED <<produced, pending, seen, applied>>

Deliver(e) ==
  /\ e \in inflight
  /\ inflight' = inflight \ {e}
  /\ IF e \in seen
       THEN UNCHANGED <<seen, applied>>
       ELSE /\ seen'    = seen \cup {e}
            /\ applied' = [applied EXCEPT ![e] = @ + 1]
  /\ UNCHANGED <<produced, pending>>

Ack(e) ==
  /\ e \in pending /\ e \in seen
  /\ pending' = pending \ {e}
  /\ UNCHANGED <<produced, inflight, seen, applied>>

Next == \E e \in Events : Produce(e) \/ Send(e) \/ Deliver(e) \/ Ack(e)

Fairness == \A e \in Events : WF_vars(Send(e)) /\ WF_vars(Deliver(e)) /\ WF_vars(Ack(e))

Spec == Init /\ [][Next]_vars /\ Fairness

AppliedAtMostOnce  == \A e \in Events : applied[e] <= 1
SeenIffApplied     == \A e \in Events : (e \in seen) <=> (applied[e] = 1)
NoEffectWithoutCommit == seen \subseteq produced
Safety == TypeOK /\ AppliedAtMostOnce /\ SeenIffApplied /\ NoEffectWithoutCommit

\* No lost events: everything committed is eventually applied exactly once.
NoLoss == \A e \in Events : (e \in produced) ~> (applied[e] = 1)
===============================================================================
