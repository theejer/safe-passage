import { useState } from "react";
import { ScrollView, Text, View } from "react-native";
import {
  runHeartbeatRuntimeSmokeTest,
  type HeartbeatSmokeReport,
} from "../../tests/heartbeat/heartbeatRuntime.smoke";
import { Button } from "@/shared/components/Button";
import { Screen } from "@/shared/components/Screen";

export default function HeartbeatSmokeTestScreen() {
  const [running, setRunning] = useState(false);
  const [report, setReport] = useState<HeartbeatSmokeReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [logs, setLogs] = useState<string[]>([]);

  async function handleRun() {
    setRunning(true);
    setError(null);
    setReport(null);
    setLogs([]);

    const appendLog = (message: string) => {
      const timestamp = new Date().toISOString();
      const line = `[${timestamp}] ${message}`;
      setLogs((prev) => [...prev, line]);
      console.log(line);
    };

    try {
      appendLog("Starting heartbeat runtime smoke test");
      const result = await runHeartbeatRuntimeSmokeTest({
        onLog: appendLog,
        checkTimeoutMs: 20000,
      });
      setReport(result);
      appendLog(`Completed heartbeat smoke test: ${result.ok ? "PASS" : "FAIL"}`);
    } catch (runError) {
      const message = runError instanceof Error ? runError.message : "Unknown test runner error";
      setError(message);
      appendLog(`Runner crashed: ${message}`);
    } finally {
      setRunning(false);
    }
  }

  return (
    <Screen>
      <ScrollView contentContainerStyle={{ gap: 12, paddingBottom: 24 }}>
        <Text style={{ fontSize: 22, fontWeight: "700" }}>Heartbeat Runtime Smoke Test</Text>
        <Text style={{ color: "#444" }}>
          Validates heartbeat queue/replay and heartbeat-enabled trip gating behavior.
        </Text>

        <Button onPress={running ? undefined : handleRun}>
          {running ? "Running..." : "Run Heartbeat Smoke Test"}
        </Button>

        {error ? (
          <View style={{ borderWidth: 1, borderColor: "#e11d48", borderRadius: 8, padding: 12, gap: 6 }}>
            <Text style={{ fontWeight: "700", color: "#be123c" }}>Runner Error</Text>
            <Text>{error}</Text>
          </View>
        ) : null}

        <View style={{ borderWidth: 1, borderColor: "#cbd5e1", borderRadius: 8, padding: 12, gap: 8 }}>
          <Text style={{ fontWeight: "700" }}>Live Logs</Text>
          {logs.length === 0 ? (
            <Text style={{ color: "#475569" }}>No logs yet. Run the test to stream progress.</Text>
          ) : (
            <View style={{ gap: 4 }}>
              {logs.map((line, index) => (
                <Text key={`${index}_${line}`} style={{ color: "#334155", fontSize: 12 }}>
                  {line}
                </Text>
              ))}
            </View>
          )}
        </View>

        {report ? (
          <View style={{ borderWidth: 1, borderColor: report.ok ? "#22c55e" : "#f59e0b", borderRadius: 8, padding: 12, gap: 8 }}>
            <Text style={{ fontWeight: "700", color: report.ok ? "#15803d" : "#b45309" }}>
              Overall: {report.ok ? "PASS" : "FAIL"}
            </Text>
            <Text>Started: {report.startedAt}</Text>
            <Text>Finished: {report.finishedAt}</Text>

            <View style={{ gap: 6, marginTop: 8 }}>
              {report.checks.map((check) => (
                <View key={check.name} style={{ borderWidth: 1, borderColor: "#e5e7eb", borderRadius: 6, padding: 8 }}>
                  <Text style={{ fontWeight: "600" }}>
                    {check.ok ? "✅" : "❌"} {check.name}
                  </Text>
                  {!check.ok && check.detail ? <Text style={{ color: "#b91c1c" }}>{check.detail}</Text> : null}
                </View>
              ))}
            </View>
          </View>
        ) : null}
      </ScrollView>
    </Screen>
  );
}
