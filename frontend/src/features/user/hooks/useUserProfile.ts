import { useState } from "react";
import type { UserProfile } from "@/features/user/types";
import { createUser, updateUserEmergencyContact } from "@/features/user/services/userApi";
import { setItem } from "@/features/storage/services/localStore";

const ACTIVE_USER_ID_KEY = "active_user_id";
const ACTIVE_USER_PROFILE_KEY = "active_user_profile";

// Hook orchestrates local form state + backend sync.
export function useUserProfile() {
  const [profile, setProfile] = useState<UserProfile>({ fullName: "", phone: "" });
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  async function saveProfile(options?: { requireRemote?: boolean }) {
    const requireRemote = options?.requireRemote ?? false;
    setIsSaving(true);
    setError(null);
    setSuccess(false);
    try {
      const normalizedFullName = profile.fullName.trim();
      const normalizedPhone = profile.phone.trim();

      if (!normalizedFullName || normalizedPhone.length < 8) {
        if (requireRemote) {
          setSaveError("Enter a valid full name and phone before saving.");
          throw new Error("invalid_profile_fields");
        }

        const fallbackUser: UserProfile = {
          ...profile,
          id: profile.id ?? `local_user_${Date.now()}`,
          fullName: normalizedFullName,
          phone: normalizedPhone,
        };
        await setItem(ACTIVE_USER_ID_KEY, fallbackUser.id as string);
        await setItem(ACTIVE_USER_PROFILE_KEY, JSON.stringify(fallbackUser));
        return fallbackUser;
      }

      let resolvedUser: UserProfile = profile;

      try {
        const created = (await createUser(profile)) as UserProfile | null;
        if (requireRemote && !created?.id) {
          setSaveError("Server save did not return a user id. Please try again.");
          throw new Error("remote_save_missing_user_id");
        }
        const emergencyName = profile.emergencyContact?.name?.trim() ?? "";
        const emergencyPhone = profile.emergencyContact?.phone?.trim() ?? "";

        if (created?.id && emergencyName.length > 0 && emergencyPhone.length >= 8) {
          await updateUserEmergencyContact(created.id, profile.emergencyContact);
        }
        if (created?.id) {
          resolvedUser = { ...profile, id: created.id };
        }
      } catch (error) {
        if (requireRemote) {
          setSaveError("Could not save to server. Please ensure backend is running and try again.");
          throw error;
        }
        resolvedUser = { ...profile, id: profile.id ?? `local_user_${Date.now()}` };
      }

      if (resolvedUser.id) {
        await setItem(ACTIVE_USER_ID_KEY, resolvedUser.id);
      }
      await setItem(ACTIVE_USER_PROFILE_KEY, JSON.stringify(resolvedUser));

      return resolvedUser;
    } finally {
      setIsSaving(false);
    }
  }

  return { profile, setProfile, isSaving, saveProfile, error, success };
}
