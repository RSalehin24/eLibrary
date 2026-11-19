------------------------------- MODULE ReadOnce -------------------------------
(* Read-once access with reading tickets (ADR-0023, ADR-0024).
   Covers INV-IDN-020 and INV-RDR-009: at most one consumed use per (user, book); the use is
   consumed when a ticket is successfully REDEEMED, not when it is issued
   (open), and never when the copy is missing/building.
   Several devices may each hold an issued ticket; the identity check
   (consume with PK insert on (user, book)) is atomic, so only one redeem wins.
   Reloading with an already redeemed ticket does not consume again.
   The v1 one-live-session invariant is RETIRED; the race it modeled is now this one.
   STATUS: edited for the ticket design, NOT MODEL-CHECKED. Must pass TLC at gate G2. *)
EXTENDS Naturals, FiniteSets

CONSTANTS Accounts, Devices

TicketStates == {"None", "Issued", "Redeemed", "Denied"}

VARIABLES ticket,    \* (account, device) -> ticket state
          copyReady, \* TRUE when the reading copy for the bound version is Ready
          uses       \* account -> number of consumed uses (identity read_once row)

vars == <<ticket, copyReady, uses>>

TypeOK ==
  /\ ticket    \in [Accounts \X Devices -> TicketStates]
  /\ copyReady \in BOOLEAN
  /\ uses      \in [Accounts -> Nat]

Init ==
  /\ ticket    = [p \in Accounts \X Devices |-> "None"]
  /\ copyReady \in BOOLEAN
  /\ uses      = [a \in Accounts |-> 0]

\* Open: the read scope is checked and a ticket issued; nothing is consumed.
Issue(a, d) ==
  /\ ticket[<<a, d>>] \in {"None", "Denied"}
  /\ ticket' = [ticket EXCEPT ![<<a, d>>] = "Issued"]
  /\ UNCHANGED <<copyReady, uses>>

\* Redeem succeeds: copy is Ready and the atomic consume wins (no use yet).
RedeemConsume(a, d) ==
  /\ ticket[<<a, d>>] = "Issued"
  /\ copyReady
  /\ uses[a] = 0
  /\ ticket' = [ticket EXCEPT ![<<a, d>>] = "Redeemed"]
  /\ uses'   = [uses EXCEPT ![a] = @ + 1]
  /\ UNCHANGED copyReady

\* Redeem loses the race or the use is already consumed by another ticket.
RedeemDenied(a, d) ==
  /\ ticket[<<a, d>>] = "Issued"
  /\ copyReady
  /\ uses[a] >= 1
  /\ ticket' = [ticket EXCEPT ![<<a, d>>] = "Denied"]
  /\ UNCHANGED <<copyReady, uses>>

\* Copy missing or building: typed error, nothing consumed, ticket stays Issued.
RedeemCopyUnavailable(a, d) ==
  /\ ticket[<<a, d>>] = "Issued"
  /\ ~copyReady
  /\ UNCHANGED vars

\* Reload with a redeemed ticket: allowed, no new use.
Reload(a, d) ==
  /\ ticket[<<a, d>>] = "Redeemed"
  /\ UNCHANGED vars

CopyChanges == copyReady' = ~copyReady /\ UNCHANGED <<ticket, uses>>

Next ==
  \/ CopyChanges
  \/ \E a \in Accounts, d \in Devices :
       Issue(a, d) \/ RedeemConsume(a, d) \/ RedeemDenied(a, d)
       \/ RedeemCopyUnavailable(a, d) \/ Reload(a, d)

Spec == Init /\ [][Next]_vars

AtMostOneUse ==
  \A a \in Accounts : uses[a] <= 1

\* A use exists iff exactly one device holds a Redeemed ticket.
UseIffOneRedeemed ==
  \A a \in Accounts :
    Cardinality({d \in Devices : ticket[<<a, d>>] = "Redeemed"}) = uses[a]

Safety == TypeOK /\ AtMostOneUse /\ UseIffOneRedeemed
===============================================================================
