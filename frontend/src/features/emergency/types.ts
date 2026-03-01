export type ScenarioKey =
  | "lost"
  | "theft"
  | "harassment"
  | "medical"
  | "flood"
  | "breakdown"
  | "detained"
  | "witness";

export type ScenarioProtocol = {
  key: ScenarioKey;
  title: string;
  steps: string[];
};
