import dotenv from 'dotenv';

dotenv.config();

export const config = {
  port: parseInt(process.env.PORT ?? '8787', 10),
  apiKey: process.env.API_KEY ?? '',
  authFolder: process.env.AUTH_FOLDER ?? 'auth',
  limits: {
    maxButtons: 3,
    maxCarouselCards: 10,
    maxListSections: 10,
    maxListRowsPerSection: 10,
    maxPollOptions: 12,
  },
} as const;

export type Config = typeof config;
