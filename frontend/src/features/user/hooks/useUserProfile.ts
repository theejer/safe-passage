import { useState } from "react";
import type { UserProfile } from "@/features/user/types";
import { createUser, updateUserEmergencyContact } from "@/features/user/services/userApi";

// Hook orchestrates local form state + backend sync.
export function useUserProfile() {
  const [profile, setProfile] = useState<UserProfile>({ fullName: "", phone: "" });
  const [isSaving, setIsSaving] = useState(false);

  async function saveProfile() {
    setIsSaving(true);
    try {
      const created = await createUser(profile);
      if (created?.id && profile.emergencyContact) {
        await updateUserEmergencyContact(created.id, profile.emergencyContact);
      }
      return created;
    } finally {
      setIsSaving(false);
    }
  }

  return { profile, setProfile, isSaving, saveProfile };
}
