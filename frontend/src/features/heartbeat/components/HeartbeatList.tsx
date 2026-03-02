import { useState } from "react";
import { Pressable, Text, View } from "react-native";
import type { LocalHeartbeatJournal } from "@/features/storage/services/offlineDb";

type HeartbeatItemProps = {
  heartbeat: LocalHeartbeatJournal;
  isExpanded: boolean;
  onToggle: () => void;
};

function HeartbeatItem({ heartbeat, isExpanded, onToggle }: HeartbeatItemProps) {
  const timestamp = new Date(heartbeat.timestamp);
  const timeString = timestamp.toLocaleTimeString("en-US", { 
    hour: "2-digit", 
    minute: "2-digit", 
    second: "2-digit" 
  });
  const dateString = timestamp.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  });

  const statusColor = 
    heartbeat.sync_status === "synced" ? "#10b981" : 
    heartbeat.sync_status === "failed" ? "#ef4444" : 
    "#f59e0b";

  return (
    <Pressable
      onPress={onToggle}
      style={({ pressed }) => ({
        borderWidth: 1,
        borderColor: "#e5e7eb",
        borderRadius: 8,
        padding: 12,
        backgroundColor: pressed ? "#f3f4f6" : "#ffffff",
      })}
    >
      <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
        <View style={{ flex: 1, gap: 4 }}>
          <View style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
            <Text style={{ fontSize: 14, fontWeight: "600", color: "#111827" }}>
              {dateString} • {timeString}
            </Text>
            <View
              style={{
                width: 8,
                height: 8,
                borderRadius: 4,
                backgroundColor: statusColor,
              }}
            />
          </View>
          <Text style={{ fontSize: 12, color: "#6b7280" }}>
            {heartbeat.source} • {heartbeat.network_status}
          </Text>
        </View>
        <Text style={{ fontSize: 18, color: "#9ca3af" }}>
          {isExpanded ? "▼" : "▶"}
        </Text>
      </View>

      {isExpanded && (
        <View
          style={{
            marginTop: 12,
            paddingTop: 12,
            borderTopWidth: 1,
            borderTopColor: "#e5e7eb",
            gap: 6,
          }}
        >
          <DetailRow label="Battery" value={heartbeat.battery_percent != null ? `${heartbeat.battery_percent}%` : "N/A"} />
          <DetailRow
            label="Location"
            value={
              heartbeat.gps_lat != null && heartbeat.gps_lng != null
                ? `${heartbeat.gps_lat.toFixed(6)}, ${heartbeat.gps_lng.toFixed(6)}`
                : "N/A"
            }
          />
          <DetailRow
            label="Accuracy"
            value={heartbeat.accuracy_meters != null ? `${heartbeat.accuracy_meters.toFixed(0)}m` : "N/A"}
          />
          <DetailRow
            label="Offline"
            value={heartbeat.offline_minutes != null ? `${heartbeat.offline_minutes} min` : "N/A"}
          />
          <DetailRow
            label="Sync Status"
            value={
              <View style={{ flexDirection: "row", alignItems: "center", gap: 6 }}>
                <View
                  style={{
                    width: 8,
                    height: 8,
                    borderRadius: 4,
                    backgroundColor: statusColor,
                  }}
                />
                <Text style={{ fontSize: 13, color: "#4b5563", textTransform: "capitalize" }}>
                  {heartbeat.sync_status || "pending"}
                </Text>
              </View>
            }
          />
        </View>
      )}
    </Pressable>
  );
}

function DetailRow({ label, value }: { label: string; value: string | React.ReactNode }) {
  return (
    <View style={{ flexDirection: "row", justifyContent: "space-between" }}>
      <Text style={{ fontSize: 13, color: "#6b7280", fontWeight: "500" }}>{label}:</Text>
      {typeof value === "string" ? (
        <Text style={{ fontSize: 13, color: "#4b5563" }}>{value}</Text>
      ) : (
        value
      )}
    </View>
  );
}

type HeartbeatListProps = {
  heartbeats: LocalHeartbeatJournal[];
};

export function HeartbeatList({ heartbeats }: HeartbeatListProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  if (heartbeats.length === 0) {
    return (
      <Text style={{ color: "#6b7280", fontSize: 14 }}>
        No heartbeats recorded yet. Heartbeats are sent automatically when monitoring is active.
      </Text>
    );
  }

  return (
    <View style={{ gap: 8 }}>
      {heartbeats.map((heartbeat) => (
        <HeartbeatItem
          key={heartbeat.id}
          heartbeat={heartbeat}
          isExpanded={expandedId === heartbeat.id}
          onToggle={() => setExpandedId(expandedId === heartbeat.id ? null : heartbeat.id)}
        />
      ))}
    </View>
  );
}
