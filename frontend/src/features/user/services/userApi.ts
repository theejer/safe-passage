import { apiClient } from "@/lib/apiClient";
import type { UserProfile } from "@/features/user/types";
import {
  enqueueSyncJob,
  getEmergencyContactByUserId,
  initializeOfflineDb,
  upsertEmergencyContact,
  upsertUserProfile,
  type SyncQueueJob,
} from "@/features/storage/services/offlineDb";
import { isLocalOnlyUserId } from "@/shared/utils/syncGuards";
import { generateUuidV4 } from "@/shared/utils/ids";

type UserCreateWire = {
  id?: string;
  full_name: string;
  phone: string;
  emergency_contact?: {
    name: string;
    phone: string;
    email?: string;
  };
};

type UserResponseWire = {
  id: string;
  full_name?: string;
  phone?: string;
  emergency_contact?: {
    name?: string;
    phone?: string;
    telegram_chat_id?: string;
    telegram_bot_active?: boolean;
  };
};

function toLocalProfile(userId: string, profile: UserProfile) {
  return {
    id: userId,
    full_name: profile.fullName.trim(),
    phone: profile.phone.trim(),
    sync_status: "pending" as const,
  };
}

function toEmergencySyncPayload(userId: string, emergencyContact?: UserProfile["emergencyContact"]) {
  const emergencyName = emergencyContact?.name?.trim() ?? "";
  const emergencyPhone = emergencyContact?.phone?.trim() ?? "";
  if (!emergencyName || emergencyPhone.length < 8) {
    return null;
  }

  return {
    id: `${userId}:primary`,
    user_id: userId,
    name: emergencyName,
    phone: emergencyPhone,
    telegram_chat_id: null,
    telegram_bot_active: false,
    sync_status: "pending" as const,
  };
}

function fromUserWire(response: UserResponseWire): UserProfile {
  return {
    id: response.id,
    fullName: String(response.full_name ?? ""),
    phone: String(response.phone ?? ""),
    emergencyContact: response.emergency_contact
      ? {
          name: String(response.emergency_contact.name ?? ""),
          phone: String(response.emergency_contact.phone ?? ""),
        }
      : undefined,
  };
}

// API boundary for user onboarding and emergency contact updates.
export async function createUser(profile: UserProfile) {
  await initializeOfflineDb();
  const userId = profile.id ?? generateUuidV4();

  const fullName = profile.fullName.trim();
  const phone = profile.phone.trim();

  const payload: UserCreateWire = {
    id: userId,
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

  await upsertUserProfile(toLocalProfile(userId, profile));

  const localEmergency = toEmergencySyncPayload(userId, profile.emergencyContact);
  if (localEmergency) {
    await upsertEmergencyContact(localEmergency);
  }

  if (isLocalOnlyUserId(userId)) {
    await enqueueSyncJob({
      entityType: "user",
      entityId: userId,
      operation: "upsert",
      payload,
    });
    return { ...profile, id: userId };
  }

  try {
    const created = (await apiClient.post("/api/users", payload)) as UserResponseWire;
    const normalized = fromUserWire(created);

    await upsertUserProfile({
      id: normalized.id as string,
      full_name: normalized.fullName,
      phone: normalized.phone,
      sync_status: "synced",
    });

    const remoteEmergency = normalized.emergencyContact;
    if (remoteEmergency?.name && remoteEmergency.phone) {
      await upsertEmergencyContact({
        id: `${normalized.id}:primary`,
        user_id: normalized.id as string,
        name: remoteEmergency.name,
        phone: remoteEmergency.phone,
        telegram_chat_id: null,
        telegram_bot_active: false,
        sync_status: "synced",
      });
    }

    return normalized;
  } catch {
    await enqueueSyncJob({
      entityType: "user",
      entityId: userId,
      operation: "upsert",
      payload,
    });
    return { ...profile, id: userId };
  }
}

export async function updateUserEmergencyContact(userId: string, emergencyContact: UserProfile["emergencyContact"]) {
  await initializeOfflineDb();

  const emergencyPayload = toEmergencySyncPayload(userId, emergencyContact);
  if (!emergencyPayload) {
    return null;
  }

  await upsertEmergencyContact(emergencyPayload);

  if (isLocalOnlyUserId(userId)) {
    await enqueueSyncJob({
      entityType: "emergency_contact",
      entityId: emergencyPayload.id,
      operation: "upsert",
      payload: emergencyContact as Record<string, unknown>,
    });
    return emergencyPayload;
  }

  try {
    const response = (await apiClient.patch(`/api/users/${userId}/emergency-contact`, emergencyContact ?? {})) as UserResponseWire;
    const mergedProfile = fromUserWire(response);
    if (mergedProfile.id) {
      await upsertUserProfile({
        id: mergedProfile.id,
        full_name: mergedProfile.fullName,
        phone: mergedProfile.phone,
        sync_status: "synced",
      });
    }

    const latestContact = await getEmergencyContactByUserId(userId);
    if (latestContact) {
      await upsertEmergencyContact({
        ...latestContact,
        sync_status: "synced",
      });
    }

    return response;
  } catch {
    await enqueueSyncJob({
      entityType: "emergency_contact",
      entityId: emergencyPayload.id,
      operation: "upsert",
      payload: emergencyContact as Record<string, unknown>,
    });
    return emergencyPayload;
  }
}

export async function replayUserSyncJob(job: SyncQueueJob) {
  if (job.entity_type !== "user") {
    throw new Error(`unsupported sync job entity type: ${job.entity_type}`);
  }

  const payload = JSON.parse(job.payload_json) as UserCreateWire;
  const created = (await apiClient.post("/api/users", payload)) as UserResponseWire;
  const normalized = fromUserWire(created);
  await upsertUserProfile({
    id: normalized.id as string,
    full_name: normalized.fullName,
    phone: normalized.phone,
    sync_status: "synced",
  });
}

export async function replayEmergencyContactSyncJob(job: SyncQueueJob) {
  if (job.entity_type !== "emergency_contact") {
    throw new Error(`unsupported sync job entity type: ${job.entity_type}`);
  }

  const payload = JSON.parse(job.payload_json) as UserProfile["emergencyContact"];
  const userId = job.entity_id.split(":")[0];
  await apiClient.patch(`/api/users/${userId}/emergency-contact`, payload ?? {});

  const latestContact = await getEmergencyContactByUserId(userId);
  if (latestContact) {
    await upsertEmergencyContact({
      ...latestContact,
      sync_status: "synced",
    });
  }
}
