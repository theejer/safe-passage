import { useEffect, useState } from "react";
import type { UserProfile } from "@/features/user/types";
import { createUser, updateUserEmergencyContact } from "@/features/user/services/userApi";
import { getItem, setItem } from "@/features/storage/services/localStore";
import { generateUuidV4 } from "@/shared/utils/ids";
import { getEmergencyContactByUserId, getUserProfile, initializeOfflineDb } from "@/features/storage/services/offlineDb";

const ACTIVE_USER_ID_KEY = "active_user_id";
const ACTIVE_USER_PROFILE_KEY = "active_user_profile";

// Hook orchestrates local form state + backend sync.
export function useUserProfile() {
  const [profile, setProfile] = useState<UserProfile>({ fullName: "", phone: "" });
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function hydrateProfile() {
      await initializeOfflineDb();
      const activeUserId = await getItem(ACTIVE_USER_ID_KEY);
      if (!activeUserId) return;

      const localProfile = await getUserProfile(activeUserId);
      if (!localProfile) return;

      const localEmergency = await getEmergencyContactByUserId(activeUserId);
      if (cancelled) return;

      setProfile({
        id: localProfile.id,
        fullName: localProfile.full_name,
        phone: localProfile.phone,
        emergencyContact: localEmergency
          ? {
              name: localEmergency.name,
              phone: localEmergency.phone,
            }
          : undefined,
      });
    }

    void hydrateProfile();

    return () => {
      cancelled = true;
    };
  }, []);

  async function saveProfile(options?: { requireRemote?: boolean }) {
    const requireRemote = options?.requireRemote ?? false;
    setIsSaving(true);
    setError(null);
    setSuccess(false);
    try {
      const normalizedFullName = profile.fullName.trim();
      const normalizedPhone = profile.phone.trim();
      const normalizedEmergencyName = profile.emergencyContact?.name?.trim() ?? "";
      const normalizedEmergencyPhone = profile.emergencyContact?.phone?.trim() ?? "";

      if (!normalizedFullName || normalizedPhone.length < 8 || !normalizedEmergencyName || normalizedEmergencyPhone.length < 8) {
        setError("Enter valid traveler and emergency contact details before saving.");
        throw new Error("invalid_profile_fields");
      }

      let resolvedUser: UserProfile = profile;

      try {
        const created = (await createUser({
          ...profile,
          fullName: normalizedFullName,
          phone: normalizedPhone,
          emergencyContact: {
            name: normalizedEmergencyName,
            phone: normalizedEmergencyPhone,
          },
        })) as UserProfile | null;
        if (requireRemote && !created?.id) {
          setError("Server save did not return a user id. Please try again.");
          throw new Error("remote_save_missing_user_id");
        }
        const emergencyName = normalizedEmergencyName;
        const emergencyPhone = normalizedEmergencyPhone;

        if (created?.id && emergencyName.length > 0 && emergencyPhone.length >= 8) {
          await updateUserEmergencyContact(created.id, profile.emergencyContact);
        }
        if (created?.id) {
          resolvedUser = {
            ...profile,
            id: created.id,
            fullName: normalizedFullName,
            phone: normalizedPhone,
            emergencyContact: {
              name: normalizedEmergencyName,
              phone: normalizedEmergencyPhone,
            },
          };
        }
      } catch (error) {
        if (requireRemote) {
          setError("Could not save to server. Please ensure backend is running and try again.");
          throw error;
        }
        resolvedUser = {
          ...profile,
          id: profile.id ?? generateUuidV4(),
          fullName: normalizedFullName,
          phone: normalizedPhone,
          emergencyContact: {
            name: normalizedEmergencyName,
            phone: normalizedEmergencyPhone,
          },
        };
      }

      if (resolvedUser.id) {
        await setItem(ACTIVE_USER_ID_KEY, resolvedUser.id);
      }
      await setItem(ACTIVE_USER_PROFILE_KEY, JSON.stringify(resolvedUser));
      setSuccess(true);

      return resolvedUser;
    } finally {
      setIsSaving(false);
    }
  }

  return { profile, setProfile, isSaving, saveProfile, error, success };
}
