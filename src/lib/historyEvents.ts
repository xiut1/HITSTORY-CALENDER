export type HistoryEvent = {
  id: string;
  country: string;
  date: string;
  year: number;
  title: string;
  description: string;
  category?: "history" | "holiday";
  subcategory?: "war" | "politics" | "science" | "culture" | "disaster";
  url?: string;
};

export const historyEvents: HistoryEvent[] = [];
