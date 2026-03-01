import { apiClient } from "@/lib/apiClient";
import type { UserProfile } from "@/features/user/types";

// API boundary for user onboarding and emergency contact updates.
export async function createUser(profile: UserProfile) {
  return apiClient.post("/users", profile);
}

export async function updateUserEmergencyContact(userId: string, emergencyContact: UserProfile["emergencyContact"]) {
  return apiClient.patch(`/users/${userId}/emergency-contact`, emergencyContact ?? {});
}
