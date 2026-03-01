import { useEffect, useState } from "react";
import NetInfo, { type NetInfoStateType } from "@react-native-community/netinfo";

export function useOnlineStatus() {
  const [isOnline, setIsOnline] = useState(true);
  const [networkType, setNetworkType] = useState<NetInfoStateType | "unknown">("unknown");

  useEffect(() => {
    const unsubscribe = NetInfo.addEventListener((state) => {
      setIsOnline(Boolean(state.isConnected) && Boolean(state.isInternetReachable ?? true));
      setNetworkType(state.type ?? "unknown");
    });

    void NetInfo.fetch().then((state) => {
      setIsOnline(Boolean(state.isConnected) && Boolean(state.isInternetReachable ?? true));
      setNetworkType(state.type ?? "unknown");
    });

    return unsubscribe;
  }, []);

  return { isOnline, networkType };
}
