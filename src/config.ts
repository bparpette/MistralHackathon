import dotenv from "dotenv";
import { z } from "zod";

dotenv.config();

const EnvSchema = z.object({
  MCP_HTTP_PORT: z.coerce.number().int().positive().default(3000),
  PORT: z.coerce.number().int().positive().optional(),
});

const parsedEnv = EnvSchema.safeParse(process.env);

if (!parsedEnv.success) {
  if (process.stdout.isTTY) {
    console.error("❌ Invalid environment variables found:", parsedEnv.error.flatten().fieldErrors);
  }
  process.exit(1);
}

export const config = {
  ...parsedEnv.data,
  MCP_HTTP_PORT: parsedEnv.data.PORT || parsedEnv.data.MCP_HTTP_PORT,
};
