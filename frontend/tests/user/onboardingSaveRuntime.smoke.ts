import { createUser, updateUserEmergencyContact } from "@/features/user/services/userApi";
import {
  getEmergencyContactByUserId,
  getPendingSyncJobs,
  getUserProfile,
  initializeOfflineDb,
} from "@/features/storage/services/offlineDb";
import { getItem, setItem } from "@/features/storage/services/localStore";
import { generateUuidV4 } from "@/shared/utils/ids";
import type { UserProfile } from "@/features/user/types";

export type OnboardingSmokeCheck = {
  name: string;
  ok: boolean;
  detail?: string;
};

export type OnboardingSmokeReport = {
  ok: boolean;
  startedAt: string;
  finishedAt: string;
  checks: OnboardingSmokeCheck[];
};

type SmokeLogger = (message: string) => void;

type OnboardingSmokeOptions = {
  onLog?: SmokeLogger;
  checkTimeoutMs?: number;
};

const ACTIVE_USER_ID_KEY = "active_user_id";

function assert(condition: unknown, message: string) {
  if (!condition) {
    throw new Error(message);
  }
}

function isUuid(value: string) {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value);
}

async function runCheck(
  checks: OnboardingSmokeCheck[],
  name: string,
  task: () => Promise<void>,
  options?: OnboardingSmokeOptions
) {
  const onLog = options?.onLog;
  const timeoutMs = options?.checkTimeoutMs ?? 15000;

  const startedAt = Date.now();
  onLog?.(`▶️ START ${name}`);
  console.log(`[onboarding-smoke] START ${name}`);

  try {
    await Promise.race([
      task(),
      new Promise<never>((_, reject) => {
        setTimeout(() => reject(new Error(`Timed out after ${timeoutMs}ms`)), timeoutMs);
      }),
    ]);

    checks.push({ name, ok: true });
    const duration = Date.now() - startedAt;
    onLog?.(`✅ PASS ${name} (${duration}ms)`);
    console.log(`[onboarding-smoke] PASS ${name} (${duration}ms)`);
  } catch (error) {
    const duration = Date.now() - startedAt;
    const detail = error instanceof Error ? error.message : "Unknown error";
    checks.push({ name, ok: false, detail });
    onLog?.(`❌ FAIL ${name} (${duration}ms) - ${detail}`);
    console.log(`[onboarding-smoke] FAIL ${name} (${duration}ms) - ${detail}`);
  }
}

export async function runOnboardingSaveRuntimeSmokeTest(
  options?: OnboardingSmokeOptions
): Promise<OnboardingSmokeReport> {
  const onLog = options?.onLog;
  const checks: OnboardingSmokeCheck[] = [];
  const startedAt = new Date().toISOString();
  const stamp = Date.now();

  const offlineUserId = `local_user_${stamp}`;
  const profile: UserProfile = {
    id: offlineUserId,
    fullName: "Smoke User",
    phone: "+919111111111",
    emergencyContact: {
      name: "Smoke Contact",
      phone: "+919222222222",
    },
  };

  onLog?.(`ℹ️ Onboarding smoke started at ${startedAt}`);

  await runCheck(
    checks,
    "uuid generation is callable",
    async () => {
      const generated = generateUuidV4();
      assert(isUuid(generated), "generateUuidV4 should return UUID v4 format");
    },
    options
  );

  await runCheck(
    checks,
    "initialize offline db",
    async () => {
      const init = await initializeOfflineDb();
      assert(init.initialized === true, "DB initialization failed");
    },
    options
  );

  await runCheck(
    checks,
    "save user profile local-first",
    async () => {
      const created = await createUser(profile);
      assert(created.id === offlineUserId, "Expected local user id to be preserved");

      const cached = await getUserProfile(offlineUserId);
      assert(Boolean(cached), "Expected user profile in local sqlite mirror");
      assert(cached?.full_name === "Smoke User", "Expected mirrored full_name");
    },
    options
  );

  await runCheck(
    checks,
    "emergency contact mirror + queue",
    async () => {
      await updateUserEmergencyContact(offlineUserId, {
        name: "Smoke Contact",
        phone: "+919333333333",
      });

      const localContact = await getEmergencyContactByUserId(offlineUserId);
      assert(Boolean(localContact), "Expected emergency contact in local mirror");
      assert(localContact?.phone === "+919333333333", "Expected updated mirrored emergency phone");

      const pending = await getPendingSyncJobs(200);
      const hasUserJob = pending.some((job) => job.entity_type === "user" && job.entity_id === offlineUserId);
      const hasEmergencyJob = pending.some((job) => job.entity_type === "emergency_contact" && job.entity_id === `${offlineUserId}:primary`);
      assert(hasUserJob, "Expected queued user upsert job");
      assert(hasEmergencyJob, "Expected queued emergency_contact upsert job");
    },
    options
  );

  await runCheck(
    checks,
    "active user metadata write/read",
    async () => {
      await setItem(ACTIVE_USER_ID_KEY, offlineUserId);
      const stored = await getItem(ACTIVE_USER_ID_KEY);
      assert(stored === offlineUserId, "Expected active user id metadata to round-trip");
    },
    options
  );

  const finishedAt = new Date().toISOString();
  const ok = checks.every((check) => check.ok);
  onLog?.(`ℹ️ Onboarding smoke finished at ${finishedAt} (${ok ? "PASS" : "FAIL"})`);

  return {
    ok,
    startedAt,
    finishedAt,
    checks,
  };
}
