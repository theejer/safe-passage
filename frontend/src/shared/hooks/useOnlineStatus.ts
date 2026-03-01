import { useEffect, useState } from "react";

export function useOnlineStatus() {
  // TODO: replace with @react-native-community/netinfo integration.
  const [isOnline, setIsOnline] = useState(true);

  useEffect(() => {
    setIsOnline(true);
  }, []);

  return { isOnline };
}
