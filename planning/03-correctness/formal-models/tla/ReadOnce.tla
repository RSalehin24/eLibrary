------------------------------- MODULE ReadOnce -------------------------------
(* Read-once access across devices.
   Covers INV-ACC-006 (at most one consumed opening; consume only on success;
   reconnect is not a new opening) and INV-LIB-008 (one live session per account).
   The race this models: two devices begin opening at the same time and both
   succeed. The Busy guard prevents it.
   STATUS: written, NOT YET MODEL-CHECKED. Must pass TLC at gate G2. *)
EXTENDS Naturals, FiniteSets

CONSTANTS Accounts, Devices

Phases == {"None", "Preparing", "Active", "Closed"}

VARIABLES phase,     \* (account, device) -> session phase
          openings   \* account -> number of consumed openings

vars == <<phase, openings>>

TypeOK ==
  /\ phase    \in [Accounts \X Devices -> Phases]
  /\ openings \in [Accounts -> Nat]

Busy(a) == \E d \in Devices : phase[<<a, d>>] \in {"Preparing", "Active"}

Init ==
  /\ phase    = [p \in Accounts \X Devices |-> "None"]
  /\ openings = [a \in Accounts |-> 0]

StartOpen(a, d) ==
  /\ phase[<<a, d>>] \in {"None", "Closed"}
  /\ openings[a] = 0
  /\ ~Busy(a)
  /\ phase' = [phase EXCEPT ![<<a, d>>] = "Preparing"]
  /\ UNCHANGED openings

\* The opening is consumed only when preparation succeeds.
PrepareOk(a, d) ==
  /\ phase[<<a, d>>] = "Preparing"
  /\ phase'    = [phase    EXCEPT ![<<a, d>>] = "Active"]
  /\ openings' = [openings EXCEPT ![a] = @ + 1]

PrepareFail(a, d) ==
  /\ phase[<<a, d>>] = "Preparing"
  /\ phase' = [phase EXCEPT ![<<a, d>>] = "None"]
  /\ UNCHANGED openings

\* Refresh or proxy retry within the active session: no new opening.
Reconnect(a, d) ==
  /\ phase[<<a, d>>] = "Active"
  /\ UNCHANGED vars

Close(a, d) ==
  /\ phase[<<a, d>>] = "Active"
  /\ phase' = [phase EXCEPT ![<<a, d>>] = "Closed"]
  /\ UNCHANGED openings

Next ==
  \E a \in Accounts, d \in Devices :
    StartOpen(a, d) \/ PrepareOk(a, d) \/ PrepareFail(a, d) \/ Reconnect(a, d) \/ Close(a, d)

Spec == Init /\ [][Next]_vars

AtMostOneOpening ==
  \A a \in Accounts : openings[a] <= 1

AtMostOneLiveSession ==
  \A a \in Accounts :
    Cardinality({d \in Devices : phase[<<a, d>>] \in {"Preparing", "Active"}}) <= 1

PreparingNeverConsumed ==
  \A a \in Accounts, d \in Devices : phase[<<a, d>>] = "Preparing" => openings[a] = 0

ActiveOrClosedMeansConsumed ==
  \A a \in Accounts, d \in Devices :
    phase[<<a, d>>] \in {"Active", "Closed"} => openings[a] = 1

Safety == TypeOK /\ AtMostOneOpening /\ AtMostOneLiveSession
          /\ PreparingNeverConsumed /\ ActiveOrClosedMeansConsumed
===============================================================================
