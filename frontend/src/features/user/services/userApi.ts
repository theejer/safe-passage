import { apiClient } from "@/lib/apiClient";
import type { UserProfile } from "@/features/user/types";

type UserCreateWire = {
  full_name: string;
  phone: string;
  emergency_contact?: {
    name: string;
    phone: string;
    email?: string;
  };
};

// API boundary for user onboarding and emergency contact updates.
export async function createUser(profile: UserProfile) {
  const fullName = profile.fullName.trim();
  const phone = profile.phone.trim();

  const payload: UserCreateWire = {
    full_name: fullName,
    phone,
  };

  const emergencyName = profile.emergencyContact?.name?.trim() ?? "";
  const emergencyPhone = profile.emergencyContact?.phone?.trim() ?? "";
  const emergencyEmail = profile.emergencyContact?.email?.trim();

  if (emergencyName.length > 0 && emergencyPhone.length >= 8) {
    payload.emergency_contact = {
      name: emergencyName,
      phone: emergencyPhone,
      email: emergencyEmail || undefined,
    };
  }

  return apiClient.post("/api/users", payload);
}

export async function updateUserEmergencyContact(userId: string, emergencyContact: UserProfile["emergencyContact"]) {
  return apiClient.patch(`/api/users/${userId}/emergency-contact`, emergencyContact ?? {});
}
