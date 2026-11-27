export const title = "SpecPack Eval Lifecycle";

export const colors = {
  preparation: "blue",
  scoring: "teal",
  result: "tan",
  failure: "pink",
};

const phases = {
  New: "Trial requested",
  Staging: "Scaffold hidden",
  ScaffoldReady: "Scaffold complete",
  BundleStaged: "Bundle staged",
  BundlePublishing: "Trial visible, bundle publishing",
  Ready: "Trial ready",
  Rejected: "Preparation failed",
  Read: "Evidence inspected",
  Rescored: "JSON report rescored",
};

export const state = ({ s }) => {
  if (s.visible && !s.complete) return "Incomplete trial visible";
  return s.phase === "Compared" ? s.verdict : phases[s.phase];
};

export const group = ({ s }) => {
  if (s.phase === "Rejected" || s.verdict === "ERROR") return "failure";
  if (s.phase === "Compared") return "result";
  if (["Ready", "Read", "Rescored"].includes(s.phase)) return "scoring";
  return "preparation";
};

const actions = {
  RejectInputs: "pack or output path rejected",
  StartStaging: "validated pack starts staging",
  FailStaging: "copy or Git initialization fails",
  FinishScaffold: "scaffold completed",
  FailBundleWrite: "bundle write fails",
  StageBundle: "bundle written privately",
  FailRunPublish: "trial rename fails",
  PublishRun: "trial renamed into place",
  PublishBundle: "bundle moved into place",
  RollBackRun: "bundle move fails and trial is withdrawn",
  ReadEvidence: "trial evidence is read",
  RescoreReport: "existing JSON report rescored",
  CompareScoredEvidence: "verdict calculated from criterion results",
  Done: "finished",
};

export const step = (action, { s }) => {
  if (action === "CompareMissingOrInvalidEvidence") {
    return s.input.kind === "NoEvidence" ? "no evidence supplied" : "evidence cannot be scored";
  }
  return actions[action];
};
