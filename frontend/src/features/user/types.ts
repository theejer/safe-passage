// Barebones user profile types for onboarding and emergency alerts.
export type EmergencyContact = {
  name: string;
  phone: string;
  email?: string;
};

export type UserProfile = {
  id?: string;
  fullName: string;
  phone: string;
  emergencyContact?: EmergencyContact;
};
