---------------------- MODULE SpecPackEvalLifecycle ----------------------

VARIABLE s

BatchSpec == {"1.1", "1.2"}
LocalSpec == {"1.2", "1.3"}

Evidence(kind, localSpec, reported, passed, flags, claimsPass) ==
    [kind |-> kind, localSpec |-> localSpec, reported |-> reported,
     passed |-> passed, flags |-> flags, claimsPass |-> claimsPass]

NoEvidence == Evidence("NoEvidence", {}, {}, {}, {}, FALSE)
InvalidKinds == {"BadJSON", "BadJUnit", "BadSpec"}
ValidKinds == {"JSON", "JUnit"}

\* JSON claims can disagree with the map. A null flag list is decoded as {}.
JsonInputs == {
    Evidence("JSON", BatchSpec, BatchSpec, BatchSpec, {}, TRUE),
    Evidence("JSON", BatchSpec, BatchSpec, {"1.1"}, {}, FALSE),
    Evidence("JSON", BatchSpec, {"1.1", "9.1"}, {"1.1", "9.1"}, {}, TRUE),
    Evidence("JSON", BatchSpec, BatchSpec, BatchSpec, {"1.2"}, TRUE)
}

\* JUnit flags map criteria with no matching testcase, such as when a
\* protocol version is the only apparent match. An empty local spec here
\* denotes the absence of a local file, so the batch fallback applies.
JUnitInputs == {
    Evidence("JUnit", LocalSpec, LocalSpec, LocalSpec, {}, FALSE),
    Evidence("JUnit", LocalSpec, LocalSpec, {"1.2"}, {"1.3"}, FALSE),
    Evidence("JUnit", {}, BatchSpec, BatchSpec, {}, FALSE)
}

InvalidInputs == {Evidence(kind, {}, {}, {}, {}, FALSE) : kind \in InvalidKinds}

Required(input) == IF input.localSpec = {} THEN BatchSpec ELSE input.localSpec

Init ==
    s = [phase |-> "New", complete |-> FALSE, visible |-> FALSE,
         input |-> NoEvidence, resultIds |-> {}, resultPassed |-> {},
         resultUnverified |-> {}, verdict |-> "None"]

RejectInputs ==
    /\ s.phase = "New"
    /\ s' = [s EXCEPT !.phase = "Rejected"]

StartStaging ==
    /\ s.phase = "New"
    /\ s' = [s EXCEPT !.phase = "Staging"]

FailStaging ==
    /\ s.phase = "Staging"
    /\ s' = [s EXCEPT !.phase = "Rejected"]

FinishScaffold ==
    /\ s.phase = "Staging"
    /\ s' = [s EXCEPT !.phase = "ScaffoldReady", !.complete = TRUE]

FailBundleWrite ==
    /\ s.phase = "ScaffoldReady"
    /\ s' = [s EXCEPT !.phase = "Rejected", !.complete = FALSE]

StageBundle ==
    /\ s.phase = "ScaffoldReady"
    /\ s' = [s EXCEPT !.phase = "BundleStaged"]

FailRunPublish ==
    /\ s.phase \in {"ScaffoldReady", "BundleStaged"}
    /\ s' = [s EXCEPT !.phase = "Rejected", !.complete = FALSE]

PublishRun ==
    /\ s.phase \in {"ScaffoldReady", "BundleStaged"}
    /\ s' = [s EXCEPT !.phase = IF s.phase = "BundleStaged"
                               THEN "BundlePublishing" ELSE "Ready",
                      !.visible = TRUE]

PublishBundle ==
    /\ s.phase = "BundlePublishing"
    /\ s' = [s EXCEPT !.phase = "Ready"]

RollBackRun ==
    /\ s.phase = "BundlePublishing"
    /\ s' = [s EXCEPT !.phase = "Rejected", !.visible = FALSE, !.complete = FALSE]

ReadEvidence ==
    /\ s.phase = "Ready"
    /\ \E input \in JsonInputs \cup JUnitInputs \cup InvalidInputs \cup {NoEvidence}:
        s' = [s EXCEPT !.phase = "Read", !.input = input]

RescoreReport ==
    /\ s.phase = "Read" /\ s.input.kind = "JSON"
    /\ s' = [s EXCEPT !.phase = "Rescored",
                      !.resultIds = s.input.reported \cup s.input.flags,
                      !.resultPassed = s.input.passed \ s.input.flags,
                      !.resultUnverified = s.input.flags]

CompareScoredEvidence ==
    /\ s.phase \in {"Read", "Rescored"} /\ s.input.kind \in ValidKinds
    /\ LET ids == Required(s.input)
           reported == IF s.phase = "Rescored" THEN s.resultIds ELSE s.input.reported
           passed == IF s.phase = "Rescored" THEN s.resultPassed ELSE s.input.passed
           flags == IF s.phase = "Rescored" THEN s.resultUnverified ELSE s.input.flags
           unverified == (ids \ reported) \cup (ids \cap flags)
           verifiedPass == (ids \cap passed) \ unverified
       IN s' = [s EXCEPT !.phase = "Compared", !.resultIds = ids,
                         !.resultPassed = verifiedPass, !.resultUnverified = unverified,
                         !.verdict = IF verifiedPass = ids THEN "PASS" ELSE "PARTIAL"]

CompareMissingOrInvalidEvidence ==
    /\ s.phase = "Read" /\ s.input.kind \notin ValidKinds
    /\ s' = [s EXCEPT !.phase = "Compared",
                      !.verdict = IF s.input = NoEvidence THEN "PENDING" ELSE "ERROR"]

Done == s.phase \in {"Rejected", "Compared"} /\ UNCHANGED s

Next ==
    \/ RejectInputs \/ StartStaging \/ FailStaging \/ FinishScaffold
    \/ FailBundleWrite \/ StageBundle \/ FailRunPublish \/ PublishRun
    \/ PublishBundle \/ RollBackRun \/ ReadEvidence \/ RescoreReport
    \/ CompareScoredEvidence \/ CompareMissingOrInvalidEvidence \/ Done

OnlyCompleteTrialIsVisible ==
    s.visible => (s.complete /\ s.phase # "Rejected")

PassRequiresCompleteEvidence ==
    (s.phase = "Compared" /\ s.input.kind \in ValidKinds) =>
        /\ s.resultIds = Required(s.input)
        /\ (s.resultIds \ s.input.reported) \subseteq s.resultUnverified
        /\ (s.input.flags \cap s.resultIds) \subseteq s.resultUnverified
        /\ s.resultPassed = (s.resultIds \cap s.input.passed) \ s.input.flags
        /\ ((s.verdict = "PASS") <=> (s.resultIds \subseteq (s.input.passed \ s.input.flags)))

RescorePreservesUnverified ==
    s.phase = "Rescored" =>
        /\ s.resultUnverified = s.input.flags
        /\ s.resultPassed \cap s.input.flags = {}

ComparisonDistinguishesPendingAndError ==
    s.phase = "Compared" =>
        /\ ((s.verdict = "PENDING") <=> (s.input.kind = "NoEvidence"))
        /\ ((s.verdict = "ERROR") <=> (s.input.kind \in InvalidKinds))

=============================================================================
