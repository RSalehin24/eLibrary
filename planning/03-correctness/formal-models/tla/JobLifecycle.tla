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
          fetchedAll,  \* job -> TRUE iff the run that reported last saw every TOC leaf fetched or recorded empty
          publishes,   \* job -> number of BookPublished effects
          outcome      \* GHOST: job -> epoch -> the TRUE result of the run that held that epoch (chosen at claim)

vars == <<state, epoch, attempts, fetchedAll, publishes, outcome>>

TypeOK ==
  /\ state      \in [Jobs -> States]
  /\ epoch      \in [Jobs -> Nat]
  /\ attempts   \in [Jobs -> Nat]
  /\ fetchedAll \in [Jobs -> BOOLEAN]
  /\ publishes  \in [Jobs -> Nat]
  /\ outcome    \in [Jobs -> [1..MaxAttempts -> BOOLEAN]]

Init ==
  /\ state      = [j \in Jobs |-> "New"]
  /\ epoch      = [j \in Jobs |-> 0]
  /\ attempts   = [j \in Jobs |-> 0]
  /\ fetchedAll = [j \in Jobs |-> FALSE]
  /\ publishes  = [j \in Jobs |-> 0]
  /\ outcome    = [j \in Jobs |-> [e \in 1..MaxAttempts |-> FALSE]]

\* A job may be queued only if no other job for the same URL is active.
Enqueue(j) ==
  /\ state[j] = "New"
  /\ \A k \in Jobs : (k # j /\ UrlOf[k] = UrlOf[j]) => state[k] \notin Active
  /\ state' = [state EXCEPT ![j] = "Queued"]
  /\ UNCHANGED <<epoch, attempts, fetchedAll, publishes, outcome>>

\* A worker claims a queued job; the epoch fences out any previous holder.
Claim(j) ==
  /\ state[j] = "Queued"
  /\ state'      = [state      EXCEPT ![j] = "Running"]
  /\ epoch'      = [epoch      EXCEPT ![j] = @ + 1]
  /\ attempts'   = [attempts   EXCEPT ![j] = @ + 1]
  /\ fetchedAll' = [fetchedAll EXCEPT ![j] = FALSE]
  /\ \E t \in BOOLEAN : outcome' = [outcome EXCEPT ![j][epoch[j] + 1] = t]   \* ghost: truth of the new run
  /\ UNCHANGED publishes

\* A worker of run e reports ITS run's real outcome. Workers of earlier runs (zombies after a
\* lease expiry) still exist (e < epoch[j]); the fencing conjunct below rejects them.
\* Sensitivity check: delete the fencing line and TLC must report PublishedImpliesCurrentRunComplete.
Fetch(j, e) ==
  /\ state[j] = "Running" /\ e \in 1..epoch[j]
  /\ e = epoch[j]                                   \* fencing
  /\ fetchedAll' = [fetchedAll EXCEPT ![j] = outcome[j][e]]
  /\ UNCHANGED <<state, epoch, attempts, publishes, outcome>>

Complete(j, e) ==
  /\ state[j] = "Running" /\ e = epoch[j] /\ fetchedAll[j]
  /\ state'     = [state     EXCEPT ![j] = "Published"]
  /\ publishes' = [publishes EXCEPT ![j] = @ + 1]
  /\ UNCHANGED <<epoch, attempts, fetchedAll, outcome>>

NeedReview(j, e) ==
  /\ state[j] = "Running" /\ e = epoch[j] /\ ~fetchedAll[j]
  /\ state' = [state EXCEPT ![j] = "Review"]
  /\ UNCHANGED <<epoch, attempts, fetchedAll, publishes, outcome>>

\* Lease timeout / worker crash.
LeaseExpire(j) ==
  /\ state[j] = "Running"
  /\ state' = [state EXCEPT ![j] = IF attempts[j] < MaxAttempts THEN "Queued" ELSE "Failed"]
  /\ UNCHANGED <<epoch, attempts, fetchedAll, publishes, outcome>>

\* A curator resolves a review item: retry (if attempts remain) or cancel.
ResolveRetry(j) ==
  /\ state[j] = "Review" /\ attempts[j] < MaxAttempts
  /\ state' = [state EXCEPT ![j] = "Queued"]
  /\ UNCHANGED <<epoch, attempts, fetchedAll, publishes, outcome>>

Cancel(j) ==
  /\ state[j] \in {"New", "Queued", "Review"}
  /\ state' = [state EXCEPT ![j] = "Cancelled"]
  /\ UNCHANGED <<epoch, attempts, fetchedAll, publishes, outcome>>

Next ==
  \E j \in Jobs :
       Enqueue(j) \/ Claim(j) \/ LeaseExpire(j) \/ ResolveRetry(j) \/ Cancel(j)
    \/ \E e \in 1..MaxAttempts :
         Fetch(j, e) \/ Complete(j, e) \/ NeedReview(j, e)

Fairness ==
  \A j \in Jobs :
       WF_vars(Claim(j)) /\ WF_vars(LeaseExpire(j)) /\ WF_vars(Enqueue(j))
    /\ \A e \in 1..MaxAttempts : WF_vars(Complete(j, e)) /\ WF_vars(NeedReview(j, e))

Spec == Init /\ [][Next]_vars /\ Fairness

(* ------------------------------ Safety ----------------------------------- *)
AtMostOneActivePerUrl ==
  \A j, k \in Jobs : (j # k /\ UrlOf[j] = UrlOf[k]) => ~(state[j] \in Active /\ state[k] \in Active)

PublishedImpliesComplete == \A j \in Jobs : state[j] = "Published" => fetchedAll[j]
\* The ghost-based property that makes fencing observable (finding F-1):
PublishedImpliesCurrentRunComplete ==
  \A j \in Jobs : state[j] = "Published" => outcome[j][epoch[j]]
PublishAtMostOnce        == \A j \in Jobs : publishes[j] <= 1
PublishedIffCounted      == \A j \in Jobs : (state[j] = "Published") <=> (publishes[j] = 1)
AttemptsBounded          == \A j \in Jobs : attempts[j] <= MaxAttempts
EpochMatchesAttempts     == \A j \in Jobs : epoch[j] = attempts[j]

Safety ==
  /\ TypeOK /\ AtMostOneActivePerUrl /\ PublishedImpliesComplete /\ PublishedImpliesCurrentRunComplete
  /\ PublishAtMostOnce
  /\ PublishedIffCounted /\ AttemptsBounded /\ EpochMatchesAttempts

(* ------------------------------ Liveness --------------------------------- *)
EventuallySettled ==
  \A j \in Jobs : (state[j] = "Queued") ~> (state[j] \in Terminal \cup {"Review"})
===============================================================================
