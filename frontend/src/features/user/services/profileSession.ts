import { getEmergencyContactByUserId, getUserProfile, initializeOfflineDb } from "@/features/storage/services/offlineDb";
import { getItem } from "@/features/storage/services/localStore";

const ACTIVE_USER_ID_KEY = "active_user_id";

export type ProfileSession = {
  userId: string;
  fullName: string;
  phone: string;
  emergencyName: string;
  emergencyPhone: string;
};

export async function getProfileSession(): Promise<ProfileSession | null> {
  await initializeOfflineDb();
  const activeUserId = (await getItem(ACTIVE_USER_ID_KEY))?.trim();
  if (!activeUserId) return null;

  const user = await getUserProfile(activeUserId);
  const emergency = await getEmergencyContactByUserId(activeUserId);

  if (!user) return null;

  const fullName = user.full_name?.trim() ?? "";
  const phone = user.phone?.trim() ?? "";
  const emergencyName = emergency?.name?.trim() ?? "";
  const emergencyPhone = emergency?.phone?.trim() ?? "";

  if (!fullName || phone.length < 8 || !emergencyName || emergencyPhone.length < 8) {
    return null;
  }

  return {
    userId: activeUserId,
    fullName,
    phone,
    emergencyName,
    emergencyPhone,
  };
}
