export type Location = {
  id?: string;
  name: string;
  district?: string;
  block?: string;
  connectivityZone?: "low" | "moderate" | "high" | "severe";
};

export type Day = {
  date: string;
  locations: Location[];
  accommodation?: string;
};

export type Trip = {
  id: string;
  userId: string;
  title: string;
  startDate: string;
  endDate: string;
  days?: Day[];
};
