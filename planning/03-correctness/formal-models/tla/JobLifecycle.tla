------------------------------ MODULE JobLifecycle ------------------------------
(* Ingestion job lifecycle with leases and fencing epochs.
   Covers INV-ING-006 (publish only when all leaves fetched),
   INV-ING-010 (state machine, <=1 active job per URL, lease expiry),
   INV-ING-016 (a job publishes at most once).
   STATUS: written, NOT YET MODEL-CHECKED (no Java/TLC on the authoring machine).
   Must pass TLC with JobLifecycle.cfg at gate G2. *)
EXTENDS Naturals, FiniteSets

CONSTANTS Jobs, Urls, UrlOf, MaxAttempts
ASSUME UrlOf \in [Jobs -> Urls]
ASSUME MaxAttempts \in Nat \ {0}

States   == {"New", "Queued", "Running", "Review", "Published", "Failed", "Cancelled"}
Active   == {"Queued", "Running", "Review"}
Terminal == {"Published", "Failed", "Cancelled"}

VARIABLES state,       \* job -> lifecycle state
          epoch,       \* job -> fencing token, incremented on every claim
          attempts,    \* job -> number of claims so far
          fetchedAll,  \* job -> TRUE iff every TOC leaf was fetched or recorded empty
          publishes    \* job -> number of BookPublished effects

vars == <<state, epoch, attempts, fetchedAll, publishes>>

TypeOK ==
  /\ state      \in [Jobs -> States]
  /\ epoch      \in [Jobs -> Nat]
  /\ attempts   \in [Jobs -> Nat]
  /\ fetchedAll \in [Jobs -> BOOLEAN]
  /\ publishes  \in [Jobs -> Nat]

Init ==
  /\ state      = [j \in Jobs |-> "New"]
  /\ epoch      = [j \in Jobs |-> 0]
  /\ attempts   = [j \in Jobs |-> 0]
  /\ fetchedAll = [j \in Jobs |-> FALSE]
  /\ publishes  = [j \in Jobs |-> 0]

\* A job may be queued only if no other job for the same URL is active.
Enqueue(j) ==
  /\ state[j] = "New"
  /\ \A k \in Jobs : (k # j /\ UrlOf[k] = UrlOf[j]) => state[k] \notin Active
  /\ state' = [state EXCEPT ![j] = "Queued"]
  /\ UNCHANGED <<epoch, attempts, fetchedAll, publishes>>

\* A worker claims a queued job; the epoch fences out any previous holder.
Claim(j) ==
  /\ state[j] = "Queued"
  /\ state'      = [state      EXCEPT ![j] = "Running"]
  /\ epoch'      = [epoch      EXCEPT ![j] = @ + 1]
  /\ attempts'   = [attempts   EXCEPT ![j] = @ + 1]
  /\ fetchedAll' = [fetchedAll EXCEPT ![j] = FALSE]
  /\ UNCHANGED publishes

\* The holder of epoch e records the outcome of acquisition. A holder with a
\* stale epoch (a zombie after lease expiry) cannot match, so the action is disabled.
Fetch(j, e, ok) ==
  /\ state[j] = "Running" /\ e = epoch[j]
  /\ fetchedAll' = [fetchedAll EXCEPT ![j] = ok]
  /\ UNCHANGED <<state, epoch, attempts, publishes>>

Complete(j, e) ==
  /\ state[j] = "Running" /\ e = epoch[j] /\ fetchedAll[j]
  /\ state'     = [state     EXCEPT ![j] = "Published"]
  /\ publishes' = [publishes EXCEPT ![j] = @ + 1]
  /\ UNCHANGED <<epoch, attempts, fetchedAll>>

NeedReview(j, e) ==
  /\ state[j] = "Running" /\ e = epoch[j] /\ ~fetchedAll[j]
  /\ state' = [state EXCEPT ![j] = "Review"]
  /\ UNCHANGED <<epoch, attempts, fetchedAll, publishes>>

\* Lease timeout / worker crash.
LeaseExpire(j) ==
  /\ state[j] = "Running"
  /\ state' = [state EXCEPT ![j] = IF attempts[j] < MaxAttempts THEN "Queued" ELSE "Failed"]
  /\ UNCHANGED <<epoch, attempts, fetchedAll, publishes>>

\* A curator resolves a review item: retry (if attempts remain) or cancel.
ResolveRetry(j) ==
  /\ state[j] = "Review" /\ attempts[j] < MaxAttempts
  /\ state' = [state EXCEPT ![j] = "Queued"]
  /\ UNCHANGED <<epoch, attempts, fetchedAll, publishes>>

Cancel(j) ==
  /\ state[j] \in {"New", "Queued", "Review"}
  /\ state' = [state EXCEPT ![j] = "Cancelled"]
  /\ UNCHANGED <<epoch, attempts, fetchedAll, publishes>>

Next ==
  \E j \in Jobs :
       Enqueue(j) \/ Claim(j) \/ LeaseExpire(j) \/ ResolveRetry(j) \/ Cancel(j)
    \/ \E e \in 0..MaxAttempts :
         (\E ok \in BOOLEAN : Fetch(j, e, ok)) \/ Complete(j, e) \/ NeedReview(j, e)

Fairness ==
  \A j \in Jobs :
       WF_vars(Claim(j)) /\ WF_vars(LeaseExpire(j)) /\ WF_vars(Enqueue(j))
    /\ \A e \in 0..MaxAttempts : WF_vars(Complete(j, e)) /\ WF_vars(NeedReview(j, e))

Spec == Init /\ [][Next]_vars /\ Fairness

(* ------------------------------ Safety ----------------------------------- *)
AtMostOneActivePerUrl ==
  \A j, k \in Jobs : (j # k /\ UrlOf[j] = UrlOf[k]) => ~(state[j] \in Active /\ state[k] \in Active)

PublishedImpliesComplete == \A j \in Jobs : state[j] = "Published" => fetchedAll[j]
PublishAtMostOnce        == \A j \in Jobs : publishes[j] <= 1
PublishedIffCounted      == \A j \in Jobs : (state[j] = "Published") <=> (publishes[j] = 1)
AttemptsBounded          == \A j \in Jobs : attempts[j] <= MaxAttempts
EpochMatchesAttempts     == \A j \in Jobs : epoch[j] = attempts[j]

Safety ==
  /\ TypeOK /\ AtMostOneActivePerUrl /\ PublishedImpliesComplete /\ PublishAtMostOnce
  /\ PublishedIffCounted /\ AttemptsBounded /\ EpochMatchesAttempts

(* ------------------------------ Liveness --------------------------------- *)
EventuallySettled ==
  \A j \in Jobs : (state[j] = "Queued") ~> (state[j] \in Terminal \cup {"Review"})
===============================================================================
