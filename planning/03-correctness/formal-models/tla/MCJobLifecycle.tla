---------------------------- MODULE MCJobLifecycle ----------------------------
(* Model instance of JobLifecycle: TLC configuration files cannot hold function values, so
   UrlOf is defined here and attached with `CONSTANT UrlOf <- ModelUrlOf`. *)
EXTENDS JobLifecycle, TLC

CONSTANTS j1, j2, j3, u1, u2

ModelUrlOf == (j1 :> u1) @@ (j2 :> u1) @@ (j3 :> u2)
===============================================================================
